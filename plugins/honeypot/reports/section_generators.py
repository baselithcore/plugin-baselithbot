"""Report Section Generators.

LLM-enhanced generation logic for report sections.
Extracted from service.py for modularity (Phase 1 refactoring).
"""

from core.observability.logging import get_logger
from typing import Optional

from .generator import ReportTextGenerator
from .llm import ModularReportLLMService
from .models import ReportConfig, ReportSection, SecurityReport

logger = get_logger(__name__)


async def generate_executive_summary_section(
    llm_service: Optional[ModularReportLLMService],
    generator: ReportTextGenerator,
    use_llm: bool,
    threat_summary,
    config: ReportConfig,
    title: Optional[str],
    timeline: Optional[list],
    geo_distribution: Optional[list],
    honeypot_context: Optional[dict] = None,
    payload_samples: Optional[list] = None,
) -> str:
    """Generate executive summary using LLM or templates.

    Args:
        llm_service: Optional LLM service instance
        generator: Template generator instance
        use_llm: Whether LLM is enabled
        threat_summary: Threat statistics
        config: Report configuration
        title: Optional custom title
        timeline: Optional timeline data for context
        geo_distribution: Optional geo data for context
        honeypot_context: Optional honeypot metadata
        payload_samples: Optional payload samples for attack analysis

    Returns:
        Executive summary markdown text
    """
    if use_llm and llm_service:
        try:
            logger.info("Generating executive summary with LLM (with payload context)")
            return await llm_service.generate_executive_summary(
                threat_summary,
                config,
                title,
                timeline,
                geo_distribution,
                honeypot_context,
                payload_samples,  # Pass payload samples to LLM
            )
        except Exception as e:
            logger.warning(
                f"LLM executive summary failed, falling back to template: {e}"
            )

    # Fallback to template-based generation
    logger.info("Generating executive summary with templates")
    return await generator.generate_executive_summary(threat_summary, config, title)


async def generate_recommendations_section(
    llm_service: Optional[ModularReportLLMService],
    generator: ReportTextGenerator,
    use_llm: bool,
    threat_summary,
    report: SecurityReport,
) -> list:
    """Generate recommendations using LLM or templates.

    Args:
        llm_service: Optional LLM service instance
        generator: Template generator instance
        use_llm: Whether LLM is enabled
        threat_summary: Threat statistics
        report: Full report data

    Returns:
        List of recommendation strings
    """
    if use_llm and llm_service:
        try:
            logger.info("Generating recommendations with LLM")
            return await llm_service.generate_recommendations(
                threat_summary, report.vulnerabilities, report.botnet_activity
            )
        except Exception as e:
            logger.warning(f"LLM recommendations failed, falling back to template: {e}")

    # Fallback to template-based generation
    logger.info("Generating recommendations with templates")
    return await generator.generate_recommendations(threat_summary, report)


async def generate_research_sections(
    report: SecurityReport,
    config: ReportConfig,
    threat_summary,
    timeline: Optional[list],
    geo_distribution: Optional[list],
    honeypot_context: Optional[dict] = None,
) -> None:
    """Generate research-specific sections using ResearchReportGenerator.

    Adds ABSTRACT, KEY_FINDINGS, MITRE_MAPPING, STATISTICAL_ANALYSIS,
    and PAYLOAD_ANALYSIS sections to the report for RESEARCH type.

    Args:
        report: SecurityReport being generated
        config: Report configuration
        threat_summary: Threat statistics
        timeline: Attack timeline data
        geo_distribution: Geographic distribution data
        honeypot_context: Optional honeypot metadata
    """
    from .llm.generators import ResearchReportGenerator

    # Get honeypot name from context or config
    honeypot_name = "All Honeypots"
    if honeypot_context:
        honeypot_name = honeypot_context.get(
            "name", config.honeypot_id or "All Honeypots"
        )
    elif config.honeypot_id:
        honeypot_name = config.honeypot_id

    # Build time range string
    time_range = f"last {config.time_range_hours} hours"
    if config.time_range_hours >= 168:
        days = config.time_range_hours // 24
        time_range = f"last {days} days"

    try:
        # Initialize research generator
        from core.services.llm.service import LLMService

        llm_service = LLMService()
        research_gen = ResearchReportGenerator(llm_service)

        # Prepare tasks for parallel execution
        import asyncio

        # Semaphore to limit concurrency (e.g., to 5) to prevent overloading local LLM
        # For external LLM APIs (like OpenAI), we can allow higher concurrency.
        semaphore = asyncio.Semaphore(5)

        async def run_with_semaphore(task_name, coro):
            async with semaphore:
                logger.info(f"Starting {task_name} generation...")
                try:
                    result = await coro
                    logger.info(f"Finished {task_name} generation.")
                    return result
                except Exception as e:
                    logger.error(f"Failed {task_name} generation: {e}")
                    raise e

        tasks = []
        # Keep track of which section corresponds to which task index
        section_order = []

        # 1. ABSTRACT
        if ReportSection.ABSTRACT in config.sections:
            logger.info(f"Queueing research abstract for {honeypot_name}")
            tasks.append(
                run_with_semaphore(
                    "ABSTRACT",
                    research_gen.generate_abstract(
                        honeypot_name=honeypot_name,
                        threat_summary=threat_summary,
                        time_range=time_range,
                        honeypot_config=honeypot_context,
                    ),
                )
            )
            section_order.append(ReportSection.ABSTRACT)

        # 2. KEY_FINDINGS
        if ReportSection.KEY_FINDINGS in config.sections:
            logger.info(f"Queueing key findings for {honeypot_name}")
            geo_list = [
                {
                    "country_name": g.country_name,
                    "country_code": g.country_code,
                    "attack_count": g.attack_count,
                }
                for g in (geo_distribution or [])
            ]
            tasks.append(
                run_with_semaphore(
                    "KEY_FINDINGS",
                    research_gen.generate_key_findings(
                        honeypot_name=honeypot_name,
                        threat_summary=threat_summary,
                        attack_categories=threat_summary.top_attack_categories,
                        geo_distribution=geo_list,
                    ),
                )
            )
            section_order.append(ReportSection.KEY_FINDINGS)

        # 3. MITRE_MAPPING
        if ReportSection.MITRE_MAPPING in config.sections:
            logger.info(f"Queueing MITRE ATT&CK mapping for {honeypot_name}")
            payload_samples = None
            if report.payload_excerpts:
                payload_samples = [p.excerpt for p in report.payload_excerpts[:10]]

            tasks.append(
                run_with_semaphore(
                    "MITRE_MAPPING",
                    research_gen.generate_mitre_mapping(
                        honeypot_name=honeypot_name,
                        attack_categories=threat_summary.top_attack_categories,
                        protocols=threat_summary.top_protocols,
                        timeline=report.attack_timeline or [],
                        payload_samples=payload_samples,
                    ),
                )
            )
            section_order.append(ReportSection.MITRE_MAPPING)

        # 4. PAYLOAD_ANALYSIS
        if (
            ReportSection.PAYLOAD_ANALYSIS in config.sections
            and report.payload_excerpts
        ):
            logger.info(f"Queueing payload analysis for {honeypot_name}")
            primary_protocol = (
                list(threat_summary.top_protocols.keys())[0]
                if threat_summary.top_protocols
                else "mixed"
            )

            # Enrich payload data with full context
            enriched_payloads = []
            for excerpt in report.payload_excerpts[:15]:
                enriched_payloads.append(
                    {
                        "category": excerpt.category,
                        "severity": excerpt.severity,
                        "excerpt": excerpt.excerpt,
                        "source_country": excerpt.source_country,
                        "protocol": excerpt.protocol,
                        "ai_classification": excerpt.ai_classification or "",
                        "timestamp": excerpt.timestamp.isoformat()
                        if hasattr(excerpt, "timestamp") and excerpt.timestamp
                        else "",
                    }
                )

            tasks.append(
                run_with_semaphore(
                    "PAYLOAD_ANALYSIS",
                    research_gen.generate_payload_analysis(
                        honeypot_name=honeypot_name,
                        payload_excerpts=enriched_payloads,
                        protocol=primary_protocol,
                    ),
                )
            )
            section_order.append(ReportSection.PAYLOAD_ANALYSIS)

        # Execute all tasks in parallel
        if tasks:
            logger.info(
                f"Executing {len(tasks)} research sections in parallel (concurrency=5)..."
            )
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            sections_content = []
            for i, result in enumerate(results):
                section_type = section_order[i]
                if isinstance(result, Exception):
                    logger.error(f"Section {section_type} failed: {result}")
                    # Optionally add a fallback or placeholder here if needed,
                    # but typically ResearchReportGenerator handles its own fallbacks inside the method.
                    # Wait, run_with_semaphore re-raises the exception.
                    # Verify if ResearchReportGenerator.generate methods raise exceptions or return fallback strings.
                    # They return fallback strings on Exception.
                    # So run_with_semaphore will simply return that string.
                    # The only case run_with_semaphore raises is if something totally unexpected happens.
                    continue
                sections_content.append(result)

        # Append research sections to executive summary
        if sections_content:
            research_content = "\n\n".join(sections_content)
            if report.executive_summary:
                report.executive_summary = (
                    f"{research_content}\n\n---\n\n{report.executive_summary}"
                )
            else:
                report.executive_summary = research_content

        logger.info(f"Research sections generated successfully for {honeypot_name}")

    except Exception as e:
        logger.warning(f"Failed to generate research sections: {e}")
        # Fallback: add a note about research sections being unavailable
        fallback = f"""## Research Report

*Analysis of {honeypot_name} honeypot*

Research sections generation encountered an issue. Standard report sections are included below.
"""
        if report.executive_summary:
            report.executive_summary = f"{fallback}\\n\\n{report.executive_summary}"
        else:
            report.executive_summary = fallback

"""Test CVE Correlation - Example Usage.

This script demonstrates how the CVE correlation system works:
1. Attack detected → Category mapped → CVE lookup → Enriched correlation
"""

import asyncio
from plugins.honeypot.agents.correlator import HoneypotCVECorrelator
from plugins.honeypot.services.cve_service import CVEService
from plugins.honeypot.config import get_honeypot_config


async def demo_cve_correlation():
    """Demonstrate CVE correlation with real attack simulation."""

    print("=== CVE Correlation Demo ===\n")

    # 1. Initialize CVE Service
    print("1. Initializing CVE Service...")
    config = get_honeypot_config()
    config.enable_dynamic_cve_lookup = True  # Enable dynamic lookups

    cve_service = CVEService(config=config, redis_client=None)  # No Redis for demo
    print("   ✓ CVE Service ready\n")

    # 2. Initialize Correlator with CVE Service
    print("2. Initializing Correlator...")
    correlator = HoneypotCVECorrelator(config=config, cve_service=cve_service)
    await correlator.initialize()
    correlator.set_cve_service(cve_service)
    print("   ✓ Correlator ready\n")

    # 3. Simulate Attack Scenarios
    print("3. Simulating attack scenarios...\n")

    # SCENARIO 1: SQL Injection Attack
    print("=" * 60)
    print("SCENARIO 1: SQL Injection Attack")
    print("=" * 60)

    correlation = await correlator.correlate_attack(
        event_id="evt_001",
        category="sql_injection",
        patterns=["UNION SELECT", "DROP TABLE"],
        honeypot_tags=[],  # No explicit CVE tag
        source_ip="203.0.113.100",
    )

    if correlation:
        print("\n✓ Correlation found!")
        print(f"  Correlation ID: {correlation['correlation_id']}")
        print(f"  Category: {correlation['category']}")
        print(f"  Matched CVEs: {correlation['matched_cves'][:3]}...")  # First 3
        print(f"  Matched CWEs: {correlation['matched_cwes']}")
        print(f"  Confidence: {correlation['confidence']:.2f}")
        print(f"  MITRE Techniques: {correlation.get('mitre_techniques', [])}")
    else:
        print("\n⏳ Correlation pending (async lookup in progress)")

    # SCENARIO 2: Log4j Exploit (Tagged Honeypot)
    print("\n" + "=" * 60)
    print("SCENARIO 2: Log4j Exploit on Tagged Honeypot")
    print("=" * 60)

    correlation = await correlator.correlate_attack(
        event_id="evt_002",
        category="exploit_attempt",
        patterns=["${jndi:ldap:"],
        honeypot_tags=["cve-2021-44228"],  # Honeypot explicitly tagged with Log4j CVE
        source_ip="203.0.113.200",
    )

    if correlation:
        print("\n✓ Direct CVE match from honeypot tag!")
        print(f"  Correlation ID: {correlation['correlation_id']}")
        print(f"  Matched CVEs: {correlation['matched_cves']}")
        print(
            f"  Confidence: {correlation['confidence']:.2f} (high due to explicit tag)"
        )

        # Show enriched CVE data from NVD
        await asyncio.sleep(1)  # Give time for enrichment
        cve_data = await cve_service.lookup_cve("CVE-2021-44228")
        if cve_data:
            print("\n📋 Enriched CVE Data:")
            print(f"  Description: {cve_data.description[:100]}...")
            print(f"  CVSS Score: {cve_data.cvss_v3_score}/10.0")
            print(f"  Severity: {cve_data.cvss_v3_severity}")
            print(f"  CWEs: {cve_data.cwe_ids}")

    # SCENARIO 3: Command Injection
    print("\n" + "=" * 60)
    print("SCENARIO 3: Command Injection Attack")
    print("=" * 60)

    correlation = await correlator.correlate_attack(
        event_id="evt_003",
        category="command_injection",
        patterns=["rm -rf", "wget http://"],
        honeypot_tags=[],
        source_ip="203.0.113.300",
    )

    if correlation:
        print("\n✓ Correlation found!")
        print(f"  Correlation ID: {correlation['correlation_id']}")
        print(f"  Matched CVEs: {len(correlation['matched_cves'])} CVEs")
        print(f"  Matched CWEs: {correlation['matched_cwes']}")
        print(f"  Confidence: {correlation['confidence']:.2f}")

    # 4. Get Service Statistics
    print("\n" + "=" * 60)
    print("CVE Service Statistics")
    print("=" * 60)

    stats = cve_service.get_stats()
    print(f"\nTotal Lookups: {stats.total_lookups}")
    print(f"Cache Hits: {stats.cache_hits}")
    print(f"Cache Misses: {stats.cache_misses}")
    print(f"API Calls: {stats.api_calls}")
    print(f"Cache Hit Rate: {stats.cache_hit_rate:.1f}%")
    print(f"Avg Latency: {stats.avg_latency_ms:.1f}ms")

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)
    print("\nKey Points:")
    print("✓ Attacks automatically mapped to CVEs via CWE")
    print("✓ Tagged honeypots get direct CVE attribution")
    print("✓ Full CVE enrichment from NVD (CVSS, severity, refs)")
    print("✓ Intelligent caching for performance")
    print("✓ Graceful fallback if NVD unavailable")


if __name__ == "__main__":
    asyncio.run(demo_cve_correlation())

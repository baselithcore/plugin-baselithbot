"""CVE Scanner Parsers.

This module contains parsing logic extracted from the CVEScannerAgent
to improve modularity and testability.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from ..config import CVEHunterConfig
    from ..models import (
        AffectedProduct,
        CVERecord,
        CVEReference,
        CVESeverity,
        CVESource,
        CVSSVector,
    )
except ImportError:
    from config import CVEHunterConfig  # type: ignore[no-redef]
    from models import (  # type: ignore[no-redef]
        AffectedProduct,
        CVERecord,
        CVEReference,
        CVESeverity,
        CVESource,
        CVSSVector,
    )


def score_to_severity(score: float, config: CVEHunterConfig) -> CVESeverity:
    """Convert CVSS score to severity level based on config thresholds."""
    if score is None:
        return CVESeverity.NONE
    # Ensure score is treated as float
    try:
        score = float(score)
    except (ValueError, TypeError):
        return CVESeverity.NONE

    if score >= config.critical_cvss_threshold:
        return CVESeverity.CRITICAL
    elif score >= config.high_cvss_threshold:
        return CVESeverity.HIGH
    elif score >= config.medium_cvss_threshold:
        return CVESeverity.MEDIUM
    elif score > 0:
        return CVESeverity.LOW
    return CVESeverity.NONE


def parse_affected_products(
    configurations: List[Dict[str, Any]],
) -> List[AffectedProduct]:
    """Parse affected products from NVD configurations."""
    products = []
    for config in configurations:
        nodes = config.get("nodes", [])
        for node in nodes:
            cpe_match = node.get("cpeMatch", [])
            for match in cpe_match:
                criteria = match.get("criteria", "")
                # Parse CPE: cpe:2.3:a:vendor:product:version:*
                parts = criteria.split(":")
                if len(parts) >= 5:
                    products.append(
                        AffectedProduct(
                            vendor=parts[3] if len(parts) > 3 else "unknown",
                            product=parts[4] if len(parts) > 4 else "unknown",
                            versions=[parts[5]] if len(parts) > 5 else [],
                            cpe=criteria,
                        )
                    )
    return products


def parse_nvd_cve(cve_data: Dict[str, Any], config: CVEHunterConfig) -> CVERecord:
    """Parse NVD CVE data into CVERecord."""
    cve_id = cve_data.get("id", "")

    # Get description
    descriptions = cve_data.get("descriptions", [])
    description = ""
    for desc in descriptions:
        if desc.get("lang") == "en":
            description = desc.get("value", "")
            break

    # Get CVSS score
    metrics = cve_data.get("metrics", {})
    cvss = None
    severity = CVESeverity.NONE

    # Try CVSS 3.1 first
    cvss_data = metrics.get("cvssMetricV31", [{}])
    if cvss_data:
        cvss_v31 = cvss_data[0].get("cvssData", {})
        score = cvss_v31.get("baseScore", 0)
        # Ensure score is float
        try:
            score = float(score) if score is not None else 0.0
        except (ValueError, TypeError):
            score = 0.0

        cvss = CVSSVector(
            version="3.1",
            vector_string=cvss_v31.get("vectorString"),
            base_score=score,
        )
        severity = score_to_severity(score, config)

    # Get affected products
    configurations = cve_data.get("configurations", [])
    affected = parse_affected_products(configurations)

    # Get references
    refs_data = cve_data.get("references", [])
    references = [
        CVEReference(
            url=ref.get("url", ""),
            source=ref.get("source", ""),
            tags=ref.get("tags", []),
        )
        for ref in refs_data
    ]

    # Get CWE IDs
    weaknesses = cve_data.get("weaknesses", [])
    cwe_ids = []
    for weakness in weaknesses:
        for desc in weakness.get("description", []):
            if desc.get("lang") == "en":
                cwe_ids.append(desc.get("value", ""))

    # Parse dates
    published = cve_data.get("published")
    modified = cve_data.get("lastModified")

    return CVERecord(
        cve_id=cve_id,
        title=cve_id,  # Use CVE ID as title for NVD records since they lack a summary
        description=description,
        severity=severity,
        cvss=cvss,
        source=CVESource.NVD,
        published_date=datetime.fromisoformat(published.replace("Z", "+00:00"))
        if published
        else None,
        last_modified=datetime.fromisoformat(modified.replace("Z", "+00:00"))
        if modified
        else None,
        affected_products=affected,
        references=references,
        cwe_ids=cwe_ids,
        raw_data=cve_data,
    )


def parse_github_advisory(advisory: Dict[str, Any]) -> Optional[CVERecord]:
    """Parse GitHub advisory into CVERecord."""
    cve_id = advisory.get("cve_id")
    if not cve_id:
        return None

    severity_str = advisory.get("severity", "").lower()
    severity_map = {
        "critical": CVESeverity.CRITICAL,
        "high": CVESeverity.HIGH,
        "moderate": CVESeverity.MEDIUM,
        "medium": CVESeverity.MEDIUM,
        "low": CVESeverity.LOW,
    }
    severity = severity_map.get(severity_str, CVESeverity.NONE)

    # Get CVSS from GitHub if available
    cvss = None
    cvss_data = advisory.get("cvss")
    if cvss_data:
        base_score = cvss_data.get("score", 0)
        try:
            base_score = float(base_score) if base_score is not None else 0.0
        except (ValueError, TypeError):
            base_score = 0.0

        cvss = CVSSVector(
            version="3.1",
            vector_string=cvss_data.get("vector_string"),
            base_score=base_score,
        )

    # Parse CWE IDs (can be list of dicts or strings)
    cwe_ids = []
    raw_cwes = advisory.get("cwes", [])
    for cwe in raw_cwes:
        if isinstance(cwe, dict):
            cwe_id = cwe.get("cwe_id")
            if cwe_id:
                cwe_ids.append(cwe_id)
        elif isinstance(cwe, str):
            cwe_ids.append(cwe)

    return CVERecord(
        cve_id=cve_id,
        title=advisory.get("summary"),
        description=advisory.get("description", ""),
        severity=severity,
        cvss=cvss,
        source=CVESource.GITHUB,
        published_date=datetime.fromisoformat(
            advisory["published_at"].replace("Z", "+00:00")
        )
        if advisory.get("published_at")
        else None,
        references=[
            CVEReference(
                url=advisory.get("html_url", ""),
                source="github",
                tags=["advisory"],
            )
        ],
        cwe_ids=cwe_ids,
    )


def parse_cisa_kev(vuln: Dict[str, Any]) -> CVERecord:
    """Parse CISA KEV vulnerability into CVERecord."""
    cve_id = vuln.get("cveID", "")

    # CISA KEV entries are high priority - known exploited
    return CVERecord(
        cve_id=cve_id,
        title=vuln.get("vulnerabilityName"),
        description=vuln.get("shortDescription", ""),
        severity=CVESeverity.CRITICAL,  # All KEV are critical priority
        source=CVESource.CISA_KEV,
        published_date=datetime.fromisoformat(vuln["dateAdded"])
        if vuln.get("dateAdded")
        else None,
        exploit_available=True,  # All CISA KEV have known exploits
        references=[
            CVEReference(
                url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                source="cisa_kev",
                tags=["known_exploited", "cisa"],
            )
        ],
        affected_products=[
            AffectedProduct(
                vendor=vuln.get("vendorProject", "unknown"),
                product=vuln.get("product", "unknown"),
                versions=[],
            )
        ],
    )


def parse_osv_vuln(
    vuln: Dict[str, Any], config: CVEHunterConfig
) -> Optional[CVERecord]:
    """Parse OSV vulnerability into CVERecord."""
    # OSV can have multiple aliases (CVE IDs)
    aliases = vuln.get("aliases", [])
    cve_id = next((a for a in aliases if a.startswith("CVE-")), None)

    if not cve_id:
        # Use OSV ID if no CVE
        cve_id = vuln.get("id", "")

    if not cve_id:
        return None

    # Get severity from database_specific or severity array
    severity = CVESeverity.MEDIUM
    severity_data = vuln.get("severity", [])
    if severity_data:
        score = severity_data[0].get("score", 0) if severity_data else 0
        severity = score_to_severity(float(score) if score else 0, config)

    return CVERecord(
        cve_id=cve_id,
        title=vuln.get("summary"),
        description=vuln.get("details", ""),
        severity=severity,
        source=CVESource.OSV,
        published_date=datetime.fromisoformat(vuln["published"].replace("Z", "+00:00"))
        if vuln.get("published")
        else None,
        references=[
            CVEReference(
                url=ref.get("url", ""),
                source="osv",
                tags=[ref.get("type", "UNKNOWN")],
            )
            for ref in vuln.get("references", [])[:5]
        ],
        affected_products=[
            AffectedProduct(
                vendor=affected.get("package", {}).get("ecosystem", "unknown"),
                product=affected.get("package", {}).get("name", "unknown"),
                versions=[r.get("introduced", "") for r in affected.get("ranges", [])],
            )
            for affected in vuln.get("affected", [])[:5]
        ],
    )

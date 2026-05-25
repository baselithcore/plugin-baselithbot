"""CVE Analyzer Scoring Logic.

This module contains scoring and correlation logic for CVE analysis.
"""

from typing import Dict, List

try:
    from ..models import CVERecord
except ImportError:
    from models import CVERecord  # type: ignore[no-redef]


def calculate_priority_score(cve: CVERecord) -> int:
    """Calculate priority score for a CVE.

    Args:
        cve: CVE record

    Returns:
        Priority score (1-5, 1 is highest)
    """
    score = 5  # Default low priority

    # CVSS score impact
    if cve.cvss_score >= 9.0:
        score = 1
    elif cve.cvss_score >= 7.0:
        score = 2
    elif cve.cvss_score >= 5.0:
        score = 3
    elif cve.cvss_score >= 3.0:
        score = 4

    # Exploit availability increases priority
    if cve.exploit_available:
        score = max(1, score - 1)

    # No patch available increases priority
    if not cve.patch_available:
        score = max(1, score - 1)

    return score


def correlate_cves(cves: List[CVERecord]) -> List[List[str]]:
    """Find related CVEs in a list.

    Args:
        cves: List of CVE records

    Returns:
        List of related CVE ID groups
    """
    # Group by CWE
    cwe_groups: Dict[str, List[str]] = {}
    for cve in cves:
        for cwe in cve.cwe_ids:
            if cwe not in cwe_groups:
                cwe_groups[cwe] = []
            cwe_groups[cwe].append(cve.cve_id)

    # Group by affected product
    product_groups: Dict[str, List[str]] = {}
    for cve in cves:
        for product in cve.affected_products:
            key = f"{product.vendor}:{product.product}"
            if key not in product_groups:
                product_groups[key] = []
            product_groups[key].append(cve.cve_id)

    # Return groups with more than 1 CVE
    correlated = []
    for group in list(cwe_groups.values()) + list(product_groups.values()):
        if len(group) > 1 and group not in correlated:
            correlated.append(group)

    return correlated

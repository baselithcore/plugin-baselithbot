"""Post-scan enrichers — annotate findings with threat-intel context.

Each enricher is fail-open: if the upstream service is unreachable or
returns garbage, the original findings list is returned untouched so
downstream persistence and UI keep working.
"""

from plugins.red_agent.enrichers.attack_mapper import AttackMapperEnricher
from plugins.red_agent.enrichers.compliance_mapper import ComplianceMapperEnricher
from plugins.red_agent.enrichers.epss_kev import EpssKevEnricher
from plugins.red_agent.enrichers.exploit_validator import (
    ExploitValidationEnricher,
    ExploitValidator,
    NucleiPocValidator,
)
from plugins.red_agent.enrichers.greynoise import GreyNoiseEnricher
from plugins.red_agent.enrichers.osv import OSVEnricher
from plugins.red_agent.enrichers.reachability import ReachabilityEnricher
from plugins.red_agent.enrichers.risk_scorer import RiskScoringEnricher
from plugins.red_agent.enrichers.sigma_hints import SigmaHintEnricher
from plugins.red_agent.enrichers.threat_intel import (
    CensysEnricher,
    OTXEnricher,
    ShodanEnricher,
    VirusTotalEnricher,
)
from plugins.red_agent.enrichers.vex import VEXStatement, VEXStore, VexEnricher

__all__ = [
    "AttackMapperEnricher",
    "CensysEnricher",
    "ComplianceMapperEnricher",
    "EpssKevEnricher",
    "ExploitValidationEnricher",
    "ExploitValidator",
    "GreyNoiseEnricher",
    "NucleiPocValidator",
    "OSVEnricher",
    "OTXEnricher",
    "ReachabilityEnricher",
    "RiskScoringEnricher",
    "ShodanEnricher",
    "SigmaHintEnricher",
    "VEXStatement",
    "VEXStore",
    "VexEnricher",
    "VirusTotalEnricher",
]

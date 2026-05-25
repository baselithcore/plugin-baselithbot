"""Red Agent scanner adapters."""

from plugins.red_agent.scanners.base import Scanner, ScannerKind
from plugins.red_agent.scanners.binary_analyzer import BinaryAnalyzerScanner
from plugins.red_agent.scanners.checkov import CheckovScanner
from plugins.red_agent.scanners.crtsh import CrtShScanner
from plugins.red_agent.scanners.dependency_confusion import (
    DependencyConfusionScanner,
)
from plugins.red_agent.scanners.gitleaks import GitleaksScanner
from plugins.red_agent.scanners.graphql_audit import GraphQLAuditScanner
from plugins.red_agent.scanners.jwt_audit import JWTAuditScanner
from plugins.red_agent.scanners.kube_bench import KubeBenchScanner
from plugins.red_agent.scanners.llm_data_leakage import LLMDataLeakageScanner
from plugins.red_agent.scanners.llm_output_handling import LLMOutputHandlingScanner
from plugins.red_agent.scanners.llm_prompt_injection import LLMPromptInjectionScanner
from plugins.red_agent.scanners.llm_recon import LLMReconScanner
from plugins.red_agent.scanners.llm_tool_abuse import LLMToolAbuseScanner
from plugins.red_agent.scanners.nmap import NmapScanner
from plugins.red_agent.scanners.nuclei import NucleiScanner
from plugins.red_agent.scanners.prowler import ProwlerScanner
from plugins.red_agent.scanners.schemathesis import SchemathesisScanner
from plugins.red_agent.scanners.secure_headers import SecureHeadersScanner
from plugins.red_agent.scanners.self_posture import SelfPostureScanner
from plugins.red_agent.scanners.semgrep import SemgrepScanner
from plugins.red_agent.scanners.sqlmap import SqlmapScanner
from plugins.red_agent.scanners.sslyze import SslyzeScanner
from plugins.red_agent.scanners.subfinder import SubfinderScanner
from plugins.red_agent.scanners.syft_grype import GrypeScanner, SyftScanner
from plugins.red_agent.scanners.trivy import TrivyScanner
from plugins.red_agent.scanners.waf_evasion import WAFEvasionScanner
from plugins.red_agent.scanners.workflow_audit import WorkflowAuditScanner
from plugins.red_agent.scanners.zap import ZapBaselineScanner

REGISTRY: dict[str, type[Scanner]] = {
    "nmap": NmapScanner,
    "nuclei": NucleiScanner,
    "zap": ZapBaselineScanner,
    "sqlmap": SqlmapScanner,
    "trivy": TrivyScanner,
    "sslyze": SslyzeScanner,
    "secure_headers": SecureHeadersScanner,
    "semgrep": SemgrepScanner,
    "gitleaks": GitleaksScanner,
    "syft": SyftScanner,
    "grype": GrypeScanner,
    "checkov": CheckovScanner,
    "prowler": ProwlerScanner,
    "kube_bench": KubeBenchScanner,
    "schemathesis": SchemathesisScanner,
    "llm_recon": LLMReconScanner,
    "llm_prompt_injection": LLMPromptInjectionScanner,
    "llm_tool_abuse": LLMToolAbuseScanner,
    "llm_data_leakage": LLMDataLeakageScanner,
    "llm_output_handling": LLMOutputHandlingScanner,
    "subfinder": SubfinderScanner,
    "crtsh": CrtShScanner,
    "workflow_audit": WorkflowAuditScanner,
    "dependency_confusion": DependencyConfusionScanner,
    "graphql_audit": GraphQLAuditScanner,
    "jwt_audit": JWTAuditScanner,
    "waf_evasion": WAFEvasionScanner,
    "binary_analyzer": BinaryAnalyzerScanner,
    "self_posture": SelfPostureScanner,
}

__all__ = [
    "Scanner",
    "ScannerKind",
    "NmapScanner",
    "NucleiScanner",
    "ZapBaselineScanner",
    "SqlmapScanner",
    "TrivyScanner",
    "SslyzeScanner",
    "SecureHeadersScanner",
    "SemgrepScanner",
    "GitleaksScanner",
    "SyftScanner",
    "GrypeScanner",
    "CheckovScanner",
    "ProwlerScanner",
    "KubeBenchScanner",
    "SchemathesisScanner",
    "LLMReconScanner",
    "LLMPromptInjectionScanner",
    "LLMToolAbuseScanner",
    "LLMDataLeakageScanner",
    "LLMOutputHandlingScanner",
    "SubfinderScanner",
    "CrtShScanner",
    "WorkflowAuditScanner",
    "DependencyConfusionScanner",
    "GraphQLAuditScanner",
    "JWTAuditScanner",
    "WAFEvasionScanner",
    "BinaryAnalyzerScanner",
    "SelfPostureScanner",
    "REGISTRY",
]

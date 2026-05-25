import type { PreflightTargetType, ScanIntensity, TargetKind } from './api';

export type ScannerKind =
  | 'recon'
  | 'dast'
  | 'sast'
  | 'sca'
  | 'secret'
  | 'cspm'
  | 'iac'
  | 'k8s'
  | 'api'
  | 'config'
  | 'threat_intel'
  | 'tls'
  | 'headers'
  | 'sbom'
  | 'malware';

export interface ScannerMeta {
  id: string;
  label: string;
  kind: ScannerKind;
  description: string;
  intensities: ScanIntensity[];
  targets: PreflightTargetType[];
}

export const SCANNER_REGISTRY: ScannerMeta[] = [
  {
    id: 'nmap',
    label: 'Nmap',
    kind: 'recon',
    description: 'Port + service discovery.',
    intensities: ['passive', 'active'],
    targets: ['url', 'hostname', 'ip', 'cidr'],
  },
  {
    id: 'nuclei',
    label: 'Nuclei',
    kind: 'dast',
    description: 'Template-based vuln probing.',
    intensities: ['passive', 'active'],
    targets: ['url', 'hostname', 'ip'],
  },
  {
    id: 'zap',
    label: 'OWASP ZAP',
    kind: 'dast',
    description: 'Baseline / full DAST scan.',
    intensities: ['passive', 'active'],
    targets: ['url'],
  },
  {
    id: 'sqlmap',
    label: 'sqlmap',
    kind: 'dast',
    description: 'Intrusive SQLi exploitation. HITL gated.',
    intensities: ['intrusive'],
    targets: ['url'],
  },
  {
    id: 'trivy',
    label: 'Trivy',
    kind: 'sca',
    description: 'Filesystem / repo SCA + IaC.',
    intensities: ['passive'],
    targets: ['repo'],
  },
  {
    id: 'sslyze',
    label: 'SSLyze',
    kind: 'tls',
    description: 'TLS posture: PCI-DSS 4.0 / NIST SP 800-52 Rev 2.',
    intensities: ['passive', 'active'],
    targets: ['url', 'hostname', 'ip'],
  },
  {
    id: 'secure_headers',
    label: 'Secure Headers',
    kind: 'headers',
    description: 'OWASP Secure Headers Project + CSP analyzer.',
    intensities: ['passive', 'active'],
    targets: ['url', 'hostname', 'ip'],
  },
  {
    id: 'semgrep',
    label: 'Semgrep',
    kind: 'sast',
    description: 'SAST with curated p/ci ruleset (OWASP / CWE).',
    intensities: ['passive'],
    targets: ['repo'],
  },
  {
    id: 'gitleaks',
    label: 'Gitleaks',
    kind: 'secret',
    description: 'Hard-coded secrets detection (CWE-798).',
    intensities: ['passive'],
    targets: ['repo'],
  },
  {
    id: 'syft',
    label: 'Syft',
    kind: 'sbom',
    description: 'SPDX SBOM generation for attestation.',
    intensities: ['passive'],
    targets: ['repo'],
  },
  {
    id: 'grype',
    label: 'Grype',
    kind: 'sca',
    description: 'Vulnerability match against Anchore feeds.',
    intensities: ['passive'],
    targets: ['repo'],
  },
  {
    id: 'checkov',
    label: 'Checkov',
    kind: 'iac',
    description: 'IaC misconfigurations (Terraform, CloudFormation, K8s YAML).',
    intensities: ['passive'],
    targets: ['repo', 'iac'],
  },
  {
    id: 'prowler',
    label: 'Prowler',
    kind: 'cspm',
    description: 'Multi-cloud CSPM benchmarks (CIS, PCI, NIST, ISO).',
    intensities: ['passive', 'active'],
    targets: ['cloud_account'],
  },
  {
    id: 'kube_bench',
    label: 'kube-bench',
    kind: 'k8s',
    description: 'CIS Kubernetes Benchmark posture audit.',
    intensities: ['passive'],
    targets: ['k8s_cluster'],
  },
  {
    id: 'self_posture',
    label: 'Self Posture',
    kind: 'config',
    description:
      'CIS-aligned audit of the host running the orchestrator (kernel, SSH, sudo, SUID, listening ports, secrets in env). Pure-Python, no subprocess.',
    intensities: ['passive'],
    targets: ['system'],
  },
  {
    id: 'binary_analyzer',
    label: 'Binary Analyzer',
    kind: 'malware',
    description:
      'Static analysis of uploaded executables (PE/ELF/Mach-O) — IOCs, signing, suspicious imports.',
    intensities: ['passive'],
    targets: ['binary'],
  },
  {
    id: 'schemathesis',
    label: 'Schemathesis',
    kind: 'api',
    description: 'Property-based fuzzing of OpenAPI / GraphQL specs.',
    intensities: ['active'],
    targets: ['api_spec', 'url'],
  },
];

export const SCANNER_META: Record<string, ScannerMeta> = Object.fromEntries(
  SCANNER_REGISTRY.map((s) => [s.id, s])
);

export const KNOWN_SCANNERS = SCANNER_REGISTRY.map((s) => s.id);

export function scannersForIntensity(intensity: ScanIntensity): string[] {
  return SCANNER_REGISTRY.filter((s) => s.intensities.includes(intensity)).map((s) => s.id);
}

export const SCANNERS_BY_INTENSITY: Record<ScanIntensity, string[]> = {
  passive: scannersForIntensity('passive'),
  active: scannersForIntensity('active'),
  intrusive: scannersForIntensity('intrusive'),
};

export const TARGET_KIND_TO_PREFLIGHT_TYPES: Record<TargetKind, PreflightTargetType[]> = {
  web: ['url', 'hostname'],
  network: ['ip', 'cidr', 'hostname'],
  cloud: ['cloud_account'],
  host: ['hostname', 'ip', 'system'],
  repo: ['repo', 'iac'],
  binary: ['binary'],
};

export function scannersForTargetKind(kind: TargetKind): ScannerMeta[] {
  const allowed = new Set(TARGET_KIND_TO_PREFLIGHT_TYPES[kind]);
  return SCANNER_REGISTRY.filter((s) => s.targets.some((t) => allowed.has(t)));
}

/**
 * Refines ``scannersForTargetKind`` using the target's raw value when
 * available. Some kinds map to multiple low-level types (e.g. ``host``
 * accepts both an enrolled daemon and the in-process ``system:local``
 * target). The value disambiguates which scanners actually make sense.
 */
export function scannersForTarget(kind: TargetKind, value: string): ScannerMeta[] {
  const all = scannersForTargetKind(kind);
  if (value.startsWith('system:')) {
    // The orchestrator host has no network surface from the scanner's
    // point of view — only the in-process posture audit applies.
    return all.filter((s) => s.targets.includes('system'));
  }
  if (kind === 'host') {
    // ``agent:<uuid>`` targets resolve to a remote host through the
    // daemon's executor; the in-process ``self_posture`` adapter would
    // audit the wrong machine.
    return all.filter((s) => !s.targets.includes('system') || s.targets.length > 1);
  }
  return all;
}

export const KIND_LABEL: Record<ScannerKind, string> = {
  recon: 'Recon',
  dast: 'DAST',
  sast: 'SAST',
  sca: 'SCA',
  secret: 'Secrets',
  cspm: 'Cloud',
  iac: 'IaC',
  k8s: 'Kubernetes',
  api: 'API',
  config: 'Config',
  threat_intel: 'Threat Intel',
  tls: 'TLS',
  headers: 'Headers',
  sbom: 'SBOM',
  malware: 'Binary',
};

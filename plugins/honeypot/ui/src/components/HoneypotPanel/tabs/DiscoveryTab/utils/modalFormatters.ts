/**
 * Formatting helpers for Discovery Detail Modal
 */

/** Convert snake_case or technical names to readable titles */
export function formatAnomalyType(type: string): string {
  const typeMap: Record<string, string> = {
    potential_zeroday: 'Potential Zero-Day Exploit',
    zeroday: 'Zero-Day Vulnerability',
    novel: 'Novel Attack Pattern',
    command_injection: 'Command Injection',
    sql_injection: 'SQL Injection',
    path_traversal: 'Path Traversal',
    xss: 'Cross-Site Scripting (XSS)',
    rce: 'Remote Code Execution',
    lfi: 'Local File Inclusion',
    rfi: 'Remote File Inclusion',
    ssrf: 'Server-Side Request Forgery',
    exploit: 'Exploit Attempt',
    attack_chain: 'Multi-Stage Attack Chain',
    threat_intel: 'Threat Intelligence Match',
    intel: 'Intelligence Indicator',
    botnet: 'Botnet Activity',
    cc_beacon: 'C&C Beacon',
    scanning: 'Port/Service Scanning',
    brute_force: 'Brute Force Attack',
    credential_stuffing: 'Credential Stuffing',
  };

  if (typeMap[type.toLowerCase()]) {
    return typeMap[type.toLowerCase()];
  }

  return type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Format centrality score with contextual meaning */
export function formatCentralityScore(
  score: number,
  type: 'degree' | 'betweenness'
): { value: string; label: string; level: 'low' | 'medium' | 'high' } {
  const percentage = (score * 100).toFixed(1);

  if (type === 'degree') {
    if (score >= 0.5)
      return { value: percentage + '%', label: 'Highly connected hub', level: 'high' };
    if (score >= 0.2)
      return { value: percentage + '%', label: 'Moderately connected', level: 'medium' };
    return { value: percentage + '%', label: 'Low connectivity', level: 'low' };
  } else {
    if (score >= 0.3)
      return { value: percentage + '%', label: 'Critical bridge node', level: 'high' };
    if (score >= 0.1)
      return { value: percentage + '%', label: 'Intermediate relay', level: 'medium' };
    return { value: percentage + '%', label: 'Peripheral node', level: 'low' };
  }
}

/** Format threat score with visual indicator */
export function getThreatLevel(score: number): { label: string; class: string } {
  if (score >= 75) return { label: 'Critical Threat', class: 'threat-critical' };
  if (score >= 50) return { label: 'High Threat', class: 'threat-high' };
  if (score >= 25) return { label: 'Medium Threat', class: 'threat-medium' };
  return { label: 'Low Threat', class: 'threat-low' };
}

"""Payload analysis prompt."""

from typing import Any, Dict, List

from ._core import RESEARCH_ANALYST_PERSONA


def research_payload_analysis_prompt(
    honeypot_name: str,
    payload_excerpts: List[Dict[str, Any]],
    protocol: str = "mixed",
) -> str:
    """Generate prompt for payload analysis section.

    Args:
        honeypot_name: Honeypot identifier
        payload_excerpts: Sanitized payload samples with metadata
        protocol: Primary protocol observed

    Returns:
        Formatted prompt for LLM
    """
    payload_data = []
    for p in payload_excerpts[:15]:
        payload_data.append(
            {
                "category": p.get("category", "unknown"),
                "severity": p.get("severity", "medium"),
                "excerpt": p.get("excerpt", "")[
                    :300
                ],  # Increased from 200 for more context
                "source_country": p.get("source_country", "Unknown"),
                "timestamp": p.get("timestamp", ""),
                "protocol": p.get("protocol", "unknown"),
                "ai_classification": p.get("ai_classification", ""),
            }
        )

    # Format payloads with full context for better analysis
    formatted_payloads = []
    for i, p in enumerate(payload_data, 1):
        formatted_payloads.append(
            f"""
**Payload {i}**:
- Time: {p["timestamp"]}
- Category: {p["category"]} | Severity: {p["severity"]}
- Protocol: {p["protocol"]} | Source: {p["source_country"]}
- AI Classification: {p["ai_classification"] or "Not classified"}
- Content: {p["excerpt"]}
"""
        )

    return f"""{RESEARCH_ANALYST_PERSONA}

**Task**: Perform an EXHAUSTIVE, FORENSICALLY-DETAILED PAYLOAD DECONSTRUCTION for the {honeypot_name} honeypot.

**Context**:
- Honeypot: {honeypot_name}
- Primary protocol: {protocol}
- Payload samples: {len(payload_excerpts)}

**CRITICAL FORMATTING REQUIREMENT**:
You MUST use EXACT markdown table syntax for the Notable Payloads table:
- Each row MUST have exactly 4 cells separated by `|`
- NO line breaks within cells
- Align columns with `:---` syntax
- Example of CORRECT format:

| Category | Severity | Technique | Description |
| :--- | :--- | :--- | :--- |
| RCE | Critical | Log4Shell (CVE-2024-21762) | JNDI injection targeting vulnerable FortiGate SSL VPN |
| Command Injection | High | Mirai Variant | Wget-based payload delivery with chmod execution |

**Payload Data** (sanitized, with full context):
{"".join(formatted_payloads)}

**Analysis Requirements** (MINIMUM 200 WORDS PER SUBSECTION):

1. **Attack Classification** (300+ words):
   - Identify EXACT techniques (e.g., "Log4Shell CVE-2024-21762", not just "RCE")
   - Group by attack family (Mirai, Mozi, Kinsing, APT-style)
   - Cite specific CVE numbers if recognizable
   - Analyze payload sophistication (script kiddie vs. advanced)
   - Identify tool signatures (nmap, sqlmap, custom scripts)

2. **Obfuscation & Evasion Techniques** (250+ words):
   - Identify base64, hex, URL encoding
   - Detect whitespace/comment evasion
   - Analyze string concatenation tricks
   - Note anti-detection measures (user-agent spoofing, polymorphism)
   - Rate evasion sophistication (1-10 scale with justification)

3. **Exploit Chain Reconstruction** (300+ words):
   - Reconstruct the FULL intended attack sequence
   - Example: "Initial Access (SSH brute force) -> Download (wget malicious.sh) -> Persistence (cron job) -> C2 Beaconing (HTTP POST to attacker IP)"
   - Identify each stage: Reconnaissance, Weaponization, Delivery, Exploitation, Installation, C2, Actions on Objectives
   - Infer attacker intent (cryptomining, botnet recruitment, data exfiltration)

4. **Malware Attribution** (200+ words):
   - Correlate with known botnets (Mirai signature: "busybox wget", Mozi: specific C2 patterns)
   - Match to threat intelligence feeds
   - Identify geographic/linguistic indicators
   - Rate confidence in attribution (High/Medium/Low with evidence)

5. **Notable Payloads Table** (STRICT MARKDOWN):
   - Select the 5-8 MOST SIGNIFICANT payloads
   - Each row MUST be a single line (no multi-line cells)
   - Description column: 1-sentence technical summary (max 100 chars)

**FORMAT**:
## Payload Analysis

### Attack Classification
[Detailed analysis with specific CVE numbers, malware families, and tool signatures. MINIMUM 300 words. Reference specific payloads by number.]

### Obfuscation & Evasion Techniques
[In-depth analysis of how attackers attempted to hide intent. MINIMUM 250 words. Cite payload examples.]

### Exploit Chain Reconstruction
[Step-by-step reconstruction of the attack kill chain. MINIMUM 300 words. Use "Payload X demonstrates..." format.]

### Malware Attribution
[Correlation with known threat actors and malware families. MINIMUM 200 words. Cite intelligence sources if applicable.]

### Notable Payloads

| Category | Severity | Technique | Description |
| :--- | :--- | :--- | :--- |
| [Exact category] | [Critical/High/Medium] | [Specific CVE or technique name] | [Single-line technical description] |

### Sophistication Assessment
[Evaluation of attacker skill level, automation vs. manual, and threat actor profiling. MINIMUM 150 words.]

**VALIDATION CHECKLIST** (confirm before generating):
- [ ] Each subsection meets minimum word count
- [ ] All CVEs and malware families are explicitly named
- [ ] Notable Payloads table has exactly 4 columns per row
- [ ] No line breaks within table cells
- [ ] At least 3 specific payload numbers are referenced in analysis
- [ ] Sophistication score (1-10) is provided with justification

Generate the comprehensive payload analysis now:"""

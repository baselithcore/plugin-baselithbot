# app/agents/metadata/extractors/patterns.py

GOAL_KEYWORDS = [
    r"obiettivo",
    r"obiettivi",
    r"scopo",
    r"finalità",
    r"purpose",
    r"mission",
    r"ambito",
    r"perimetro",
    r"contesto",
    r"background",
    r"context",
    r"description",
]

STAKEHOLDER_PATTERNS = [
    r"([A-Z][a-z]+ [A-Z][a-z]+),?\s*\(([a-zA-Z\s]+)\)",  # "Mario Rossi (PM)"
    r"(?:Owner|Lead|Responsabile)[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)",  # "Owner: Mario Rossi"
    r"(?:Participants|Partecipanti)[:\s]+((?:[A-Z][a-z]+ [A-Z][a-z]+(?:,\s*)?)+)",  # List of names
    r"([a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,})",  # email
    r"(Team\s+[A-Z][a-zA-Z]+)",  # "Team Frontend"
    r"Referente[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)",  # "Referente: Mario Rossi"
    r"Attori[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)",  # "Attori: Mario Rossi"
]

BLACKLIST_TERMS = [
    "document",
    "documento",
    "plan",
    "piano",
    "report",
    "analisi",
    "analysis",
    "system",
    "sistema",
    "server",
    "api",
    "test",
    "story",
    "epic",
    "milestone",
    "release",
    "sprint",
    "meeting",
    "riunione",
    "marketing cloud",
    "salesforce",
    "jira",
    "confluence",
    "aws",
    "azure",
    "google",
    "cloud",
    "specifications",
    "specifiche",
    "recovery",
    "disaster",
]

TIMELINE_PATTERNS = [
    r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",  # dates
    r"(?:Deadline|Scadenza|Due Date)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",  # "Do: 12/12/2024"
    r"(Q[1-4]\s+\d{4})",  # quarters
    r"(entro\s+[a-z]+\s+\d{4})",  # "entro dicembre 2024"
    r"(Release\s+[\d.]+)",  # "Release 1.0"
    r"(MVP|Alpha|Beta|GA|Go-Live|Go Live)",  # milestones keywords
]

TECH_KEYWORDS = [
    # Frameworks
    "React",
    "Angular",
    "Vue",
    "Django",
    "Flask",
    "FastAPI",
    "Spring",
    "Express",
    "Next.js",
    "Nuxt",
    "Laravel",
    "Rails",
    # Languages
    "Python",
    "JavaScript",
    "TypeScript",
    "Java",
    "C#",
    "Go",
    "Rust",
    "PHP",
    "Ruby",
    "Kotlin",
    "Swift",
    # Databases
    "PostgreSQL",
    "MySQL",
    "MongoDB",
    "Redis",
    "Elasticsearch",
    "DynamoDB",
    "Cassandra",
    "Neo4j",
    # Cloud/Infra
    "AWS",
    "Azure",
    "GCP",
    "Docker",
    "Kubernetes",
    "Jenkins",
    "GitHub Actions",
    "GitLab CI",
    "Terraform",
    # Enterprise
    "Salesforce",
    "Marketing Cloud",
    "Jira",
    "Confluence",
    "ServiceNow",
    "SAP",
]

RISK_KEYWORDS = [
    r"rischio",
    r"risk",
    r"problema",
    r"issue",
    r"criticità",
    r"attenzione",
    r"warning",
    r"concern",
]

MODULE_PATTERNS = [
    r"(?:modulo|feature|funzionalità|funzionalita|workflow)\s+(?:di\s+)?([A-Za-z0-9][^\n,.;:]{2,80})",
    r"(?:area|ambito)\s+(?:di\s+)?([A-Za-z0-9][^\n,.;:]{2,80})",
]

INTEGRATION_PATTERNS = [
    r"(?:integrazione|interfaccia|sincronizzazione|collegamento)\s+(?:con|verso)\s+([A-Za-z0-9][^\n,.;:]{2,80})",
    r"(?:esporre|consumare|invocare)\s+(?:le\s+)?api\s+([A-Za-z0-9][^\n,.;:]{2,80})",
]

CONSTRAINT_KEYWORDS = [
    "vincolo",
    "constraint",
    "gdpr",
    "compliance",
    "sla",
    "tempo massimo",
    "entro ",
    "non deve",
    "deve garantire",
    "obbligatorio",
]

BUSINESS_RULE_KEYWORDS = [
    "regola",
    "business rule",
    "solo se",
    "almeno",
    "al massimo",
    "non può",
    "non puo",
    "deve essere",
    "è consentito",
    "e consentito",
]

ASSUMPTION_KEYWORDS = [
    "assunzione",
    "presupposto",
    "si assume",
    "assume che",
    "dipende da",
]

OPEN_QUESTION_KEYWORDS = [
    "da chiarire",
    "da confermare",
    "tbd",
    "to be defined",
    "to be confirmed",
]

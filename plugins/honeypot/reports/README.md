# AI-Powered Attack Pattern Research

Academic-grade cybersecurity research report generation with AI-powered insights using the Baselith-Core Framework.

## Features

- **AI-Powered Analysis**: Use LLM to generate professional, contextual report narratives
- **Multiple Report Types**: Executive, Technical, Threat Intel, Compliance, Incident, Pentest
- **Flexible Providers**: Support for Ollama (local) and OpenAI (cloud)
- **Graceful Fallback**: Automatic fallback to template-based generation if LLM fails
- **Enterprise-Grade**: Output matches CrowdStrike, Splunk, and other professional platforms

## Configuration

### Environment Variables

Configure your LLM provider in `.env`:

```bash
# LLM Provider Configuration
LLM_PROVIDER=ollama              # Options: ollama, openai
LLM_MODEL=llama3.2:latest        # Model name
LLM_API_BASE=http://localhost:11434  # For Ollama
LLM_API_KEY=                     # For OpenAI (sk-...)
LLM_TEMPERATURE=0.7              # Generation temperature (0.0-2.0)
```

### Provider Options

#### Ollama (Local, Recommended for Development)

```bash
# Install Ollama: https://ollama.ai
# Pull model
ollama pull llama3.2

# Configure .env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2:latest
LLM_API_BASE=http://localhost:11434
```

**Best Models for Security Reports:**

- `llama3.2:latest` - Fast, balanced (4GB VRAM)
- `mixtral:8x7b` - High quality, slower (26GB VRAM)
- `codellama:34b` - Technical focus (19GB VRAM)

#### OpenAI (Cloud, Production Ready)

```bash
# Get API key: https://platform.openai.com/api-keys

# Configure .env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo-preview
LLM_API_KEY=sk-your-api-key-here
LLM_TEMPERATURE=0.7
```

**Best Models for Security Reports:**

- `gpt-4-turbo-preview` - Highest quality
- `gpt-4` - Balanced quality/speed
- `gpt-3.5-turbo` - Fast, cost-effective

## Usage

### Basic Report Generation

```python
from plugins.honeypot.reports import ReportService, ReportConfig, ReportType

# Initialize service (LLM enabled by default)
service = ReportService(use_llm=True)

# Configure report
config = ReportConfig(
    report_type=ReportType.TECHNICAL,
    time_range_hours=168,  # 7 days
    organization_name="Acme Corp",
    sections=[
        ReportSection.EXECUTIVE_SUMMARY,
        ReportSection.THREAT_LANDSCAPE,
        ReportSection.ATTACK_ANALYTICS,
        ReportSection.GEO_ANALYSIS,
        ReportSection.RECOMMENDATIONS,
    ]
)

# Generate report
report = await service.generate_report(config=config)
```

### Disable LLM (Template Only)

```python
# Use template-based generation only
service = ReportService(use_llm=False)
report = await service.generate_report(config=config)
```

### API Endpoint

```bash
# Generate report with preview
curl -X GET "http://localhost:8000/honeypot/reports/preview?report_type=technical&time_range_hours=168"

# Generate and download PDF
curl -X POST "http://localhost:8000/honeypot/reports/generate/pdf" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "report_type": "threat_intel",
      "time_range_hours": 168,
      "organization_name": "Acme Corp"
    }
  }' --output report.pdf
```

### Research Overview (Abstract)

- **Template**: Statistical summary of the observation period
- **LLM**: Peer-reviewed style abstract with context, significance, and quantified results

### Key Findings

- **Template**: List of top alerts and categories
- **LLM**: 5-8 specific, quantified analytical observations prioritised by research significance

### MITRE ATT&CK Mapping

- **Template**: static mapping of common techniques
- **LLM**: Dynamic mapping of observed behaviors to specific ATT&CK Technique IDs (Txxxx) with evidence and confidence scoring

### Attack Pattern Analysis

- **Template**: Static pattern descriptions
- **LLM**: Behavioral analysis, attacker sophistication assessment, and campaign correlation

### Statistical & Temporal Analysis

- **Template**: Basic count distribution
- **LLM**: Detailed statistical metrics, ratio analysis, and temporal trend cycles (hourly/daily)

## Advanced Features

### Custom Report Types

```python
config = ReportConfig(
    report_type=ReportType.EXECUTIVE,  # Board-level briefing
    sections=[
        ReportSection.EXECUTIVE_SUMMARY,
        ReportSection.THREAT_LANDSCAPE,
    ],
    organization_name="Acme Corp",
    classification="CONFIDENTIAL"
)
```

### Time Range Options

```python
config = ReportConfig(
    time_range_hours=24,    # Last 24 hours
    # time_range_hours=168, # Last 7 days (default)
    # time_range_hours=720, # Last 30 days
)
```

### Filtering by Honeypot

```python
config = ReportConfig(
    honeypot_id="hp-ssh-prod-01",  # Filter to specific honeypot
)
```

## Report Types Reference

| Type | Audience | LLM Enhancement | Sections |
|------|----------|-----------------|----------|
| **Executive** | C-level, Board | Business risk translation | Summary, Landscape, Recommendations |
| **Technical** | Security Engineers | Detailed TTPs, MITRE ATT&CK | Summary, Analytics, Timeline, IOCs |
| **Threat Intel** | SOC, Analysts | Attribution, campaigns, IOCs | Landscape, Botnets, Geo, IOCs |
| **Compliance** | Auditors | Logging completeness, policies | Summary, Analytics, Pentest |
| **Incident** | IR Team | Timeline narrative, root cause | Summary, Timeline, Analytics, IOCs |
| **Pentest** | Security Team | Vulnerability prioritization | Summary, Pentest, CVEs, Recommendations |

## Performance Considerations

### LLM Response Times

- **Ollama (llama3.2)**: 2-10 seconds per section
- **OpenAI (gpt-4)**: 3-8 seconds per section
- **OpenAI (gpt-3.5)**: 1-3 seconds per section

### Token Usage (OpenAI)

- Executive Summary: ~500-1000 tokens
- Threat Analysis: ~800-1500 tokens
- Recommendations: ~300-800 tokens
- **Total Report**: ~2000-4000 tokens (~$0.01-0.02 per report with gpt-4)

### Optimization Tips

1. **Ollama**: Use smaller models (llama3.2) for faster generation
2. **OpenAI**: Use gpt-3.5-turbo for cost/speed balance
3. **Caching**: LLM responses are cached for 1 hour (configurable)
4. **Async**: Multiple sections generated in parallel

## Error Handling

The service automatically falls back to template-based generation if:

- LLM service is unavailable
- API key is invalid
- Rate limit exceeded
- Model doesn't support required features

```python
# Logs will show:
# INFO: Generating executive summary with LLM
# WARNING: LLM executive summary failed, falling back to template
# INFO: Generating executive summary with templates
```

## Troubleshooting

### Ollama Issues

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Check logs
docker logs ollama  # If using Docker

# Pull/update model
ollama pull llama3.2:latest
```

### OpenAI Issues

```bash
# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $LLM_API_KEY"

# Check usage
# Visit: https://platform.openai.com/usage
```

### LLM Not Being Used

Check logs for initialization:

```text
INFO: ReportService initialized with LLM-enhanced generation enabled
INFO: LLM service initialized successfully
```

If you see:

```text
WARNING: Failed to initialize LLM service: ... Falling back to templates.
```

Check:

1. `.env` file has correct `LLM_PROVIDER` and `LLM_API_KEY`/`LLM_API_BASE`
2. Ollama/OpenAI service is running and accessible
3. Model exists: `ollama list` or check OpenAI model name

## Examples

### Example 1: Quick Executive Briefing

```bash
curl -X GET "http://localhost:8000/honeypot/reports/preview?report_type=executive&time_range_hours=24"
```

**Output** (LLM-enhanced):

```markdown
## Executive Overview

### Security Posture Status: ELEVATED

Over the past 24 hours, Acme Corp's security infrastructure successfully
identified and neutralized 1,247 attempted intrusions from 89 distinct
threat actors. The automated defense systems demonstrated strong
resilience, with no successful breaches detected.

**Business Impact Assessment:**
The elevated threat level stems from coordinated scanning activity
originating from Eastern Europe (45% of traffic), likely associated with
opportunistic botnet campaigns rather than targeted attacks. Critical
infrastructure remained secure throughout the period.

**Strategic Recommendation:**
Implement enhanced monitoring for SSH and RDP services, which accounted
for 78% of attempted intrusions. Consider deploying additional rate-limiting
controls to reduce noise from automated scanners.
```

### Example 2: Technical Threat Intelligence

```python
config = ReportConfig(
    report_type=ReportType.THREAT_INTEL,
    time_range_hours=168,
    sections=[
        ReportSection.THREAT_LANDSCAPE,
        ReportSection.BOTNET_DISCOVERY,
        ReportSection.IOC_LIST,
    ]
)

report = await service.generate_report(config)
```

**Output** includes:

- AI-analyzed botnet cluster sophistication scores
- C&C infrastructure attribution
- Campaign correlation across IOCs
- Defensive recommendations prioritized by threat level

## Best Practices

1. **Use Ollama for Development**: Free, local, no API costs
2. **Use OpenAI for Production**: Better quality, faster, more reliable
3. **Enable LLM for Important Reports**: Executive, Threat Intel, Incident
4. **Use Templates for Automated Reports**: Scheduled daily/weekly reports
5. **Set Appropriate Temperature**: 0.7 for balanced, 0.3 for factual, 1.0 for creative
6. **Review LLM Output**: Always verify AI-generated recommendations before action

## License

Part of the Baselith-Core Honeypot System. See main project LICENSE.

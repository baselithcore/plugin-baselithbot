"""CSS Part 2: callouts, key findings, payload, correlation, metric cards, MISP."""

_PART2 = """
/* =========================================================================
   Professional Enhancement CSS (Phase 4)
   ========================================================================= */

/* Callout Boxes - For highlighting key findings */
.callout {
    border-radius: 8px;
    padding: 16px 20px;
    margin: 1.5em 0;
    border-left: 4px solid;
    page-break-inside: avoid;
    position: relative;
}
.callout-critical {
    background: linear-gradient(135deg, #fff5f5 0%, #ffe5e5 100%);
    border-color: #ff4757;
}
.callout-warning {
    background: linear-gradient(135deg, #fff8e6 0%, #fff0c2 100%);
    border-color: #ffa502;
}
.callout-info {
    background: linear-gradient(135deg, #e8f4fd 0%, #d1e9f7 100%);
    border-color: #00b4d8;
}
.callout-success {
    background: linear-gradient(135deg, #e8f8f0 0%, #d4f0e3 100%);
    border-color: #2ed573;
}
.callout-title {
    font-weight: 700;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 11pt;
}
.callout-icon {
    font-size: 16pt;
}
.callout-content {
    font-size: 10pt;
    line-height: 1.5;
    color: #333;
}

/* Key Findings Box - Prominent highlight section */
.key-findings-box {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    color: white;
    border-radius: 12px;
    padding: 24px 30px;
    margin: 2em 0;
    page-break-inside: avoid;
}
.key-findings-box h3 {
    color: #00b4d8;
    margin-top: 0;
    margin-bottom: 16px;
    font-size: 14pt;
    display: flex;
    align-items: center;
    gap: 10px;
}
.key-findings-list {
    list-style: none;
    padding: 0;
    margin: 0;
}
.key-findings-list li {
    padding: 8px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    font-size: 10pt;
    display: flex;
    align-items: flex-start;
    gap: 10px;
}
.key-findings-list li:last-child {
    border-bottom: none;
}
.finding-icon {
    color: #00b4d8;
    font-weight: bold;
}

/* Payload Excerpt Styling */
.payload-section {
    background: #f8f9fa;
    border-radius: 12px;
    padding: 24px;
    margin: 2em 0;
    border: 1px solid #e9ecef;
}
.payload-section h3 {
    color: #1a1a2e;
    margin-top: 0;
    margin-bottom: 20px;
    font-size: 13pt;
}
.payload-sample {
    background: white;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 16px;
    border: 1px solid #dee2e6;
    page-break-inside: avoid;
}
.payload-sample:last-child {
    margin-bottom: 0;
}
.payload-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
}
.payload-category {
    font-weight: 600;
    color: #1a1a2e;
    font-size: 11pt;
}
.severity-badge {
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 8pt;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.severity-critical {
    background: #ff4757;
    color: white;
}
.severity-high {
    background: #ff7f50;
    color: white;
}
.severity-medium {
    background: #ffa502;
    color: #333;
}
.severity-low {
    background: #2ed573;
    color: white;
}
.payload-box {
    background: #1a1a2e;
    color: #00ff00;
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    padding: 12px 16px;
    border-radius: 6px;
    font-size: 9pt;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-all;
    line-height: 1.4;
}
.payload-meta {
    display: flex;
    gap: 20px;
    margin-top: 10px;
    font-size: 8pt;
    color: #666;
}
.payload-meta span {
    display: flex;
    align-items: center;
    gap: 4px;
}

/* Discovery Insights Section */
.discovery-insights {
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    border-radius: 12px;
    padding: 24px;
    margin: 2em 0;
    border: 1px solid #dee2e6;
}
.discovery-insights h3 {
    color: #16213e;
    margin-top: 0;
    display: flex;
    align-items: center;
    gap: 10px;
}
.insight-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
    margin-top: 16px;
}
.insight-card {
    background: white;
    padding: 16px;
    border-radius: 8px;
    border: 1px solid #dee2e6;
}
.insight-card-title {
    font-size: 9pt;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
}
.insight-card-value {
    font-size: 20pt;
    font-weight: bold;
    color: #00b4d8;
}
.insight-card-label {
    font-size: 9pt;
    color: #888;
    margin-top: 4px;
}

/* Correlation Section */
.correlation-section {
    margin: 2em 0;
}
.correlation-card {
    background: white;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 12px;
    border-left: 4px solid #9d4edd;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}
.correlation-type {
    font-size: 9pt;
    color: #9d4edd;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 6px;
}
.correlation-confidence {
    float: right;
    background: #e8f4fd;
    color: #00b4d8;
    padding: 2px 10px;
    border-radius: 10px;
    font-size: 9pt;
    font-weight: 600;
}
.correlation-evidence {
    font-size: 10pt;
    color: #333;
    margin-bottom: 8px;
}
.correlation-ips {
    font-size: 9pt;
    color: #666;
}
.correlation-ips code {
    background: #f4f4f4;
    padding: 1px 6px;
    border-radius: 3px;
    margin: 0 2px;
}

/* Metric Cards for Summary */
.metric-cards {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin: 2em 0;
}
.metric-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    color: white;
    padding: 20px;
    border-radius: 10px;
    text-align: center;
}
.metric-card-icon {
    font-size: 24pt;
    margin-bottom: 8px;
}
.metric-card-value {
    font-size: 24pt;
    font-weight: bold;
    color: #00b4d8;
}
.metric-card-label {
    font-size: 9pt;
    color: #aaa;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-top: 4px;
}

/* MISP Status Box */
.misp-status-box {
    background: linear-gradient(135deg, #e8f4fd 0%, #d1e9f7 100%);
    border-radius: 8px;
    padding: 16px 20px;
    margin: 1.5em 0;
    border: 1px solid #b8daef;
    display: flex;
    align-items: center;
    gap: 16px;
}
.misp-icon {
    font-size: 24pt;
}
.misp-info {
    flex: 1;
}
.misp-title {
    font-weight: 600;
    color: #16213e;
    font-size: 11pt;
}
.misp-detail {
    font-size: 9pt;
    color: #666;
    margin-top: 4px;
}
.misp-sync-bar {
    width: 120px;
    height: 8px;
    background: #ddd;
    border-radius: 4px;
    overflow: hidden;
}
.misp-sync-fill {
    height: 100%;
    background: linear-gradient(90deg, #00b4d8, #2ed573);
    border-radius: 4px;
}
"""

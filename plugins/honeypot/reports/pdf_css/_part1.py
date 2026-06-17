"""CSS Part 1: cover page, table of contents."""

_PART1 = """
/* Cover Page Styles - Modern Cybersecurity Theme */
.cover-page {
    height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    text-align: center;
    padding: 40px 50px;
    background: linear-gradient(145deg, #0a0a12 0%, #1a1a2e 40%, #16213e 70%, #0f3460 100%);
    color: white;
    position: relative;
}
.cover-page::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background:
        radial-gradient(circle at 20% 80%, rgba(0, 180, 216, 0.1) 0%, transparent 40%),
        radial-gradient(circle at 80% 20%, rgba(157, 78, 221, 0.1) 0%, transparent 40%);
    pointer-events: none;
}
.cover-header {
    position: relative;
    z-index: 1;
}
.cover-brand {
    margin-bottom: 20px;
}
.cover-logo {
    font-size: 56pt;
    margin-bottom: 10px;
}
.cover-institution {
    font-size: 16pt;
    letter-spacing: 4px;
    text-transform: uppercase;
    color: #00b4d8;
    font-weight: 600;
}
.cover-tagline {
    font-size: 10pt;
    color: #888;
    margin-top: 8px;
    letter-spacing: 2px;
}
.cover-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    position: relative;
    z-index: 1;
}
.cover-threat-badge {
    display: inline-block;
    padding: 8px 24px;
    border: 2px solid;
    border-radius: 20px;
    font-size: 10pt;
    font-weight: bold;
    letter-spacing: 2px;
    margin-bottom: 30px;
}
.cover-title {
    font-size: 32pt;
    font-weight: 800;
    margin-bottom: 15px;
    color: white;
    border-bottom: none;
    line-height: 1.2;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.cover-subtitle {
    font-size: 16pt;
    color: #9d4edd;
    margin-bottom: 30px;
    font-weight: 300;
}
.cover-divider {
    width: 100px;
    height: 3px;
    background: linear-gradient(90deg, #00b4d8, #9d4edd);
    margin: 0 auto 30px;
}
.cover-stats {
    display: flex;
    justify-content: center;
    gap: 40px;
    margin-top: 20px;
}
.cover-stat {
    text-align: center;
    background: rgba(255, 255, 255, 0.05);
    padding: 20px 25px;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.1);
}
.cover-stat-icon {
    font-size: 24pt;
    margin-bottom: 8px;
}
.cover-stat-value {
    font-size: 28pt;
    font-weight: bold;
    color: #00b4d8;
}
.cover-stat-label {
    font-size: 9pt;
    color: #aaa;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 5px;
}
.cover-footer {
    position: relative;
    z-index: 1;
    margin-top: 30px;
    padding-top: 20px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
}
.cover-meta-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px 40px;
    text-align: left;
    max-width: 600px;
    margin: 0 auto 20px;
}
.cover-meta-item {
    display: flex;
    justify-content: space-between;
    padding: 5px 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
.cover-meta-label {
    font-size: 9pt;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.cover-meta-value {
    font-size: 9pt;
    color: #ddd;
    font-weight: 500;
}
.cover-org {
    font-size: 11pt;
    color: #9d4edd;
    font-weight: bold;
    margin-bottom: 10px;
}
.cover-confidential {
    font-size: 8pt;
    color: #ff4757;
    letter-spacing: 2px;
    text-transform: uppercase;
}

/* Table of Contents */
.toc {
    padding: 30px 40px;
}
.toc h2 {
    text-align: center;
    margin-bottom: 30px;
    font-size: 18pt;
    color: #1a1a2e;
}
.toc-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 25px;
}
.toc-section {
    background: #f8f9fa;
    padding: 20px;
    border-radius: 8px;
    border-left: 4px solid #00b4d8;
}
.toc-section-title {
    font-weight: bold;
    color: #1a1a2e;
    margin-bottom: 12px;
    font-size: 11pt;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.toc-list {
    list-style: none;
    padding: 0;
    margin: 0;
}
.toc-list li {
    padding: 6px 0;
    border-bottom: 1px dashed #ddd;
    font-size: 10pt;
}
.toc-list li:last-child {
    border-bottom: none;
}
.toc-list a {
    color: #333;
    text-decoration: none;
}
.toc-list a:hover {
    color: #00b4d8;
}
"""

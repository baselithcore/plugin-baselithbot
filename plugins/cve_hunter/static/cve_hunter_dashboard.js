class CVEHunterDashboard {
  constructor() {
    this.apiBase = '/api/cve_hunter';
    this.init();
  }

  async init() {
    this.renderLayout();
    await this.loadStats();
    await this.loadCVEs();
    this.setupEventListeners();

    // Auto-refresh stats every minute
    setInterval(() => this.loadStats(), 60000);

    // Start live terminal polling
    this.startTerminalPolling();
  }

  async startTerminalPolling() {
    const terminal = document.getElementById('cve-terminal-output');
    if (!terminal) return;

    const poll = async () => {
      try {
        const response = await fetch(`${this.apiBase}/discovery/logs`);
        if (!response.ok) return;

        const logs = await response.json();

        // Render logs (reverse order for terminal feel)
        const content = logs
          .map((log) => {
            let className = 'cve-term-log';
            let prefix = `[${new Date(log.timestamp).toLocaleTimeString()}] `;

            if (log.is_alert) className = 'cve-term-alert';
            if (log.is_error) className = 'cve-term-error';

            return `<div class="${className}">${prefix}${log.message}</div>`;
          })
          .reverse()
          .join('');

        // Add cursor at bottom (which is visually top due to reverse-column)
        terminal.innerHTML = `<div class="cve-term-cursor">_</div>` + content;
      } catch (e) {
        // Silent fail for polling
      }
    };

    // Poll every 3 seconds
    setInterval(poll, 3000);
    poll(); // Initial call
  }

  renderLayout() {
    const container = document.getElementById('cve-hunter-root');
    if (!container) return;

    container.innerHTML = `
            <div class="cve-dashboard">
                <header class="cve-header">
                    <div>
                        <h1 class="cve-title">CVE Hunter</h1>
                        <p style="color: var(--cve-text-secondary); margin-top: 0.25rem;">
                            Autonomous Vulnerability Scanning Swarm
                        </p>
                    </div>
                    <div class="cve-actions">
                        <span id="scan-status" style="color: var(--cve-text-secondary); display: flex; align-items: center;"></span>
                        <button id="scan-btn" class="cve-btn cve-btn-primary">
                            Search for Vulnerabilities
                        </button>
                    </div>
                </header>

                <div class="cve-stats-grid">
                    <div class="cve-stat-card">
                        <div class="cve-stat-value" id="stat-total">-</div>
                        <div class="cve-stat-label">Total CVEs</div>
                    </div>
                    <div class="cve-stat-card">
                        <div class="cve-stat-value" id="stat-critical" style="color: var(--cve-critical)">-</div>
                        <div class="cve-stat-label">Critical</div>
                    </div>
                    <div class="cve-stat-card">
                        <div class="cve-stat-value" id="stat-high" style="color: var(--cve-high)">-</div>
                        <div class="cve-stat-label">High Priority</div>
                    </div>
                    <div class="cve-stat-card">
                        <div class="cve-stat-value" id="stat-alerts">-</div>
                        <div class="cve-stat-label">Active Alerts</div>
                    </div>
                </div>

                <!-- Live Hunt Terminal -->
                <div class="cve-terminal-section">
                    <header class="cve-terminal-header">
                        <span><span style="color: #0f0">●</span> Live Hunt Protocol Active</span>
                        <span id="term-status">SCANNING_NETWORKS</span>
                    </header>
                    <div class="cve-terminal-body" id="cve-terminal-output">
                        <div class="cve-term-cursor">_</div>
                    </div>
                </div>

                <div class="cve-list-container">
                    <table class="cve-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Severity</th>
                                <th>CVSS</th>
                                <th>Description</th>
                                <th>Analyzed</th>
                                <th>Date</th>
                            </tr>
                        </thead>
                        <tbody id="cve-list-body">
                            <tr><td colspan="6" class="cve-loading">Loading vulnerabilities...</td></tr>
                        </tbody>
                    </table>
                </div>

                <!-- Detail Modal -->
                <div id="cve-modal" class="cve-modal-overlay hidden">
                    <div class="cve-modal">
                        <header class="cve-modal-header">
                            <div>
                                <h2 id="modal-title" class="cve-title"></h2>
                                <div id="modal-badges" style="margin-top: 0.5rem; display: flex; gap: 0.5rem;"></div>
                            </div>
                            <button class="cve-modal-close" onclick="document.getElementById('cve-modal').classList.add('hidden')">&times;</button>
                        </header>
                        <div class="cve-modal-body" id="modal-content"></div>
                    </div>
                </div>
            </div>
        `;
  }

  async loadStats() {
    try {
      const response = await fetch(`${this.apiBase}/stats`);
      const stats = await response.json();

      document.getElementById('stat-total').textContent = stats.total_cves;
      document.getElementById('stat-critical').textContent = stats.critical_count;
      document.getElementById('stat-high').textContent = stats.high_count;
      document.getElementById('stat-alerts').textContent = stats.active_alerts;
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  }

  async loadCVEs() {
    try {
      const response = await fetch(`${this.apiBase}/cves?page_size=50`);
      const data = await response.json();
      this.renderCVEList(data.items);
    } catch (error) {
      console.error('Failed to load CVEs:', error);
      document.getElementById('cve-list-body').innerHTML = `
                <tr><td colspan="6" style="text-align: center; padding: 2rem; color: var(--cve-critical)">
                    Failed to load data. Please try again.
                </td></tr>
            `;
    }
  }

  renderCVEList(cves) {
    const tbody = document.getElementById('cve-list-body');
    if (!cves.length) {
      tbody.innerHTML = `<tr><td colspan="6" class="cve-loading">No vulnerabilities found yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = cves
      .map(
        (cve) => `
            <tr class="cve-row" onclick="window.cveDashboard.showDetails('${cve.cve_id}')">
                <td style="font-family: monospace; font-weight: 600; color: var(--cve-accent)">${cve.cve_id}</td>
                <td><span class="cve-badge cve-badge-${cve.severity.toLowerCase()}">${cve.severity}</span></td>
                <td>${cve.cvss_score || '-'}</td>
                <td style="max-width: 400px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                    ${cve.description || 'No description available'}
                </td>
                <td>${cve.ai_summary ? '✅' : '-'}</td>
                <td style="color: var(--cve-text-secondary)">${new Date(cve.published_date || Date.now()).toLocaleDateString()}</td>
            </tr>
        `
      )
      .join('');
  }

  async showDetails(cveId) {
    const modal = document.getElementById('cve-modal');
    const content = document.getElementById('modal-content');

    // Show loading state
    modal.classList.remove('hidden');
    content.innerHTML = '<div class="cve-loading">Loading details...</div>';

    try {
      const response = await fetch(`${this.apiBase}/cves/${cveId}`);
      const cve = await response.json();

      document.getElementById('modal-title').textContent = cve.cve_id;
      document.getElementById('modal-badges').innerHTML = `
                <span class="cve-badge cve-badge-${cve.severity?.toLowerCase() || 'low'}">${cve.severity}</span>
                ${cve.cvss_score ? `<span class="cve-badge" style="background: rgba(255,255,255,0.1)">CVSS ${cve.cvss_score}</span>` : ''}
            `;

      content.innerHTML = `
                <div class="cve-metrics">
                    <div class="cve-metric-box">
                        <div class="cve-stat-label">Source</div>
                        <div>${cve.source}</div>
                    </div>
                    <div class="cve-metric-box">
                        <div class="cve-stat-label">Published</div>
                        <div>${new Date(cve.published_date).toLocaleDateString()}</div>
                    </div>
                    <div class="cve-metric-box">
                        <div class="cve-stat-label">Exploit Available</div>
                        <div style="color: ${cve.exploit_available ? 'var(--cve-critical)' : 'inherit'}">
                            ${cve.exploit_available ? 'YES ⚠️' : 'No'}
                        </div>
                    </div>
                </div>

                ${
                  cve.ai_summary
                    ? `
                    <div class="cve-detail-section">
                        <h3 class="cve-detail-title">🤖 AI Security Analysis</h3>
                        <div class="cve-ai-summary">
                            ${this.formatMarkdown(cve.ai_summary)}
                        </div>
                    </div>
                `
                    : ''
                }

                <div class="cve-detail-section">
                    <h3 class="cve-detail-title">Description</h3>
                    <p style="line-height: 1.6; color: var(--cve-text-secondary)">
                        ${cve.description}
                    </p>
                </div>

                <div class="cve-detail-section">
                    <h3 class="cve-detail-title">Affected Products</h3>
                    <div style="display: flex; flex-wrap: wrap; gap: 0.5rem">
                        ${
                          cve.affected_products
                            .map(
                              (p) => `
                            <span style="background: rgba(255,255,255,0.1); padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.875rem;">
                                ${p.vendor} / ${p.product} ${p.versions.length ? `(${p.versions.join(', ')})` : ''}
                            </span>
                        `
                            )
                            .join('') ||
                          '<span style="color: var(--cve-text-secondary)">No specific products listed</span>'
                        }
                    </div>
                </div>

                <div class="cve-detail-section">
                    <h3 class="cve-detail-title">References</h3>
                    <ul class="cve-refs-list">
                        ${cve.references
                          .map(
                            (ref) => `
                            <li><a href="${ref.url}" target="_blank" rel="noopener noreferrer">${ref.url}</a></li>
                        `
                          )
                          .join('')}
                    </ul>
                </div>
            `;
    } catch (error) {
      console.error('Failed to load details:', error);
      content.innerHTML = '<div style="color: var(--cve-critical)">Failed to load details.</div>';
    }
  }

  async triggerScan() {
    const btn = document.getElementById('scan-btn');
    const status = document.getElementById('scan-status');

    btn.disabled = true;
    status.textContent = 'Scanning...';

    try {
      const response = await fetch(`${this.apiBase}/scan?days_back=7`, { method: 'POST' });
      const result = await response.json();

      if (result.success) {
        status.textContent = 'Scan complete';
        setTimeout(() => (status.textContent = ''), 3000);
        // Refresh data
        await this.loadStats();
        await this.loadCVEs();
      } else {
        status.textContent = 'Scan failed';
        status.style.color = 'var(--cve-critical)';
      }
    } catch (error) {
      console.error('Scan failed:', error);
      status.textContent = 'Error triggering scan';
      status.style.color = 'var(--cve-critical)';
    } finally {
      btn.disabled = false;
    }
  }

  setupEventListeners() {
    document.getElementById('scan-btn')?.addEventListener('click', () => this.triggerScan());
  }

  formatMarkdown(text) {
    // Simple markdown formatter or pass-through if complex rendering is needed
    // For now, just handle basic paragraphs and lists
    return text.replace(/\n\n/g, '<br><br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  }
}

// Initialize on load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.cveDashboard = new CVEHunterDashboard();
  });
} else {
  window.cveDashboard = new CVEHunterDashboard();
}

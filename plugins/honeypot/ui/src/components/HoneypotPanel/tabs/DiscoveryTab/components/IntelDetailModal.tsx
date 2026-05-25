import { useState } from 'react';
import {
  X,
  Copy,
  Check,
  Globe,
  Link,
  Hash,
  FileCode,
  Download,
  Search,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

import './IntelDetailModal.css';

interface IntelDetailModalProps {
  category: 'ips' | 'domains' | 'hashes' | 'yara' | null;
  iocs: {
    ips?: string[];
    domains?: string[];
    hashes?: Array<{ sha256: string; md5?: string; size?: number; preview?: string }>;
  };
  iocCount: { ips: number; domains: number; hashes: number };
  yaraRules: string[];
  onClose: () => void;
}

export function IntelDetailModal({
  category,
  iocs,
  iocCount,
  yaraRules,
  onClose,
}: IntelDetailModalProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedItem, setCopiedItem] = useState<string | null>(null);
  const [expandedRules, setExpandedRules] = useState<Set<number>>(new Set());

  const handleCopy = async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedItem(id);
      setTimeout(() => setCopiedItem(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleExportJson = () => {
    const exportData = {
      generated_at: new Date().toISOString(),
      source: 'honeypot-threat-intel',
      iocs: {
        malicious_ips: iocs.ips || [],
        malicious_domains: iocs.domains || [],
        payload_hashes: iocs.hashes || [],
      },
      yara_rules: yaraRules,
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `threat-intel-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleExportYara = () => {
    const yaraContent = yaraRules.join('\n\n');
    const blob = new Blob([yaraContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `honeypot-rules-${new Date().toISOString().split('T')[0]}.yar`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const toggleRuleExpand = (idx: number) => {
    const newExpanded = new Set(expandedRules);
    if (newExpanded.has(idx)) {
      newExpanded.delete(idx);
    } else {
      newExpanded.add(idx);
    }
    setExpandedRules(newExpanded);
  };

  const getModalTitle = () => {
    switch (category) {
      case 'ips':
        return `Malicious IPs (${iocCount.ips})`;
      case 'domains':
        return `Malicious Domains (${iocCount.domains})`;
      case 'hashes':
        return `Payload Hashes (${iocCount.hashes})`;
      case 'yara':
        return `YARA Rules (${yaraRules.length})`;
      default:
        return 'Export Threat Intelligence';
    }
  };

  const getModalIcon = () => {
    switch (category) {
      case 'ips':
        return <Globe size={20} />;
      case 'domains':
        return <Link size={20} />;
      case 'hashes':
        return <Hash size={20} />;
      case 'yara':
        return <FileCode size={20} />;
      default:
        return <Download size={20} />;
    }
  };

  const filterItems = <T,>(items: T[], getSearchText: (item: T) => string): T[] => {
    if (!searchQuery.trim()) return items;
    const query = searchQuery.toLowerCase();
    return items.filter((item) => getSearchText(item).toLowerCase().includes(query));
  };

  const renderContent = () => {
    // Export options view
    if (category === null) {
      return (
        <div className="intel-export-options">
          <div className="export-option" onClick={handleExportJson}>
            <div className="export-option-icon json">
              <Download size={24} />
            </div>
            <div className="export-option-info">
              <h4>Export as JSON</h4>
              <p>Download all IOCs and metadata in JSON format</p>
            </div>
          </div>
          <div className="export-option" onClick={handleExportYara}>
            <div className="export-option-icon yara">
              <FileCode size={24} />
            </div>
            <div className="export-option-info">
              <h4>Export YARA Rules</h4>
              <p>Download {yaraRules.length} generated YARA rules</p>
            </div>
          </div>
          <div className="export-summary">
            <h4>Export Summary</h4>
            <div className="export-summary-grid">
              <div className="export-summary-item">
                <Globe size={16} />
                <span>{iocCount.ips} IPs</span>
              </div>
              <div className="export-summary-item">
                <Link size={16} />
                <span>{iocCount.domains} Domains</span>
              </div>
              <div className="export-summary-item">
                <Hash size={16} />
                <span>{iocCount.hashes} Hashes</span>
              </div>
              <div className="export-summary-item">
                <FileCode size={16} />
                <span>{yaraRules.length} YARA Rules</span>
              </div>
            </div>
          </div>
        </div>
      );
    }

    // IPs list
    if (category === 'ips') {
      const filteredIps = filterItems(iocs.ips || [], (ip) => ip);
      return (
        <div className="intel-list-container">
          <div className="intel-search-bar">
            <Search size={16} />
            <input
              type="text"
              placeholder="Search IPs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div className="intel-list">
            {filteredIps.map((ip, idx) => (
              <div key={ip} className="intel-list-item">
                <span className="item-index">{idx + 1}</span>
                <code className="item-value">{ip}</code>
                <button
                  className="copy-btn"
                  onClick={() => handleCopy(ip, `ip-${idx}`)}
                  title="Copy"
                >
                  {copiedItem === `ip-${idx}` ? <Check size={14} /> : <Copy size={14} />}
                </button>
              </div>
            ))}
            {filteredIps.length === 0 && (
              <div className="intel-empty">No IPs match your search</div>
            )}
          </div>
        </div>
      );
    }

    // Domains list
    if (category === 'domains') {
      const filteredDomains = filterItems(iocs.domains || [], (d) => d);
      return (
        <div className="intel-list-container">
          <div className="intel-search-bar">
            <Search size={16} />
            <input
              type="text"
              placeholder="Search domains..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div className="intel-list">
            {filteredDomains.map((domain, idx) => (
              <div key={domain} className="intel-list-item domain">
                <span className="item-index">{idx + 1}</span>
                <code className="item-value domain">{domain}</code>
                <button
                  className="copy-btn"
                  onClick={() => handleCopy(domain, `domain-${idx}`)}
                  title="Copy"
                >
                  {copiedItem === `domain-${idx}` ? <Check size={14} /> : <Copy size={14} />}
                </button>
              </div>
            ))}
            {filteredDomains.length === 0 && (
              <div className="intel-empty">No domains match your search</div>
            )}
          </div>
        </div>
      );
    }

    // Hashes list
    if (category === 'hashes') {
      const hashes = iocs.hashes || [];
      const filteredHashes = filterItems(hashes, (h) => h.sha256 || '');
      return (
        <div className="intel-list-container">
          <div className="intel-search-bar">
            <Search size={16} />
            <input
              type="text"
              placeholder="Search hashes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div className="intel-list hashes">
            {filteredHashes.map((hash, idx) => (
              <div key={hash.sha256 || idx} className="intel-list-item hash">
                <span className="item-index">{idx + 1}</span>
                <div className="hash-details">
                  <div className="hash-row">
                    <span className="hash-label">SHA-256:</span>
                    <code className="hash-value">{hash.sha256}</code>
                    <button
                      className="copy-btn"
                      onClick={() => handleCopy(hash.sha256, `sha-${idx}`)}
                      title="Copy SHA-256"
                    >
                      {copiedItem === `sha-${idx}` ? <Check size={14} /> : <Copy size={14} />}
                    </button>
                  </div>
                  {hash.md5 && (
                    <div className="hash-row secondary">
                      <span className="hash-label">MD5:</span>
                      <code className="hash-value">{hash.md5}</code>
                    </div>
                  )}
                  <div className="hash-meta">
                    {hash.size && <span className="hash-size">{hash.size} bytes</span>}
                    {hash.preview && (
                      <span className="hash-preview" title={hash.preview}>
                        Preview: {hash.preview.substring(0, 50)}...
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {filteredHashes.length === 0 && (
              <div className="intel-empty">No hashes match your search</div>
            )}
          </div>
        </div>
      );
    }

    // YARA rules
    if (category === 'yara') {
      return (
        <div className="intel-yara-container">
          <div className="yara-actions">
            <button className="yara-export-btn" onClick={handleExportYara}>
              <Download size={14} />
              Download All Rules
            </button>
          </div>
          <div className="intel-list yara">
            {yaraRules.map((rule, idx) => {
              const ruleNameMatch = rule.match(/rule\s+(\w+)/);
              const ruleName = ruleNameMatch ? ruleNameMatch[1] : `Rule ${idx + 1}`;
              const isExpanded = expandedRules.has(idx);

              return (
                <div key={idx} className="yara-rule-card">
                  <div className="yara-rule-header" onClick={() => toggleRuleExpand(idx)}>
                    <FileCode size={16} className="yara-icon" />
                    <span className="yara-rule-name">{ruleName}</span>
                    <div className="yara-rule-actions">
                      <button
                        className="copy-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleCopy(rule, `yara-${idx}`);
                        }}
                        title="Copy rule"
                      >
                        {copiedItem === `yara-${idx}` ? <Check size={14} /> : <Copy size={14} />}
                      </button>
                      <button className="expand-toggle">
                        {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                      </button>
                    </div>
                  </div>
                  {isExpanded && (
                    <pre className="yara-rule-content">
                      <code>{rule}</code>
                    </pre>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      );
    }

    return null;
  };

  return (
    <div className="intel-detail-modal-overlay" onClick={onClose}>
      <div className="intel-detail-modal" onClick={(e) => e.stopPropagation()}>
        <div className="intel-modal-header">
          <div className="modal-title">
            {getModalIcon()}
            <h2>{getModalTitle()}</h2>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        <div className="intel-modal-content">{renderContent()}</div>
      </div>
    </div>
  );
}

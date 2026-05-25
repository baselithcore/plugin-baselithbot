import { useState, useMemo } from 'react';
import {
  Lightbulb,
  ChevronDown,
  ChevronUp,
  X,
  Download,
  CheckCircle,
  AlertTriangle,
  Zap,
  Bug,
  Network,
  Terminal,
  Target,
  Filter,
  SortAsc,
  Sparkles,
  Shield,
  Info,
} from 'lucide-react';
import type { HoneypotSuggestion, DiscoveryResult } from '../../../../types';

import './SuggestionsSection.css';

interface SuggestionsSectionProps {
  result: DiscoveryResult;
}

type SortOption = 'priority' | 'confidence' | 'occurrences' | 'catch_rate' | 'relevance';
type FilterPriority = 'all' | 'critical' | 'high' | 'medium' | 'low';
type FilterType = 'all' | 'zeroday_pattern' | 'behavioral_cluster' | 'protocol_anomaly';

const PRIORITY_CONFIG: Record<string, { color: string; bgColor: string; label: string }> = {
  critical: { color: '#ff4757', bgColor: 'rgba(255, 71, 87, 0.15)', label: 'CRITICAL' },
  high: { color: '#ff6b9d', bgColor: 'rgba(255, 107, 157, 0.15)', label: 'HIGH' },
  medium: { color: '#ffa726', bgColor: 'rgba(255, 167, 38, 0.15)', label: 'MEDIUM' },
  low: { color: '#00ff9d', bgColor: 'rgba(0, 255, 157, 0.15)', label: 'LOW' },
};

const SOPHISTICATION_CONFIG: Record<
  string,
  { color: string; label: string; icon: React.ElementType }
> = {
  advanced: { color: '#ff4757', label: 'Advanced', icon: Shield },
  intermediate: { color: '#ffa726', label: 'Intermediate', icon: Zap },
  basic: { color: '#00ff9d', label: 'Basic', icon: Target },
};

const TYPE_ICONS: Record<string, React.ElementType> = {
  zeroday_pattern: Bug,
  behavioral_cluster: Network,
  protocol_anomaly: Zap,
  exploit_technique: Target,
  command_pattern: Terminal,
};

function RelevanceBadge({ score }: { score: number }) {
  const percentage = Math.round(score * 100);
  const color = score >= 0.7 ? '#00ff9d' : score >= 0.4 ? '#ffa726' : '#ff6b9d';

  return (
    <div className="relevance-badge" title={`Investigation value: ${percentage}%`}>
      <Sparkles size={12} style={{ color }} />
      <div className="relevance-bar">
        <div
          className="relevance-bar-fill"
          style={{ width: `${percentage}%`, background: color }}
        />
      </div>
      <span style={{ color }}>{percentage}%</span>
    </div>
  );
}

function SuggestionCard({
  suggestion,
  onDismiss,
  onViewYaml,
}: {
  suggestion: HoneypotSuggestion;
  onDismiss: (id: string) => void;
  onViewYaml: (suggestion: HoneypotSuggestion) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  const priorityConfig = PRIORITY_CONFIG[suggestion.priority] || PRIORITY_CONFIG.medium;
  const TypeIcon = TYPE_ICONS[suggestion.suggestion_type] || Lightbulb;
  const sophisticationLevel =
    (suggestion as { sophistication_level?: string }).sophistication_level || 'basic';
  const sophisticationConfig =
    SOPHISTICATION_CONFIG[sophisticationLevel] || SOPHISTICATION_CONFIG.basic;
  const relevanceScore = (suggestion as { relevance_score?: number }).relevance_score || 0;
  const investigationRationale =
    (suggestion as { investigation_rationale?: string }).investigation_rationale || '';

  return (
    <div className="suggestion-card">
      <div className="suggestion-card-header">
        <div className="suggestion-card-icon">
          <TypeIcon size={18} />
        </div>
        <div className="suggestion-card-title-section">
          <h4 className="suggestion-card-title">{suggestion.title}</h4>
          <div className="suggestion-card-meta">
            <span
              className="suggestion-priority-badge"
              style={{ backgroundColor: priorityConfig.bgColor, color: priorityConfig.color }}
            >
              {priorityConfig.label}
            </span>
            <span className="suggestion-protocol-badge">
              {suggestion.suggested_protocol.toUpperCase()}:{suggestion.suggested_port}
            </span>
            <span
              className="suggestion-sophistication-badge"
              style={{ color: sophisticationConfig.color }}
              title={`Attack sophistication: ${sophisticationConfig.label}`}
            >
              <sophisticationConfig.icon size={10} />
              {sophisticationConfig.label}
            </span>
          </div>
        </div>
        <button
          className="suggestion-dismiss-btn"
          onClick={() => onDismiss(suggestion.id)}
          title="Dismiss suggestion"
        >
          <X size={16} />
        </button>
      </div>

      {relevanceScore > 0 && <RelevanceBadge score={relevanceScore} />}

      <p className="suggestion-description">{suggestion.description}</p>

      {investigationRationale && (
        <div className="suggestion-investigation-rationale">
          <Info size={12} />
          <span>{investigationRationale}</span>
        </div>
      )}

      <div className="suggestion-metrics">
        <div className="suggestion-metric">
          <span className="metric-value">{suggestion.occurrence_count}</span>
          <span className="metric-label">Occurrences</span>
        </div>
        <div className="suggestion-metric">
          <span className="metric-value">{suggestion.source_ips.length}</span>
          <span className="metric-label">Source IPs</span>
        </div>
        <div className="suggestion-metric">
          <span className="metric-value">
            {(suggestion.estimated_catch_rate * 100).toFixed(0)}%
          </span>
          <span className="metric-label">Est. Catch Rate</span>
        </div>
        <div className="suggestion-metric">
          <span className="metric-value">{(suggestion.confidence * 100).toFixed(0)}%</span>
          <span className="metric-label">Confidence</span>
        </div>
      </div>

      <button className="suggestion-rationale-toggle" onClick={() => setExpanded(!expanded)}>
        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        Why this suggestion?
      </button>

      {expanded && (
        <div className="suggestion-rationale">
          <p>{suggestion.rationale}</p>
          {suggestion.tags.length > 0 && (
            <div className="suggestion-tags">
              {suggestion.tags.map((tag) => (
                <span key={tag} className="suggestion-tag">
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="suggestion-actions">
        <button className="suggestion-action-btn primary" onClick={() => onViewYaml(suggestion)}>
          <Download size={14} />
          View YAML
        </button>
      </div>
    </div>
  );
}

function SuggestionsFilters({
  priorityFilter,
  typeFilter,
  sortBy,
  onPriorityChange,
  onTypeChange,
  onSortChange,
}: {
  priorityFilter: FilterPriority;
  typeFilter: FilterType;
  sortBy: SortOption;
  onPriorityChange: (priority: FilterPriority) => void;
  onTypeChange: (type: FilterType) => void;
  onSortChange: (sort: SortOption) => void;
}) {
  return (
    <div className="suggestions-filters">
      <div className="filter-group">
        <Filter size={14} />
        <select
          value={priorityFilter}
          onChange={(e) => onPriorityChange(e.target.value as FilterPriority)}
          className="filter-select"
        >
          <option value="all">All Priorities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      <div className="filter-group">
        <Target size={14} />
        <select
          value={typeFilter}
          onChange={(e) => onTypeChange(e.target.value as FilterType)}
          className="filter-select"
        >
          <option value="all">All Types</option>
          <option value="zeroday_pattern">Zero-Day Pattern</option>
          <option value="behavioral_cluster">Behavioral Cluster</option>
          <option value="protocol_anomaly">Protocol Anomaly</option>
        </select>
      </div>

      <div className="filter-group">
        <SortAsc size={14} />
        <select
          value={sortBy}
          onChange={(e) => onSortChange(e.target.value as SortOption)}
          className="filter-select"
        >
          <option value="priority">Sort by Priority</option>
          <option value="relevance">Sort by Relevance</option>
          <option value="confidence">Sort by Confidence</option>
          <option value="occurrences">Sort by Occurrences</option>
          <option value="catch_rate">Sort by Catch Rate</option>
        </select>
      </div>
    </div>
  );
}

function YamlPreviewModal({
  suggestion,
  onClose,
}: {
  suggestion: HoneypotSuggestion;
  onClose: () => void;
}) {
  const [yaml, setYaml] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  // Fetch YAML on mount
  useState(() => {
    fetch(`/api/honeypot/discovery/suggestions/${suggestion.id}/yaml`)
      .then((res) => res.json())
      .then((data) => {
        setYaml(data.yaml);
        setLoading(false);
      })
      .catch(() => {
        setYaml('# Failed to load YAML configuration');
        setLoading(false);
      });
  });

  const handleCopy = async () => {
    if (yaml) {
      await navigator.clipboard.writeText(yaml);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownload = () => {
    if (yaml) {
      const blob = new Blob([yaml], { type: 'text/yaml' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${suggestion.title.toLowerCase().replace(/\s+/g, '-')}.yaml`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  return (
    <div className="yaml-modal-overlay" onClick={onClose}>
      <div className="yaml-modal" onClick={(e) => e.stopPropagation()}>
        <div className="yaml-modal-header">
          <h3>Honeypot Configuration</h3>
          <button className="yaml-modal-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>
        <div className="yaml-modal-content">
          {loading ? (
            <div className="yaml-loading">Loading configuration...</div>
          ) : (
            <pre className="yaml-code">{yaml}</pre>
          )}
        </div>
        <div className="yaml-modal-footer">
          <button className="yaml-modal-btn" onClick={handleCopy}>
            {copied ? <CheckCircle size={14} /> : null}
            {copied ? 'Copied!' : 'Copy to Clipboard'}
          </button>
          <button className="yaml-modal-btn primary" onClick={handleDownload}>
            <Download size={14} />
            Download YAML
          </button>
        </div>
        <p className="yaml-modal-hint">
          Save this file to <code>plugins/honeypot/honeypots/</code> and restart the honeypot engine
          to activate.
        </p>
      </div>
    </div>
  );
}

export function SuggestionsSection({ result }: SuggestionsSectionProps) {
  const [selectedSuggestion, setSelectedSuggestion] = useState<HoneypotSuggestion | null>(null);
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());
  const [priorityFilter, setPriorityFilter] = useState<FilterPriority>('all');
  const [typeFilter, setTypeFilter] = useState<FilterType>('all');
  const [sortBy, setSortBy] = useState<SortOption>('priority');

  const rawSuggestions = (result.suggestions || []).filter(
    (s) => !s.dismissed && !s.applied && !dismissedIds.has(s.id)
  );

  // Apply filters and sorting
  const suggestions = useMemo(() => {
    let filtered = [...rawSuggestions];

    // Apply priority filter
    if (priorityFilter !== 'all') {
      filtered = filtered.filter((s) => s.priority === priorityFilter);
    }

    // Apply type filter
    if (typeFilter !== 'all') {
      filtered = filtered.filter((s) => s.suggestion_type === typeFilter);
    }

    // Apply sorting
    const priorityOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'priority':
          return (priorityOrder[a.priority] || 4) - (priorityOrder[b.priority] || 4);
        case 'confidence':
          return b.confidence - a.confidence;
        case 'occurrences':
          return b.occurrence_count - a.occurrence_count;
        case 'catch_rate':
          return b.estimated_catch_rate - a.estimated_catch_rate;
        case 'relevance':
          const aRelevance = (a as { relevance_score?: number }).relevance_score || 0;
          const bRelevance = (b as { relevance_score?: number }).relevance_score || 0;
          return bRelevance - aRelevance;
        default:
          return 0;
      }
    });

    return filtered;
  }, [rawSuggestions, priorityFilter, typeFilter, sortBy]);

  const handleDismiss = async (id: string) => {
    setDismissedIds((prev) => new Set(prev).add(id));
    try {
      await fetch(`/api/honeypot/discovery/suggestions/${id}/dismiss`, {
        method: 'POST',
      });
    } catch {
      // Ignore errors, UI already updated
    }
  };

  if (rawSuggestions.length === 0) {
    return (
      <div className="suggestions-section">
        <div className="suggestions-header">
          <Lightbulb size={16} />
          <h3>Suggested Honeypots</h3>
        </div>
        <div className="suggestions-empty">
          <Lightbulb size={32} />
          <p>No high-quality suggestions available</p>
          <span>
            Suggestions are generated when novel attack patterns are detected that warrant
            investigation with a custom honeypot. Low-quality and generic patterns are filtered out.
          </span>
        </div>
      </div>
    );
  }

  // Count by priority
  const byPriority = rawSuggestions.reduce(
    (acc, s) => {
      acc[s.priority] = (acc[s.priority] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <div className="suggestions-section">
      <div className="suggestions-header">
        <Lightbulb size={16} />
        <h3>Suggested Honeypots</h3>
        <span className="suggestions-count">{rawSuggestions.length}</span>
      </div>

      <div className="suggestions-summary">
        {Object.entries(byPriority).map(([priority, count]) => {
          const config = PRIORITY_CONFIG[priority] || PRIORITY_CONFIG.medium;
          return (
            <div
              key={priority}
              className="suggestion-priority-summary"
              style={{ color: config.color }}
            >
              <AlertTriangle size={12} />
              <span>
                {count} {priority}
              </span>
            </div>
          );
        })}
      </div>

      <SuggestionsFilters
        priorityFilter={priorityFilter}
        typeFilter={typeFilter}
        sortBy={sortBy}
        onPriorityChange={setPriorityFilter}
        onTypeChange={setTypeFilter}
        onSortChange={setSortBy}
      />

      {suggestions.length === 0 && rawSuggestions.length > 0 && (
        <div className="suggestions-empty-filtered">
          <Filter size={20} />
          <p>No suggestions match the current filters</p>
          <button
            className="reset-filters-btn"
            onClick={() => {
              setPriorityFilter('all');
              setTypeFilter('all');
            }}
          >
            Reset Filters
          </button>
        </div>
      )}

      <div className="suggestions-grid">
        {suggestions.map((suggestion) => (
          <SuggestionCard
            key={suggestion.id}
            suggestion={suggestion}
            onDismiss={handleDismiss}
            onViewYaml={setSelectedSuggestion}
          />
        ))}
      </div>

      {selectedSuggestion && (
        <YamlPreviewModal
          suggestion={selectedSuggestion}
          onClose={() => setSelectedSuggestion(null)}
        />
      )}
    </div>
  );
}

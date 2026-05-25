/**
 * ThreatsFilters - Filter bar component for ThreatsTab
 * Provides comprehensive filtering with autocomplete for IP and Country
 */

import { useState } from 'react';
import {
  Search,
  Filter,
  RefreshCw,
  Globe,
  Server,
  AlertCircle,
  MapPin,
  Network,
  X,
  User,
} from 'lucide-react';
import { AttackEvent } from '../../../types';
import { normalizeIpDisplay } from '../../../api';
import { getCountryFlag } from '../../../geoUtils';
import { FilterState, getIpSuggestions, getCountrySuggestions } from './utils/threatsHelpers';

interface ThreatsFiltersProps {
  filters: FilterState;
  onFilterChange: (key: string, value: any) => void;
  onClearFilter: (key: string) => void;
  onRefresh: () => void;
  availableHoneypots: { id: string; name: string }[];
  events: AttackEvent[];
  loading: boolean;
}

export function ThreatsFilters({
  filters,
  onFilterChange,
  onClearFilter,
  onRefresh,
  availableHoneypots,
  events,
  loading,
}: ThreatsFiltersProps) {
  const [showIpSuggestions, setShowIpSuggestions] = useState(false);
  const [showCountrySuggestions, setShowCountrySuggestions] = useState(false);

  const ipSuggestions = getIpSuggestions(events, filters.source_ip);
  const countrySuggestions = getCountrySuggestions(events, filters.country);

  return (
    <div className="hp-filters-bar">
      {/* IP Search with Autocomplete */}
      <div className="hp-filter-group search relative-group">
        <Search size={16} className="hp-filter-icon" />
        <input
          type="text"
          placeholder="Search IP..."
          value={filters.source_ip}
          onChange={(e) => onFilterChange('source_ip', e.target.value)}
          onFocus={() => setShowIpSuggestions(true)}
          onBlur={() => setTimeout(() => setShowIpSuggestions(false), 200)}
        />
        {filters.source_ip && (
          <button className="hp-clear-btn" onClick={() => onClearFilter('source_ip')}>
            <X size={12} />
          </button>
        )}

        {/* IP Suggestions Dropdown */}
        {showIpSuggestions && ipSuggestions.length > 0 && (
          <div className="hp-search-suggestions list-mode">
            {ipSuggestions.map((ip) => (
              <div
                key={ip}
                className="hp-search-suggestion-item"
                onClick={() => onFilterChange('source_ip', ip)}
              >
                <Network size={12} />
                <span>{normalizeIpDisplay(ip)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Country Search with Autocomplete */}
      <div className="hp-filter-group search relative-group">
        <Globe size={16} className="hp-filter-icon" />
        <input
          type="text"
          placeholder="Country..."
          value={filters.country}
          onChange={(e) => onFilterChange('country', e.target.value)}
          onFocus={() => setShowCountrySuggestions(true)}
          onBlur={() => setTimeout(() => setShowCountrySuggestions(false), 200)}
          style={{ width: '120px' }}
        />
        {filters.country && (
          <button className="hp-clear-btn" onClick={() => onClearFilter('country')}>
            <X size={12} />
          </button>
        )}

        {/* Country Suggestions Dropdown */}
        {showCountrySuggestions && countrySuggestions.length > 0 && (
          <div className="hp-search-suggestions list-mode">
            {countrySuggestions.map((c) => (
              <div
                key={c.code}
                className="hp-search-suggestion-item"
                onClick={() => onFilterChange('country', c.code)}
              >
                <MapPin size={12} />
                <span>
                  {getCountryFlag(c.code)} {c.name}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Type Filter (Bot/Human/All) */}
      <div className="hp-filter-group select">
        <User size={16} className="hp-filter-icon" />
        <select
          value={filters.is_bot === undefined ? 'all' : filters.is_bot ? 'bot' : 'human'}
          onChange={(e) => {
            const val = e.target.value;
            onFilterChange('is_bot', val === 'all' ? undefined : val === 'bot');
          }}
        >
          <option value="all">All Actors</option>
          <option value="human">Humans Only</option>
          <option value="bot">Bots Only</option>
        </select>
      </div>

      {/* Honeypot Filter */}
      <div className="hp-filter-group select">
        <Server size={16} className="hp-filter-icon" />
        <select
          value={filters.honeypot_id}
          onChange={(e) => onFilterChange('honeypot_id', e.target.value)}
        >
          <option value="">All Honeypots</option>
          {availableHoneypots.map((hp) => (
            <option key={hp.id} value={hp.id}>
              {hp.name}
            </option>
          ))}
        </select>
      </div>

      {/* Protocol Filter */}
      <div className="hp-filter-group select">
        <Filter size={16} className="hp-filter-icon" />
        <select
          value={filters.protocol}
          onChange={(e) => onFilterChange('protocol', e.target.value)}
        >
          <option value="">All Protocols</option>
          <option value="ssh">SSH</option>
          <option value="http">HTTP</option>
          <option value="tcp">TCP</option>
        </select>
      </div>

      {/* Severity Filter */}
      <div className="hp-filter-group select">
        <AlertCircle size={16} className="hp-filter-icon" />
        <select
          value={filters.severity}
          onChange={(e) => onFilterChange('severity', e.target.value)}
        >
          <option value="">All Severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
          <option value="info">Info</option>
        </select>
      </div>

      {/* Refresh Button */}
      <button className="hp-refresh-btn" onClick={onRefresh} title="Refresh Data">
        <RefreshCw size={16} className={loading ? 'spin' : ''} />
      </button>
    </div>
  );
}

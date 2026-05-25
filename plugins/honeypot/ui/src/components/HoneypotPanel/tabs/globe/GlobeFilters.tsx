/**
 * GlobeFilters - Search and filter controls for Globe Tab
 * Redesigned for better UX with always-visible search
 */

import { RefObject } from 'react';
import { Search, User, Bot, Network, MapPin, X } from 'lucide-react';
import type { FilterType, SearchSuggestion } from './types';

interface GlobeFiltersProps {
  searchTerm: string;
  setSearchTerm: (term: string) => void;
  filterType: FilterType;
  setFilterType: (type: FilterType) => void;
  timeRange: string;
  onTimeRangeChange: (range: string) => void;
  searchInputRef: RefObject<HTMLInputElement>;
  filteredCount: number;
  suggestions: SearchSuggestion[];
  showSuggestions: boolean;
  onSuggestionClick: (value: string) => void;
}

export function GlobeFilters({
  searchTerm,
  setSearchTerm,
  filterType,
  setFilterType,
  timeRange,
  onTimeRangeChange,
  searchInputRef,
  filteredCount,
  suggestions,
  showSuggestions,
  onSuggestionClick,
}: GlobeFiltersProps) {
  return (
    <div className="hp-origins-controls">
      {/* Search Bar - Always Visible */}
      <div className="hp-filter-search-container">
        <Search size={16} className="hp-filter-search-icon" />
        <input
          ref={searchInputRef}
          type="text"
          className="hp-filter-search-input"
          placeholder="Search IP, Country, City..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
        {searchTerm && (
          <button
            className="hp-filter-search-clear"
            onClick={() => setSearchTerm('')}
            title="Clear search"
          >
            <X size={14} />
          </button>
        )}

        {/* Autocomplete Dropdown */}
        {showSuggestions && suggestions.length > 0 && (
          <div className="hp-search-suggestions">
            {suggestions.map((suggestion, idx) => (
              <div
                key={idx}
                className="hp-search-suggestion-item"
                onClick={() => onSuggestionClick(suggestion.value)}
              >
                {suggestion.type === 'ip' ? <Network size={12} /> : <MapPin size={12} />}
                <span>{suggestion.value}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="hp-filter-divider" />

      {/* Bot/Human Filter */}
      <div className="hp-filter-group">
        <button
          className={`hp-filter-btn ${filterType === 'all' ? 'active' : ''}`}
          onClick={() => setFilterType('all')}
          title="All Attackers"
        >
          All
        </button>
        <button
          className={`hp-filter-btn ${filterType === 'human' ? 'active' : ''}`}
          onClick={() => setFilterType('human')}
          title="Humans Only"
        >
          <User size={14} />
        </button>
        <button
          className={`hp-filter-btn ${filterType === 'bot' ? 'active' : ''}`}
          onClick={() => setFilterType('bot')}
          title="Bots Only"
        >
          <Bot size={14} />
        </button>
      </div>

      <div className="hp-filter-divider" />

      {/* Time Range Filter */}
      <div className="hp-filter-group">
        <button
          className={`hp-filter-btn ${timeRange === 'all' ? 'active' : ''}`}
          onClick={() => onTimeRangeChange('all')}
          title="All Time"
        >
          All
        </button>
        <button
          className={`hp-filter-btn ${timeRange === '1h' ? 'active' : ''}`}
          onClick={() => onTimeRangeChange('1h')}
          title="Last 1 Hour"
        >
          1H
        </button>
        <button
          className={`hp-filter-btn ${timeRange === '24h' ? 'active' : ''}`}
          onClick={() => onTimeRangeChange('24h')}
          title="Last 24 Hours"
        >
          24H
        </button>
        <button
          className={`hp-filter-btn ${timeRange === '7d' ? 'active' : ''}`}
          onClick={() => onTimeRangeChange('7d')}
          title="Last 7 Days"
        >
          7D
        </button>
        <button
          className={`hp-filter-btn ${timeRange === '30d' ? 'active' : ''}`}
          onClick={() => onTimeRangeChange('30d')}
          title="Last 30 Days"
        >
          30D
        </button>
      </div>

      {/* Attack Count */}
      <span className="hp-origins-count">{filteredCount} attacks</span>
    </div>
  );
}

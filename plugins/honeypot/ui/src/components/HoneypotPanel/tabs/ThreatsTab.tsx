/**
 * ThreatsTab - Unified Event List & Threat Analysis
 *
 * Orchestrates the display of attack events with server-side pagination,
 * filtering, and expandable threat details.
 *
 * Refactored for modularity - see threats/ subdirectory for component breakdown.
 */

import { useState, useEffect } from 'react';
import { AttackEvent } from '../../types';
import { fetchEvents, fetchHoneypots } from '../../api';
import { ThreatsFilters } from './threats/ThreatsFilters';
import { ThreatsTable } from './threats/ThreatsTable';
import { ThreatsPagination } from './threats/ThreatsPagination';
import { FilterState, buildActiveFilters } from './threats/utils/threatsHelpers';

import './ThreatsTab.css';

interface ThreatsTabProps {
  events?: AttackEvent[];
  onSelectAttack: (event: AttackEvent) => void;
}

export function ThreatsTab({ onSelectAttack }: ThreatsTabProps) {
  // Data state
  const [events, setEvents] = useState<AttackEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [totalPages, setTotalPages] = useState(1);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Filters state
  const [filters, setFilters] = useState<FilterState>({
    source_ip: '',
    country: '',
    honeypot_id: '',
    protocol: '',
    severity: '',
    category: '',
    is_bot: undefined,
  });

  // Debounced filters for API calls
  const [debouncedFilters, setDebouncedFilters] = useState(filters);

  // Metadata state
  const [availableHoneypots, setAvailableHoneypots] = useState<{ id: string; name: string }[]>([]);
  const [refreshKey, setRefreshKey] = useState(0);

  // Debounce effect
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedFilters(filters);
    }, 500);
    return () => clearTimeout(handler);
  }, [filters]);

  // Load available honeypots for filter dropdown
  useEffect(() => {
    fetchHoneypots()
      .then((hps) => {
        setAvailableHoneypots(hps.map((h) => ({ id: h.id, name: h.name })));
      })
      .catch((err) => console.warn('Failed to load honeypots', err));
  }, []);

  // Main data loader
  useEffect(() => {
    let isMounted = true;

    const loadData = async () => {
      setLoading(true);
      try {
        const activeFilters = buildActiveFilters(debouncedFilters);
        const response = await fetchEvents(page, pageSize, activeFilters);

        if (isMounted) {
          setEvents(response.items);
          setTotal(response.total);
          setTotalPages(Math.ceil(response.total / pageSize));
        }
      } catch (error) {
        console.error('Failed to fetch events:', error);
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    loadData();

    return () => {
      isMounted = false;
    };
  }, [page, pageSize, debouncedFilters, refreshKey]);

  // Handlers
  const handleFilterChange = (key: string, value: any) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setPage(1); // Reset to first page on filter change
  };

  const clearFilter = (key: string) => {
    handleFilterChange(key, key === 'is_bot' ? undefined : '');
  };

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setPage(newPage);
    }
  };

  const handlePageSizeChange = (newSize: number) => {
    setPageSize(newSize);
    setPage(1); // Reset to first page
  };

  const handleRefresh = () => {
    setRefreshKey((prev) => prev + 1);
  };

  const toggleRow = (eventId: string) => {
    setExpandedId(expandedId === eventId ? null : eventId);
  };

  return (
    <div className="hp-list-tab">
      {/* Thread Intelligence Dashboard */}

      <ThreatsFilters
        filters={filters}
        onFilterChange={handleFilterChange}
        onClearFilter={clearFilter}
        onRefresh={handleRefresh}
        availableHoneypots={availableHoneypots}
        events={events}
        loading={loading}
      />

      <ThreatsTable
        events={events}
        loading={loading}
        expandedId={expandedId}
        onToggleRow={toggleRow}
        onSelectAttack={onSelectAttack}
      />

      <ThreatsPagination
        page={page}
        totalPages={totalPages}
        pageSize={pageSize}
        total={total}
        eventsCount={events.length}
        onPageChange={handlePageChange}
        onPageSizeChange={handlePageSizeChange}
      />
    </div>
  );
}

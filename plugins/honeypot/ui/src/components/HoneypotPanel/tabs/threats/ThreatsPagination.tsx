/**
 * ThreatsPagination - Pagination controls for ThreatsTab
 * Handles page navigation and page size selection
 */

import { ChevronLeft, ChevronRight } from 'lucide-react';

interface ThreatsPaginationProps {
  page: number;
  totalPages: number;
  pageSize: number;
  total: number;
  eventsCount: number;
  onPageChange: (newPage: number) => void;
  onPageSizeChange: (newSize: number) => void;
}

export function ThreatsPagination({
  page,
  totalPages,
  pageSize,
  total,
  eventsCount,
  onPageChange,
  onPageSizeChange,
}: ThreatsPaginationProps) {
  return (
    <div className="hp-pagination">
      <span className="hp-page-info">
        Showing {eventsCount} of {total} events (Page {page} of {totalPages})
      </span>
      <div className="hp-page-controls">
        <button disabled={page <= 1} onClick={() => onPageChange(page - 1)} className="hp-page-btn">
          <ChevronLeft size={16} /> Previous
        </button>

        <select
          className="hp-page-size-select"
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
        >
          <option value={20}>20 / page</option>
          <option value={50}>50 / page</option>
          <option value={100}>100 / page</option>
          <option value={500}>500 / page</option>
        </select>

        <button
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          className="hp-page-btn"
        >
          Next <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}

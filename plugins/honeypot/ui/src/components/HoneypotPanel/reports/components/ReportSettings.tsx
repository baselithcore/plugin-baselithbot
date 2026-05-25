/**
 * Report Settings Component
 *
 * Configuration options for time range, organization, and classification.
 */

import { Clock, Building, Lock } from 'lucide-react';
import { TIME_RANGES } from '../ReportsConstants';

interface ReportSettingsProps {
  timeRange: number;
  organizationName: string;
  classification: string;
  onTimeRangeChange: (range: number) => void;
  onOrganizationChange: (name: string) => void;
  onClassificationChange: (classification: string) => void;
}

export function ReportSettings({
  timeRange,
  organizationName,
  classification,
  onTimeRangeChange,
  onOrganizationChange,
  onClassificationChange,
}: ReportSettingsProps) {
  return (
    <div className="report-settings">
      {/* Time Range */}
      <div className="setting-group">
        <label className="config-label">
          <Clock size={16} />
          Time Range
        </label>
        <select
          value={timeRange}
          onChange={(e) => onTimeRangeChange(Number(e.target.value))}
          className="config-select"
        >
          {TIME_RANGES.map((range) => (
            <option key={range.value} value={range.value}>
              {range.label}
            </option>
          ))}
        </select>
      </div>

      {/* Organization Name */}
      <div className="setting-group">
        <label className="config-label">
          <Building size={16} />
          Organization Name (Optional)
        </label>
        <input
          type="text"
          value={organizationName}
          onChange={(e) => onOrganizationChange(e.target.value)}
          placeholder="e.g., ACME Corporation"
          className="config-input"
        />
      </div>

      {/* Classification */}
      <div className="setting-group">
        <label className="config-label">
          <Lock size={16} />
          Classification Level
        </label>
        <select
          value={classification}
          onChange={(e) => onClassificationChange(e.target.value)}
          className="config-select"
        >
          <option value="UNCLASSIFIED">UNCLASSIFIED</option>
          <option value="INTERNAL">INTERNAL</option>
          <option value="CONFIDENTIAL">CONFIDENTIAL</option>
          <option value="SECRET">SECRET</option>
        </select>
      </div>
    </div>
  );
}

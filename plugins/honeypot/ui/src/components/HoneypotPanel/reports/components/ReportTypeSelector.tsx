/**
 * Report Type Selector Component
 *
 * Displays available report types with icons and descriptions.
 */

import { ReportType, ReportTypesResponse } from '../../../types';
import { REPORT_TYPE_ICONS } from '../ReportsConstants';

interface ReportTypeSelectorProps {
  reportTypes: ReportTypesResponse | null;
  selectedType: ReportType;
  onTypeChange: (type: ReportType) => void;
}

export function ReportTypeSelector({
  reportTypes,
  selectedType,
  onTypeChange,
}: ReportTypeSelectorProps) {
  if (!reportTypes) {
    return (
      <div className="report-type-selector-loading">
        <div className="skeleton-loader" style={{ height: '100px' }}></div>
      </div>
    );
  }

  return (
    <div className="report-type-selector">
      <label className="config-label">Report Type</label>
      <div className="report-types-grid">
        {Object.entries(reportTypes.types).map(([type, info]) => {
          const Icon = REPORT_TYPE_ICONS[type as ReportType];
          const isSelected = selectedType === type;

          return (
            <button
              key={type}
              className={`report-type-card ${isSelected ? 'selected' : ''}`}
              onClick={() => onTypeChange(type as ReportType)}
            >
              {Icon && <Icon size={24} />}
              <div className="report-type-content">
                <h3>{info.name}</h3>
                <p>{info.description}</p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

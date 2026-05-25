/**
 * ReportsConfig - Refactored with Modular Components
 *
 * Uses extracted components for better maintainability.
 */

import { useState } from 'react';
import { Settings, ChevronUp, ChevronDown } from 'lucide-react';
import { ReportType, ReportSection, ReportTypesResponse } from '../../types';
import { ReportTypeSelector, SectionSelector, ReportSettings, ReportActions } from './components';

interface ReportsConfigProps {
  reportTypes: ReportTypesResponse | null;
  selectedType: ReportType;
  selectedSections: ReportSection[];
  timeRange: number;
  organizationName: string;
  classification: string;
  isLoadingPreview: boolean;
  isExporting: boolean;
  exportFormat: 'markdown' | 'pdf';
  onTypeChange: (type: ReportType) => void;
  onSectionsChange: (sections: ReportSection[]) => void;
  onTimeRangeChange: (range: number) => void;
  onOrganizationChange: (name: string) => void;
  onClassificationChange: (classification: string) => void;
  onGeneratePreview: () => void;
  onExport: (format: 'markdown' | 'pdf') => void;
}

export function ReportsConfigRefactored({
  reportTypes,
  selectedType,
  selectedSections,
  timeRange,
  organizationName,
  classification,
  isLoadingPreview,
  isExporting,
  exportFormat,
  onTypeChange,
  onSectionsChange,
  onTimeRangeChange,
  onOrganizationChange,
  onClassificationChange,
  onGeneratePreview,
  onExport,
}: ReportsConfigProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Get available sections for selected report type
  // Get available sections (fallback to all sections as default_sections is not in type)
  const availableSections: ReportSection[] = reportTypes?.sections.map((s) => s.id) || [];

  return (
    <div className="reports-config">
      <div className="config-header">
        <h2>Report Configuration</h2>
      </div>

      <div className="config-content">
        {/* Report Type Selection */}
        <ReportTypeSelector
          reportTypes={reportTypes}
          selectedType={selectedType}
          onTypeChange={onTypeChange}
        />

        {/* Section Selection */}
        <SectionSelector
          sections={availableSections}
          selectedSections={selectedSections}
          onSectionsChange={onSectionsChange}
        />

        {/* Advanced Settings Toggle */}
        <button className="advanced-toggle" onClick={() => setShowAdvanced(!showAdvanced)}>
          <Settings size={16} />
          Advanced Settings
          {showAdvanced ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>

        {/* Advanced Settings Panel */}
        {showAdvanced && (
          <div className="advanced-settings">
            <ReportSettings
              timeRange={timeRange}
              organizationName={organizationName}
              classification={classification}
              onTimeRangeChange={onTimeRangeChange}
              onOrganizationChange={onOrganizationChange}
              onClassificationChange={onClassificationChange}
            />
          </div>
        )}

        {/* Action Buttons */}
        <ReportActions
          isLoadingPreview={isLoadingPreview}
          isExporting={isExporting}
          exportFormat={exportFormat}
          hasSelectedSections={selectedSections.length > 0}
          onGeneratePreview={onGeneratePreview}
          onExport={onExport}
        />
      </div>
    </div>
  );
}

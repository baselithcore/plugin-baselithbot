import { useState } from 'react';
import {
  FileText,
  Clock,
  Settings,
  ChevronUp,
  ChevronDown,
  Building,
  Lock,
  CheckCircle,
  Eye,
  Loader2,
  FileCode,
  Download,
  Server,
} from 'lucide-react';
import { ReportType, ReportSection, ReportTypesResponse, HoneypotInfo } from '../../types';
import { REPORT_TYPE_ICONS, SECTION_ICONS, TIME_RANGES } from './ReportsConstants';

interface ReportsConfigProps {
  reportTypes: ReportTypesResponse | null;
  honeypots: HoneypotInfo[];
  selectedHoneypotId: string | null;
  selectedType: ReportType;
  selectedSections: ReportSection[];
  timeRange: number;
  organizationName: string;
  classification: string;
  isLoadingPreview: boolean;
  isExporting: boolean;
  exportFormat: 'markdown' | 'pdf';
  onHoneypotChange: (id: string | null) => void;
  onTypeChange: (type: ReportType) => void;
  onSectionsChange: (sections: ReportSection[]) => void;
  onTimeRangeChange: (range: number) => void;
  onOrganizationChange: (name: string) => void;
  onClassificationChange: (classification: string) => void;
  onGeneratePreview: () => void;
  onExport: (format: 'markdown' | 'pdf') => void;
}

export function ReportsConfig({
  reportTypes,
  honeypots,
  selectedHoneypotId,
  selectedType,
  selectedSections,
  timeRange,
  organizationName,
  classification,
  isLoadingPreview,
  isExporting,
  exportFormat,
  onHoneypotChange,
  onTypeChange,
  onSectionsChange,
  onTimeRangeChange,
  onOrganizationChange,
  onClassificationChange,
  onGeneratePreview,
  onExport,
}: ReportsConfigProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  const toggleSection = (section: ReportSection) => {
    onSectionsChange(
      selectedSections.includes(section)
        ? selectedSections.filter((s) => s !== section)
        : [...selectedSections, section]
    );
  };

  return (
    <div className="hp-reports-config">
      {/* Honeypot Selector */}
      <div className="hp-config-section">
        <h3>
          <Server size={16} />
          Honeypot
        </h3>
        <select
          className="hp-select hp-honeypot-selector"
          value={selectedHoneypotId ?? ''}
          onChange={(e) => onHoneypotChange(e.target.value || null)}
        >
          <option value="">All Honeypots</option>
          {honeypots.map((hp) => (
            <option key={hp.id} value={hp.id}>
              {hp.name} ({hp.protocol.toUpperCase()})
            </option>
          ))}
        </select>
      </div>

      <div className="hp-config-section">
        <h3>
          <FileText size={16} />
          Report Type
        </h3>
        <div className="hp-report-types">
          {reportTypes?.types.map((type) => {
            const Icon = REPORT_TYPE_ICONS[type.id as ReportType] || FileText;
            return (
              <button
                key={type.id}
                className={`hp-report-type-btn ${selectedType === type.id ? 'active' : ''}`}
                onClick={() => onTypeChange(type.id as ReportType)}
                title={type.description}
              >
                <Icon size={20} />
                <span>{type.name}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="hp-config-section">
        <h3>
          <Clock size={16} />
          Time Range
        </h3>
        <div className="hp-time-range-selector">
          {TIME_RANGES.map((range) => (
            <button
              key={range.value}
              className={`hp-time-btn ${timeRange === range.value ? 'active' : ''}`}
              onClick={() => onTimeRangeChange(range.value)}
            >
              {range.label}
            </button>
          ))}
        </div>
      </div>

      <div className="hp-config-section">
        <h3>
          <Settings size={16} />
          Sections
        </h3>
        <div className="hp-sections-grid">
          {reportTypes?.sections.map((section) => {
            const Icon = SECTION_ICONS[section.id as ReportSection] || FileText;
            const isSelected = selectedSections.includes(section.id as ReportSection);
            return (
              <button
                key={section.id}
                className={`hp-section-btn ${isSelected ? 'active' : ''}`}
                onClick={() => toggleSection(section.id as ReportSection)}
                title={section.description}
              >
                <Icon size={14} />
                <span>{section.name}</span>
                {isSelected && <CheckCircle size={12} className="hp-section-check" />}
              </button>
            );
          })}
        </div>
      </div>

      {/* Advanced Options */}
      <div className="hp-config-section hp-config-advanced">
        <button className="hp-advanced-toggle" onClick={() => setShowAdvanced(!showAdvanced)}>
          <Settings size={14} />
          Advanced Options
          {showAdvanced ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>

        {showAdvanced && (
          <div className="hp-advanced-options">
            <div className="hp-form-group">
              <label>
                <Building size={14} />
                Organization Name
              </label>
              <input
                type="text"
                className="hp-input"
                placeholder="Your Organization"
                value={organizationName}
                onChange={(e) => onOrganizationChange(e.target.value)}
              />
            </div>

            <div className="hp-form-group">
              <label>
                <Lock size={14} />
                Classification
              </label>
              <select
                className="hp-select"
                value={classification}
                onChange={(e) => onClassificationChange(e.target.value)}
              >
                <option value="PUBLIC">Public</option>
                <option value="INTERNAL">Internal</option>
                <option value="CONFIDENTIAL">Confidential</option>
                <option value="RESTRICTED">Restricted</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="hp-reports-actions">
        <button
          className="hp-btn hp-btn-preview"
          onClick={onGeneratePreview}
          disabled={isLoadingPreview}
        >
          {isLoadingPreview ? (
            <>
              <Loader2 size={16} className="spin" />
              Generating...
            </>
          ) : (
            <>
              <Eye size={16} />
              Preview Report
            </>
          )}
        </button>

        <div className="hp-export-buttons">
          <button
            className="hp-btn hp-btn-export hp-btn-markdown"
            onClick={() => onExport('markdown')}
            disabled={isExporting}
          >
            {isExporting && exportFormat === 'markdown' ? (
              <Loader2 size={16} className="spin" />
            ) : (
              <FileCode size={16} />
            )}
            Markdown
          </button>
          <button
            className="hp-btn hp-btn-export hp-btn-pdf"
            onClick={() => onExport('pdf')}
            disabled={isExporting}
          >
            {isExporting && exportFormat === 'pdf' ? (
              <Loader2 size={16} className="spin" />
            ) : (
              <Download size={16} />
            )}
            PDF
          </button>
        </div>
      </div>
    </div>
  );
}

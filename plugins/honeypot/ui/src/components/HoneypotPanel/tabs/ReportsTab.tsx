/**
 * ReportsTab - Security Report Generator
 *
 * Professional report generation with PDF/Markdown export.
 * Features: Report type selection, preview, customizable sections, export.
 */

import { useState, useEffect, useCallback } from 'react';
import { Sparkles } from 'lucide-react';
import type {
  ReportType,
  ReportSection,
  SecurityReport,
  ReportTypesResponse,
  ReportGenerationRequest,
  HoneypotInfo,
} from '../../types';
import {
  fetchReportTypes,
  fetchHoneypots,
  generateReportPreview,
  downloadMarkdownReport,
  downloadPdfReport,
} from '../../api';
import './ReportsTab.css';
import { ReportsConfig } from '../reports/ReportsConfig';
import { ReportsPreview } from '../reports/ReportsPreview';
import { DEFAULT_SECTIONS } from '../reports/ReportsConstants';

export function ReportsTab() {
  // State
  const [reportTypes, setReportTypes] = useState<ReportTypesResponse | null>(null);
  const [honeypots, setHoneypots] = useState<HoneypotInfo[]>([]);
  const [selectedHoneypotId, setSelectedHoneypotId] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<ReportType>('technical');
  const [selectedSections, setSelectedSections] = useState<ReportSection[]>(
    DEFAULT_SECTIONS.technical
  );
  const [timeRange, setTimeRange] = useState(168);
  const [organizationName, setOrganizationName] = useState('');
  const [classification, setClassification] = useState('INTERNAL');

  // Preview state
  const [preview, setPreview] = useState<SecurityReport | null>(null);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  // Export state
  const [isExporting, setIsExporting] = useState(false);
  const [exportFormat, setExportFormat] = useState<'markdown' | 'pdf'>('markdown');

  // Load report types and honeypots on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        const [types, honeypotList] = await Promise.all([fetchReportTypes(), fetchHoneypots()]);
        setReportTypes(types);
        setHoneypots(honeypotList);
      } catch (err) {
        console.error('Failed to load report data:', err);
      }
    };
    loadData();
  }, []);

  // Update sections when report type changes
  useEffect(() => {
    setSelectedSections(DEFAULT_SECTIONS[selectedType] || []);
  }, [selectedType]);

  // Generate preview
  const handleGeneratePreview = useCallback(async () => {
    try {
      setIsLoadingPreview(true);
      setPreviewError(null);
      const report = await generateReportPreview(
        selectedType,
        timeRange,
        selectedHoneypotId ?? undefined,
        selectedSections
      );
      setPreview(report);
    } catch (err) {
      setPreviewError('Failed to generate preview. Please try again.');
      console.error(err);
    } finally {
      setIsLoadingPreview(false);
    }
  }, [selectedType, timeRange, selectedHoneypotId, selectedSections]);

  // Export report
  const handleExport = useCallback(
    async (format: 'markdown' | 'pdf') => {
      try {
        setIsExporting(true);
        setExportFormat(format);

        const request: ReportGenerationRequest = {
          config: {
            report_type: selectedType,
            format: format,
            sections: selectedSections,
            time_range_hours: timeRange,
            honeypot_id: selectedHoneypotId ?? undefined,
            organization_name: organizationName || undefined,
            classification: classification,
          },
        };

        const blob =
          format === 'markdown'
            ? await downloadMarkdownReport(request)
            : await downloadPdfReport(request);

        // Create download link
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const timestamp = new Date().toISOString().slice(0, 10);
        const isHtml = blob.type === 'text/html';
        const ext = format === 'markdown' ? 'md' : isHtml ? 'html' : 'pdf';
        a.download = `security_report_${selectedType}_${timestamp}.${ext}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } catch (err) {
        console.error('Export failed:', err);
        alert('Failed to export report. Please try again.');
      } finally {
        setIsExporting(false);
      }
    },
    [
      selectedType,
      selectedSections,
      timeRange,
      selectedHoneypotId,
      organizationName,
      classification,
    ]
  );

  return (
    <div className="hp-reports">
      {/* Header */}
      <div className="hp-reports-header">
        <div className="hp-reports-header-left">
          <div className="hp-reports-icon">
            <Sparkles size={24} />
          </div>
          <div>
            <h2>Attack Pattern Research Analysis</h2>
            <p>Analyze and study attack patterns collected from honeypot infrastructure</p>
          </div>
        </div>
      </div>

      <div className="hp-reports-content">
        {/* Configuration Panel */}
        <ReportsConfig
          reportTypes={reportTypes}
          honeypots={honeypots}
          selectedHoneypotId={selectedHoneypotId}
          selectedType={selectedType}
          selectedSections={selectedSections}
          timeRange={timeRange}
          organizationName={organizationName}
          classification={classification}
          isLoadingPreview={isLoadingPreview}
          isExporting={isExporting}
          exportFormat={exportFormat}
          onHoneypotChange={setSelectedHoneypotId}
          onTypeChange={setSelectedType}
          onSectionsChange={setSelectedSections}
          onTimeRangeChange={setTimeRange}
          onOrganizationChange={setOrganizationName}
          onClassificationChange={setClassification}
          onGeneratePreview={handleGeneratePreview}
          onExport={handleExport}
        />

        {/* Preview Panel */}
        <ReportsPreview
          preview={preview}
          isLoading={isLoadingPreview}
          error={previewError}
          selectedType={selectedType}
          classification={classification}
          onRetry={handleGeneratePreview}
        />
      </div>
    </div>
  );
}

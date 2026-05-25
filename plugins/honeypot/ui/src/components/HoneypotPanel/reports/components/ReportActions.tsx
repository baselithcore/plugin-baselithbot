/**
 * Report Actions Component
 *
 * Buttons for previewing and exporting reports.
 */

import { Eye, Loader2, FileCode, Download } from 'lucide-react';

interface ReportActionsProps {
  isLoadingPreview: boolean;
  isExporting: boolean;
  exportFormat: 'markdown' | 'pdf';
  hasSelectedSections: boolean;
  onGeneratePreview: () => void;
  onExport: (format: 'markdown' | 'pdf') => void;
}

export function ReportActions({
  isLoadingPreview,
  isExporting,
  exportFormat,
  hasSelectedSections,
  onGeneratePreview,
  onExport,
}: ReportActionsProps) {
  return (
    <div className="report-actions">
      <button
        className="preview-button"
        onClick={onGeneratePreview}
        disabled={isLoadingPreview || !hasSelectedSections}
      >
        {isLoadingPreview ? (
          <>
            <Loader2 size={20} className="spin" />
            Generating Preview...
          </>
        ) : (
          <>
            <Eye size={20} />
            Generate Preview
          </>
        )}
      </button>

      <div className="export-buttons">
        <button
          className="export-button markdown"
          onClick={() => onExport('markdown')}
          disabled={isExporting || !hasSelectedSections}
        >
          {isExporting && exportFormat === 'markdown' ? (
            <>
              <Loader2 size={20} className="spin" />
              Exporting...
            </>
          ) : (
            <>
              <FileCode size={20} />
              Export Markdown
            </>
          )}
        </button>

        <button
          className="export-button pdf"
          onClick={() => onExport('pdf')}
          disabled={isExporting || !hasSelectedSections}
        >
          {isExporting && exportFormat === 'pdf' ? (
            <>
              <Loader2 size={20} className="spin" />
              Generating PDF...
            </>
          ) : (
            <>
              <Download size={20} />
              Export PDF
            </>
          )}
        </button>
      </div>
    </div>
  );
}

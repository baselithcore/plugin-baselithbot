import { FileText, AlertTriangle, RefreshCw, Loader2 } from 'lucide-react';
import { SecurityReport, ReportType } from '../../types';
import {
  EnhancedExecutiveSummary,
  ThreatOverviewMetrics,
  EnhancedAttackAnalytics,
  EnhancedGeoDistribution,
  BotnetActivity,
  Vulnerabilities,
  IOCList,
  Recommendations,
} from './components/EnhancedReportSections';
import './visualizations/visualizations.css';

interface ReportsPreviewProps {
  preview: SecurityReport | null;
  isLoading: boolean;
  error: string | null;
  selectedType: ReportType;
  classification: string;
  onRetry: () => void;
}

export function ReportsPreview({
  preview,
  isLoading,
  error,
  selectedType,
  classification,
  onRetry,
}: ReportsPreviewProps) {
  if (!preview && !isLoading && !error) {
    return (
      <div className="hp-preview-empty">
        <div className="hp-preview-empty-icon">
          <FileText size={48} />
        </div>
        <h3>No Preview Generated</h3>
        <p>Configure your report settings and click "Preview Report" to see a preview</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="hp-preview-loading">
        <Loader2 size={48} className="spin" />
        <p>Generating report preview...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="hp-preview-error">
        <AlertTriangle size={48} />
        <h3>Preview Failed</h3>
        <p>{error}</p>
        <button className="hp-btn hp-btn-secondary" onClick={onRetry}>
          <RefreshCw size={14} />
          Retry
        </button>
      </div>
    );
  }

  if (!preview) return null;

  return (
    <div className="hp-preview-content">
      {/* Report Header */}
      <div className="hp-preview-header">
        <div className="hp-preview-title">
          <h2>Attack Pattern Research: {selectedType.replace('_', ' ').toUpperCase()}</h2>
          <div className="hp-preview-meta">
            <span className="hp-preview-classification">{classification}</span>
            <span className="hp-preview-id">ID: {preview.metadata.report_id}</span>
            <span className="hp-preview-date">
              {new Date(preview.metadata.generated_at).toLocaleString()}
            </span>
          </div>
        </div>
      </div>

      {/* Threat Overview with Animated Metrics */}
      <ThreatOverviewMetrics report={preview} />

      {/* Executive Summary */}
      {preview.executive_summary && (
        <EnhancedExecutiveSummary content={preview.executive_summary} />
      )}

      {/* Attack Analytics with Charts */}
      <EnhancedAttackAnalytics report={preview} />

      {/* Geographic Distribution with Chart */}
      {preview.geo_distribution && <EnhancedGeoDistribution data={preview.geo_distribution} />}

      {/* Botnet Activity */}
      {preview.botnet_activity && <BotnetActivity data={preview.botnet_activity} />}

      {/* Vulnerabilities */}
      {preview.vulnerabilities && <Vulnerabilities data={preview.vulnerabilities} />}

      {/* IOCs */}
      {preview.iocs && <IOCList data={preview.iocs} />}

      {/* Recommendations */}
      {preview.recommendations && <Recommendations data={preview.recommendations} />}
    </div>
  );
}

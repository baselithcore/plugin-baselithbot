import type { TriageReport } from '../../lib/types';

export function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString('it-IT', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

function _slugifyForFilename(value: string | null | undefined): string {
  return (
    (value ?? 'report')
      .replace(/[^a-zA-Z0-9-_]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .toLowerCase()
      .slice(0, 48) || 'report'
  );
}

function _triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function downloadReportMarkdown(report: TriageReport) {
  const stamp = new Date(report.generated_at).toISOString().slice(0, 16).replace(/[:T]/g, '-');
  const filename = `pretriage-${_slugifyForFilename(report.patient_pseudonym)}-${stamp}.md`;
  const md =
    report.intake_report ??
    `# Pre-triage clinico\n\n_(nessun intake report disponibile)_\n\n` +
      `Codice triage: ${report.triage.code}\n` +
      `Razionale: ${report.triage.rationale}\n`;
  _triggerDownload(new Blob([md], { type: 'text/markdown;charset=utf-8' }), filename);
}

export function downloadReportJson(report: TriageReport) {
  const stamp = new Date(report.generated_at).toISOString().slice(0, 16).replace(/[:T]/g, '-');
  const filename = `pretriage-${_slugifyForFilename(report.patient_pseudonym)}-${stamp}.json`;
  _triggerDownload(
    new Blob([JSON.stringify(report, null, 2)], { type: 'application/json;charset=utf-8' }),
    filename
  );
}

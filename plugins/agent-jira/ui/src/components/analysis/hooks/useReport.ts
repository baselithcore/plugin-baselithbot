import { useState } from 'react';
import { exportPlanReport } from '../../../api/client';
import { AnalysisResponse } from '../../../types';

export const useReport = (onError: (msg: string) => void) => {
  const [downloadingReport, setDownloadingReport] = useState(false);

  const onDownloadReport = async (analysis: AnalysisResponse | null) => {
    if (!analysis) return;
    setDownloadingReport(true);
    try {
      const report = await exportPlanReport({
        plan: analysis.plan,
        metadata: analysis.metadata,
        summary: analysis.summary,
        jira_results: analysis.jira?.results || [],
      });

      const normalizeLinks = (html: string) =>
        html.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, (_m, _text, url) => {
          const safeUrl = String(url);
          return `<a href="${safeUrl}" target="_blank" rel="noreferrer">${safeUrl}</a>`;
        });

      const html = normalizeLinks(report.html);

      // Crea un iframe invisibile per stampare
      const iframe = document.createElement('iframe');
      iframe.style.position = 'fixed';
      iframe.style.right = '0';
      iframe.style.bottom = '0';
      iframe.style.width = '0';
      iframe.style.height = '0';
      iframe.style.border = '0';
      // Use srcdoc for cleaner HTML injection
      iframe.srcdoc = html;
      document.body.appendChild(iframe);

      // Fallback per download diretto
      const downloadHtmlFallback = (htmlContent: string, filename: string) => {
        const blob = new Blob([htmlContent], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename.replace(/\.pdf$/i, '.html');
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      };

      const printAndCleanup = () => {
        try {
          iframe.contentWindow?.focus();
          iframe.contentWindow?.print();
        } catch (e) {
          downloadHtmlFallback(html, report.filename);
          onError('Stampa bloccata: scaricato fallback HTML.');
        } finally {
          setTimeout(() => iframe.remove(), 1000);
        }
      };

      if (iframe.contentWindow && iframe.contentDocument?.readyState === 'complete') {
        printAndCleanup();
      } else {
        iframe.onload = printAndCleanup;
      }
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Errore durante la generazione del report.');
    } finally {
      setDownloadingReport(false);
    }
  };

  return {
    downloadingReport,
    onDownloadReport,
  };
};

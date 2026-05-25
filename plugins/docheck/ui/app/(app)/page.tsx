'use client';

import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';

import Link from 'next/link';
import { ChevronRight, FileText } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { AgentPipeline } from '@/components/AgentPipeline';
import { TopBar } from '@/components/TopBar';
import { AskModal } from '@/components/findings/AskModal';
import { FindingDetailDrawer } from '@/components/findings/FindingDetailDrawer';
import { FindingsPanel } from '@/components/findings/FindingsPanel';
import { Landing } from '@/components/home/Landing';
import { ReasoningDrawer } from '@/components/reasoning/ReasoningDrawer';
import { Button } from '@/components/ui/button';
import { DocumentViewer } from '@/components/viewer/DocumentViewer';
import { getReport, listDecisions } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import { useAnalysisStream } from '@/lib/useAnalysisStream';

export default function HomePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const urlDocId = searchParams.get('doc');
  const urlReportId = searchParams.get('report');
  const tNav = useTranslations('nav.items');

  const docId = useAppStore((s) => s.currentDocId);
  const setDocId = useAppStore((s) => s.setCurrentDocId);
  const report = useAppStore((s) => s.currentReport);
  const setReport = useAppStore((s) => s.setCurrentReport);
  const hydrateDecisions = useAppStore((s) => s.hydrateDecisions);

  // URL → store sync. URL is the source of truth for the workspace target so
  // the view is restorable, shareable, and survives reload.
  useEffect(() => {
    if (urlDocId && urlDocId !== docId) {
      setDocId(urlDocId);
      if (!urlReportId) setReport(null);
    }
  }, [urlDocId, urlReportId, docId, setDocId, setReport]);

  // Clear stale report when URL drops the report param or points to a
  // different one — prevents showing prior findings under the new doc.
  useEffect(() => {
    if (!urlReportId && report) setReport(null);
    else if (urlReportId && report && report.report_id !== urlReportId) setReport(null);
  }, [urlReportId, report, setReport]);

  const reportQuery = useQuery({
    queryKey: ['report', urlReportId],
    queryFn: () => getReport(urlReportId as string),
    enabled: !!urlReportId && report?.report_id !== urlReportId,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    if (reportQuery.data && reportQuery.data.report_id !== report?.report_id) {
      setReport(reportQuery.data);
    }
  }, [reportQuery.data, report?.report_id, setReport]);
  // Skip WS subscription when the doc already has a finalized report —
  // there is no producer to listen to and an idle WS only adds noise.
  const stream = useAnalysisStream(docId, !report?.report_id);

  useEffect(() => {
    if (!report?.report_id) {
      hydrateDecisions({});
      return;
    }
    let cancelled = false;
    listDecisions(report.report_id)
      .then((m) => {
        if (cancelled) return;
        const map: Record<string, 'accepted' | 'rejected' | 'muted'> = {};
        Object.entries(m).forEach(([fid, d]) => {
          if (d.decision) map[fid] = d.decision;
        });
        hydrateDecisions(map);
      })
      .catch(() => {
        /* keep current */
      });
    return () => {
      cancelled = true;
    };
  }, [report?.report_id, hydrateDecisions]);

  return (
    <div className="h-screen flex flex-col">
      <TopBar />
      {urlDocId && (
        <nav
          aria-label="breadcrumb"
          className="px-4 lg:px-6 py-2 border-b border-border bg-bg-panel-soft/60 flex items-center gap-1.5 text-[11px] text-text-muted"
        >
          <Link
            href="/documents"
            className="inline-flex items-center gap-1.5 rounded px-1.5 py-0.5 hover:bg-bg-panel-elev hover:text-text-primary transition-colors ring-focus"
          >
            <FileText size={11} />
            {tNav('documents.label')}
          </Link>
          <ChevronRight size={11} className="text-text-muted/60" />
          <span className="font-mono text-text-secondary">{urlDocId}</span>
          {urlReportId && (
            <>
              <ChevronRight size={11} className="text-text-muted/60" />
              <span className="font-mono text-status-info">{urlReportId}</span>
            </>
          )}
        </nav>
      )}
      {docId && !stream.done && (
        <div className="px-4 lg:px-6 py-2.5 border-b border-border bg-bg-panel/60 backdrop-blur-md">
          <AgentPipeline
            phase={stream.phase}
            progress={stream.progress}
            done={stream.done}
            error={stream.error}
            variant="compact"
          />
        </div>
      )}
      {!docId ? (
        <Landing />
      ) : (
        <main className="flex-1 overflow-hidden">
          <PanelGroup direction="horizontal" autoSaveId="docheck:workspace">
            <Panel defaultSize={60} minSize={38}>
              <DocumentViewer />
            </Panel>
            <PanelResizeHandle className="w-px bg-border hover:bg-status-info/60 transition-colors" />
            <Panel defaultSize={40} minSize={26}>
              <FindingsPanel />
            </Panel>
          </PanelGroup>
        </main>
      )}
      <ReasoningDrawer />
      <FindingDetailDrawer />
      <AskModal />
      {docId && stream.done && (
        <div className="absolute bottom-3 left-1/2 -translate-x-1/2 z-20">
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              setDocId(null);
              setReport(null);
              router.replace('/');
            }}
          >
            ← New analysis
          </Button>
        </div>
      )}
    </div>
  );
}

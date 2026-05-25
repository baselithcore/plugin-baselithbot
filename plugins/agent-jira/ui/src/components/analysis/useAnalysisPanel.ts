import { ChangeEvent, useEffect } from 'react';
import {
  AnalysisResponse,
  JiraIssue,
  JiraProject,
  KbDocumentEntry,
  ScenarioPayload,
  UserStoryPayload,
} from '../../types';
import { ToastPayload } from './FloatingToast';
import { inferDocId } from './analysisUtils';

// Hooks
import { useKbData } from './hooks/useKbData';
import { useAnalysisSession } from './hooks/useAnalysisSession';
import { useJiraData } from './hooks/useJiraData';
import { useJiraSync } from './hooks/useJiraSync';
import { useReport } from './hooks/useReport';
import { useAnalysisPersistence } from './hooks/useAnalysisPersistence';

type UseAnalysisPanelResult = {
  prompt: string;
  setPrompt: (value: string) => void;
  selectedKb: string;
  setSelectedKb: (value: string) => void;
  file: File | null;
  kbDocuments: KbDocumentEntry[];
  analysis: AnalysisResponse | null;
  onFileChange: (event: ChangeEvent<HTMLInputElement>) => void;
  onAnalyze: () => Promise<void>;
  loading: boolean;
  disableAnalyze: boolean;
  error: string | null;
  toast: ToastPayload | null;
  storing: boolean;
  onStore: () => Promise<void>;
  syncing: boolean;
  syncingAllScenarios: boolean;
  scenarioSyncing: string | null;
  onSyncAllScenarios: () => Promise<void>;
  onSyncJira: () => Promise<void>;
  docId: string | null;
  baselineIssues: JiraIssue[];
  historicalIssues: JiraIssue[];
  createdIssues: JiraIssue[];
  storySyncing: string | null;
  onSyncSingleStory: (story: UserStoryPayload) => Promise<void>;
  onSyncScenarios: (story: UserStoryPayload) => Promise<void>;
  onSyncSingleScenario: (story: UserStoryPayload, scenario: ScenarioPayload) => Promise<void>;
  downloadingReport: boolean;
  onDownloadReport: () => Promise<void>;
  jiraProjects: JiraProject[];
  loadingJiraProjects: boolean;
  onSelectStoryProject: (story: UserStoryPayload, projectKey: string | null) => void;
  selectedProjectKey: string;
  onSelectBulkProject: (projectKey: string) => void;
  onResetSession: () => void;
  analysisStartTime: number | null;
};

export const useAnalysisPanel = (initialKb?: {
  path: string;
  timestamp: number;
}): UseAnalysisPanelResult => {
  // 1. KB Data
  const { selectedKb, setSelectedKb, kbDocuments } = useKbData(initialKb);

  // 2. Session (File, Analysis, Error, Toast)
  const {
    prompt,
    setPrompt,
    file,
    setFile,
    analysis,
    setAnalysis,
    loading,
    error,
    setError,
    toast,
    setToast,
    onFileChange,
    onAnalyze,
    storing,
    onStore,
    analysisStartTime,
    resetSession,
  } = useAnalysisSession(selectedKb);

  // 3. Jira Data
  const { jiraProjects, loadingJiraProjects, defaultProjectKey, allowedProjectKeys } =
    useJiraData();

  // 4. Computed docId (needed for Sync and Persistence)
  const docId = inferDocId(analysis, selectedKb, file);

  // 5. Jira Sync & Logic
  const {
    syncing,
    syncingAllScenarios,
    scenarioSyncing,
    storySyncing,
    onSyncJira,
    onSyncSingleStory,
    onSyncScenarios,
    onSyncSingleScenario,
    onSyncAllScenarios,
    selectedProjectKey,
    onSelectBulkProject,
    onSelectStoryProject,
    baselineIssues,
    historicalIssues,
    createdIssues,
    setPersistedJiraByDoc,
    setBaselineJiraByDoc,
  } = useJiraSync({
    analysis,
    docId,
    jiraProjects,
    defaultProjectKey,
    setAnalysis,
    setToast,
  });

  // 6. Persistence & Restoration
  const { autoRunRequested, clearAutoRun, persistAnalysisCache } = useAnalysisPersistence({
    initialKb,
    kbDocuments,
    setSelectedKb,
    setFile,
    analysis,
    setAnalysis,
    file,
    selectedKb,
    setPersistedJiraByDoc,
    setBaselineJiraByDoc,
  });

  // Auto-run analysis if there's an initial KB but no cache was found.
  useEffect(() => {
    if (autoRunRequested && selectedKb && !loading && !analysis) {
      clearAutoRun();
      onAnalyze();
    }
  }, [autoRunRequested, selectedKb, loading, analysis, clearAutoRun, onAnalyze]);

  // 7. Report Generation
  const { downloadingReport, onDownloadReport } = useReport((msg) => setError(msg));

  return {
    prompt,
    setPrompt,
    selectedKb,
    setSelectedKb,
    file,
    kbDocuments,
    analysis,
    onFileChange,
    onAnalyze,
    loading,
    disableAnalyze: loading,
    error,
    toast,
    storing,
    onStore,
    syncing,
    syncingAllScenarios,
    scenarioSyncing,
    onSyncAllScenarios,
    onSyncJira,
    docId,
    baselineIssues,
    historicalIssues,
    createdIssues,
    storySyncing,
    onSyncSingleStory,
    onSyncScenarios,
    onSyncSingleScenario,
    downloadingReport,
    onDownloadReport: () => onDownloadReport(analysis),
    jiraProjects,
    loadingJiraProjects,
    onSelectStoryProject,
    selectedProjectKey,
    onSelectBulkProject,
    onResetSession: () => {
      setSelectedKb('');
      setPrompt('');
      resetSession();
    },
    analysisStartTime,
  };
};

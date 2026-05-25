import { useState, useMemo, useEffect } from 'react';
import { syncJira, syncJiraStory, syncJiraTestCases } from '../../../api/client';
import {
  AnalysisResponse,
  JiraIssue,
  JiraProject,
  ProjectPlanPayload,
  ScenarioPayload,
  UserStoryPayload,
} from '../../../types';
import { mergeJiraResults, historicalIssuesForDoc } from '../analysisUtils';

type UseJiraSyncProps = {
  analysis: AnalysisResponse | null;
  docId: string | null;
  jiraProjects: JiraProject[];
  defaultProjectKey?: string;
  setAnalysis: React.Dispatch<React.SetStateAction<AnalysisResponse | null>>;
  setToast: (payload: any) => void;
};

export const useJiraSync = ({
  analysis,
  docId,
  jiraProjects,
  defaultProjectKey: initialDefaultKey,
  setAnalysis,
  setToast,
}: UseJiraSyncProps) => {
  // Sync States
  const [syncing, setSyncing] = useState(false);
  const [syncingAllScenarios, setSyncingAllScenarios] = useState(false);
  const [scenarioSyncing, setScenarioSyncing] = useState<string | null>(null);
  const [storySyncing, setStorySyncing] = useState<string | null>(null);

  // Selection State
  const [selectedProjectKey, setSelectedProjectKey] = useState<string>('');

  // Data Persistence (in-memory per session)
  const [persistedJiraByDoc, setPersistedJiraByDoc] = useState<Record<string, JiraIssue[]>>({});
  const [baselineJiraByDoc, setBaselineJiraByDoc] = useState<Record<string, JiraIssue[]>>({});

  // Computed
  const currentIssues = useMemo(() => analysis?.jira?.results || [], [analysis]);

  const historicalIssues = useMemo(
    () => historicalIssuesForDoc(docId, currentIssues, persistedJiraByDoc),
    [docId, currentIssues, persistedJiraByDoc]
  );

  const baselineIssues: JiraIssue[] = useMemo(
    () => (docId ? baselineJiraByDoc[docId] || [] : []),
    [docId, baselineJiraByDoc]
  );

  const baselineKeys = useMemo(
    () => new Set(baselineIssues.map((issue) => (issue.key || issue.summary || '').toString())),
    [baselineIssues]
  );

  const createdIssues = useMemo(
    () =>
      currentIssues.filter((issue) => {
        const k = (issue.key || issue.summary || '').toString();
        return k ? !baselineKeys.has(k) : true;
      }),
    [currentIssues, baselineKeys]
  );

  useEffect(() => {
    if (analysis && docId) {
      setBaselineJiraByDoc((prev) => {
        if (prev[docId]) return prev;
        return { ...prev, [docId]: analysis.jira?.results || [] };
      });
    }
  }, [analysis, docId]);

  // Handlers
  const onSelectBulkProject = (key: string) => {
    setSelectedProjectKey(key);
    if (!analysis?.plan?.user_stories) return;

    setAnalysis((prev) => {
      if (!prev?.plan?.user_stories) return prev;
      const nextKey = key || null;
      const updatedStories = prev.plan.user_stories!.map((item) => ({
        ...item,
        jira_project_key: nextKey,
      }));
      return {
        ...prev,
        plan: {
          ...prev.plan,
          user_stories: updatedStories,
        } as ProjectPlanPayload,
      };
    });
  };

  const onSelectStoryProject = (story: UserStoryPayload, projectKey: string | null) => {
    setAnalysis((prev) => {
      if (!prev?.plan?.user_stories) return prev;
      const updatedStories = prev.plan.user_stories!.map((item) =>
        item.title === story.title ? { ...item, jira_project_key: projectKey || null } : item
      );
      return {
        ...prev,
        plan: {
          ...prev.plan,
          user_stories: updatedStories,
        } as ProjectPlanPayload,
      };
    });
  };

  const applyJiraResult = (
    results: JiraIssue[],
    status: string,
    successMessage: string,
    failureMessage: string,
    merge = false
  ) => {
    const isOk = status === 'ok' || status === 'partial';
    // 'partial' status from bulk operations should be considered somewhat success?
    // Original logic: result.status === 'ok' ? successMessage : failureMessage

    const msg = isOk ? successMessage : failureMessage;
    setToast({ message: msg, tone: isOk ? 'success' : 'error' });

    setAnalysis((prev) => {
      if (!prev) return prev;
      const merged = merge ? mergeJiraResults(prev.jira.results, results) : results;

      if (docId) {
        setPersistedJiraByDoc((map) => ({ ...map, [docId]: merged }));
      }

      return {
        ...prev,
        jira: {
          ...prev.jira,
          status: msg,
          results: merged,
        },
      };
    });
  };

  const onSyncJira = async () => {
    if (!analysis?.plan) return;

    // Check validation logic...
    if (jiraProjects.length > 0) {
      const missing = analysis.plan.user_stories?.find((s) => !s.jira_project_key);
      if (missing) {
        setToast({ message: 'Seleziona un progetto Jira per ogni user story.', tone: 'error' });
        return;
      }
    }

    setSyncing(true);
    try {
      const resp = await syncJira({
        plan: analysis.plan,
        kb: analysis.kb,
        metadata: analysis.metadata,
      });
      applyJiraResult(
        resp.results,
        resp.status,
        'User story create su Jira.',
        'Alcune user story hanno generato errori.'
      );
    } catch (err) {
      setToast({
        message: err instanceof Error ? err.message : 'Errore durante la sincronizzazione Jira.',
        tone: 'error',
      });
    } finally {
      setSyncing(false);
    }
  };

  const onSyncSingleStory = async (story: UserStoryPayload) => {
    if (!analysis?.plan) return;
    setStorySyncing(story.title);
    try {
      const resp = await syncJiraStory({
        story,
        kb: analysis.kb,
        metadata: analysis.metadata,
      });
      applyJiraResult(
        resp.results,
        resp.status,
        'User story creata su Jira.',
        'Errore creazione user story.',
        true
      );
    } catch (err) {
      setToast({
        message: err instanceof Error ? err.message : 'Errore sync story.',
        tone: 'error',
      });
    } finally {
      setStorySyncing(null);
    }
  };

  const findStoryKey = (story: UserStoryPayload): string | null => {
    const candidates = analysis?.jira?.results || [];
    const match = candidates.find((issue) => issue.summary === story.title && issue.key);
    return match?.key || null;
  };

  const deriveProjectKey = (story: UserStoryPayload, storyKey?: string | null) => {
    if (story.jira_project_key) return story.jira_project_key;
    if (storyKey && storyKey.includes('-')) return storyKey.split('-', 1)[0];
    return null;
  };

  const onSyncScenarios = async (story: UserStoryPayload) => {
    if (!analysis?.plan) return;
    const kbLabel = analysis?.kb?.label || (analysis as any)?.metadata?.kb_label || null;
    const storyKey = findStoryKey(story);

    if (!storyKey) {
      setToast({ message: 'Crea prima la user story su Jira.', tone: 'error' });
      return;
    }

    setScenarioSyncing(story.title);
    try {
      const result = await syncJiraTestCases({
        story_key: storyKey,
        scenarios: story.scenarios || [],
        project_key: deriveProjectKey(story, storyKey) || undefined,
        kb_label: kbLabel || undefined,
        category: (analysis as any)?.metadata?.category || 'analysis',
      });
      applyJiraResult(
        result.results,
        result.status,
        'Test BDD creati.',
        'Errore creazione test BDD.',
        true
      );
    } catch (err) {
      setToast({
        message: err instanceof Error ? err.message : 'Errore sync scenari',
        tone: 'error',
      });
    } finally {
      setScenarioSyncing(null);
    }
  };

  const onSyncSingleScenario = async (story: UserStoryPayload, scenario: ScenarioPayload) => {
    if (!analysis) return;
    const kbLabel = analysis?.kb?.label || (analysis as any)?.metadata?.kb_label || null;
    const storyKey = findStoryKey(story);
    if (!storyKey) {
      setToast({ message: 'Crea prima la user story su Jira.', tone: 'error' });
      return;
    }

    setScenarioSyncing(scenario.scenario_id || scenario.title);
    try {
      const result = await syncJiraTestCases({
        story_key: storyKey,
        scenarios: [scenario],
        project_key: deriveProjectKey(story, storyKey) || undefined,
        kb_label: kbLabel || undefined,
        category: (analysis as any)?.metadata?.category || 'analysis',
      });
      applyJiraResult(
        result.results,
        result.status,
        'Test BDD creato.',
        'Errore creazione test BDD.',
        true
      );
    } catch (err) {
      setToast({
        message: err instanceof Error ? err.message : 'Errore sync scenario',
        tone: 'error',
      });
    } finally {
      setScenarioSyncing(null);
    }
  };

  const onSyncAllScenarios = async () => {
    if (!analysis?.plan?.user_stories?.length) return;
    const kbLabel = analysis?.kb?.label || (analysis as any)?.metadata?.kb_label || null;

    const storiesWithScenarios = analysis.plan.user_stories.filter(
      (s) => s.scenarios && s.scenarios.length > 0
    );
    if (storiesWithScenarios.length === 0) {
      setToast({ message: 'Nessuno scenario BDD disponibile.', tone: 'error' });
      return;
    }

    const missingStoryKey = storiesWithScenarios.find((s) => !findStoryKey(s));
    if (missingStoryKey) {
      setToast({ message: 'Crea prima tutte le user story su Jira.', tone: 'error' });
      return;
    }

    setSyncingAllScenarios(true);
    setScenarioSyncing('ALL_SCENARIOS');

    let aggregatedResults: JiraIssue[] = [];
    let hasErrors = false;

    try {
      for (const story of storiesWithScenarios) {
        const storyKey = findStoryKey(story) as string;
        const result = await syncJiraTestCases({
          story_key: storyKey,
          scenarios: story.scenarios || [],
          project_key: deriveProjectKey(story, storyKey) || undefined,
          kb_label: kbLabel || undefined,
          category: (analysis as any)?.metadata?.category || 'analysis',
        });
        aggregatedResults = mergeJiraResults(aggregatedResults, result.results);
        if (result.status !== 'ok') hasErrors = true;
      }

      if (aggregatedResults.length === 0) {
        setToast({ message: 'Nessun test BDD creato.', tone: 'error' });
        return;
      }

      applyJiraResult(
        aggregatedResults,
        hasErrors ? 'partial' : 'ok',
        'Test BDD creati.',
        'Errore durante creazione test BDD.',
        true
      );
    } catch (err) {
      setToast({
        message: err instanceof Error ? err.message : 'Errore sync all scenarios',
        tone: 'error',
      });
    } finally {
      setScenarioSyncing(null);
      setSyncingAllScenarios(false);
    }
  };

  // Auto-select default project when available
  useEffect(() => {
    if (initialDefaultKey && !selectedProjectKey && analysis?.plan?.user_stories) {
      onSelectBulkProject(initialDefaultKey);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialDefaultKey, analysis?.plan?.user_stories]);

  return {
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

    docId,
    baselineIssues,
    historicalIssues,
    createdIssues,

    setBaselineJiraByDoc,
    setPersistedJiraByDoc,
  };
};

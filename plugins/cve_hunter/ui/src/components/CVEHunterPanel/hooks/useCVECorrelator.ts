/**
 * useCVECorrelator - Correlator data fetching and feedback handling
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  fetchAttackChains,
  fetchCorrelations,
  fetchUnifiedFindings,
  fetchFindingCorrelations,
  fetchDastFindings,
  fetchFeedbackAudit,
  recordUnifiedFeedback,
  recordDastFeedback,
  recordClassicCorrelationFeedback,
  recordCveCorrelationFeedback,
  recordAttackChainCorrelationFeedback,
  AttackChain,
  CVECorrelation,
  UnifiedFinding,
  FindingCorrelationResponse,
  DastFinding,
  FeedbackAuditItem,
} from '../../api';

export interface UseCVECorrelatorReturn {
  // State
  attackChains: AttackChain[];
  correlations: CVECorrelation[];
  unifiedFindings: UnifiedFinding[];
  dastFindings: DastFinding[];
  findingCorrelations: FindingCorrelationResponse | null;
  feedbackAudit: FeedbackAuditItem[];

  // Computed
  topDastFindings: DastFinding[];
  topUnifiedFindings: UnifiedFinding[];
  filteredFeedback: FeedbackAuditItem[];
  recentFeedback: FeedbackAuditItem[];

  // Feedback filter state
  feedbackFilter: 'all' | 'confirmed' | 'false_positive';
  setFeedbackFilter: React.Dispatch<React.SetStateAction<'all' | 'confirmed' | 'false_positive'>>;
  feedbackQuery: string;
  setFeedbackQuery: React.Dispatch<React.SetStateAction<string>>;

  // Handlers
  handleUnifiedFeedback: (
    findingId: string,
    outcome: 'confirmed' | 'false_positive'
  ) => Promise<void>;
  handleDastFeedback: (findingId: string, outcome: 'confirmed' | 'false_positive') => Promise<void>;
  handleCorrelationFeedback: (
    kind: 'cve' | 'chain',
    id: string,
    outcome: 'confirmed' | 'false_positive'
  ) => Promise<void>;
  handleClassicCorrelationFeedback: (
    correlationId: string,
    outcome: 'confirmed' | 'false_positive'
  ) => Promise<void>;
}

/**
 * Hook for correlator data and feedback handling
 */
export function useCVECorrelator(): UseCVECorrelatorReturn {
  const [attackChains, setAttackChains] = useState<AttackChain[]>([]);
  const [correlations, setCorrelations] = useState<CVECorrelation[]>([]);
  const [unifiedFindings, setUnifiedFindings] = useState<UnifiedFinding[]>([]);
  const [dastFindings, setDastFindings] = useState<DastFinding[]>([]);
  const [findingCorrelations, setFindingCorrelations] = useState<FindingCorrelationResponse | null>(
    null
  );
  const [feedbackAudit, setFeedbackAudit] = useState<FeedbackAuditItem[]>([]);
  const [feedbackFilter, setFeedbackFilter] = useState<'all' | 'confirmed' | 'false_positive'>(
    'all'
  );
  const [feedbackQuery, setFeedbackQuery] = useState('');

  // Load correlator data
  const loadCorrelatorData = useCallback(async () => {
    try {
      const [chainsData, corrsData, unifiedData, findingCorrData, dastData, feedbackData] =
        await Promise.all([
          fetchAttackChains(),
          fetchCorrelations(),
          fetchUnifiedFindings(),
          fetchFindingCorrelations(),
          fetchDastFindings(),
          fetchFeedbackAudit(80),
        ]);
      setAttackChains(chainsData);
      setCorrelations(corrsData);
      setUnifiedFindings(unifiedData);
      setFindingCorrelations(findingCorrData);
      setDastFindings(dastData);
      setFeedbackAudit(feedbackData);
    } catch (err) {
      console.error('Failed to load correlator data', err);
    }
  }, []);

  // Polling for correlator data (30s)
  useEffect(() => {
    loadCorrelatorData();
    const interval = setInterval(loadCorrelatorData, 30000);
    return () => clearInterval(interval);
  }, [loadCorrelatorData]);

  // Computed values
  const topDastFindings = useMemo(() => {
    const sorted = [...dastFindings].sort((a, b) => b.confidence - a.confidence);
    return sorted.slice(0, 6);
  }, [dastFindings]);

  const topUnifiedFindings = useMemo(() => {
    const sorted = [...unifiedFindings].sort((a, b) => b.score - a.score);
    return sorted.slice(0, 6);
  }, [unifiedFindings]);

  const filteredFeedback = useMemo(() => {
    const query = feedbackQuery.trim().toLowerCase();
    return feedbackAudit.filter((item) => {
      if (feedbackFilter !== 'all' && item.outcome !== feedbackFilter) {
        return false;
      }
      if (!query) return true;
      const haystack = `${item.label || ''} ${item.detail || ''} ${item.id || ''} ${
        item.type || ''
      }`.toLowerCase();
      return haystack.includes(query);
    });
  }, [feedbackAudit, feedbackFilter, feedbackQuery]);

  const recentFeedback = useMemo(() => filteredFeedback.slice(0, 8), [filteredFeedback]);

  // Feedback handlers
  const handleUnifiedFeedback = async (
    findingId: string,
    outcome: 'confirmed' | 'false_positive'
  ) => {
    try {
      await recordUnifiedFeedback(findingId, outcome);
      setUnifiedFindings((prev) =>
        prev.map((finding) =>
          finding.finding_id === findingId ? { ...finding, feedback: outcome } : finding
        )
      );
    } catch (err) {
      console.error('Failed to record unified feedback', err);
    }
  };

  const handleDastFeedback = async (findingId: string, outcome: 'confirmed' | 'false_positive') => {
    try {
      await recordDastFeedback(findingId, outcome);
      setDastFindings((prev) =>
        prev.map((finding) =>
          finding.finding_id === findingId ? { ...finding, feedback: outcome } : finding
        )
      );
    } catch (err) {
      console.error('Failed to record DAST feedback', err);
    }
  };

  const handleCorrelationFeedback = async (
    kind: 'cve' | 'chain',
    id: string,
    outcome: 'confirmed' | 'false_positive'
  ) => {
    try {
      if (kind === 'cve') {
        await recordCveCorrelationFeedback(id, outcome);
      } else {
        await recordAttackChainCorrelationFeedback(id, outcome);
      }
      setFindingCorrelations((prev) => {
        if (!prev) return prev;
        if (kind === 'cve') {
          return {
            ...prev,
            cve_correlations: prev.cve_correlations.map((item) =>
              item.correlation_id === id ? { ...item, feedback: outcome } : item
            ),
          };
        }
        return {
          ...prev,
          attack_chain_candidates: prev.attack_chain_candidates.map((item) =>
            item.chain_id === id ? { ...item, feedback: outcome } : item
          ),
        };
      });
    } catch (err) {
      console.error('Failed to record correlation feedback', err);
    }
  };

  const handleClassicCorrelationFeedback = async (
    correlationId: string,
    outcome: 'confirmed' | 'false_positive'
  ) => {
    try {
      await recordClassicCorrelationFeedback(correlationId, outcome);
      setCorrelations((prev) =>
        prev.map((item) =>
          item.correlation_id === correlationId ? { ...item, feedback: outcome } : item
        )
      );
    } catch (err) {
      console.error('Failed to record CVE correlation feedback', err);
    }
  };

  return {
    attackChains,
    correlations,
    unifiedFindings,
    dastFindings,
    findingCorrelations,
    feedbackAudit,
    topDastFindings,
    topUnifiedFindings,
    filteredFeedback,
    recentFeedback,
    feedbackFilter,
    setFeedbackFilter,
    feedbackQuery,
    setFeedbackQuery,
    handleUnifiedFeedback,
    handleDastFeedback,
    handleCorrelationFeedback,
    handleClassicCorrelationFeedback,
  };
}

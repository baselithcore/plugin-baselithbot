import { useState, useEffect, useCallback } from 'react';
import type { DiscoveryResult } from '../../../../types';
import * as api from '../../../../api';

/**
 * Discovery analysis hook with optimized loading.
 *
 * On mount: Fetches cached result for instant display.
 * Manual trigger: Runs full analysis when user clicks "Run Analysis".
 */
export function useDiscoveryAnalysis(_honeypotId?: string | null) {
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<DiscoveryResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stale, setStale] = useState(false);

  // Run fresh analysis (user-triggered)
  const runAnalysis = useCallback(async () => {
    setAnalyzing(true);
    setError(null);

    try {
      // Always analyze ALL honeypots (undefined = no filter)
      const analysisResult = await api.runDiscoveryAnalysis(undefined);
      setResult(analysisResult);
      setStale(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed');
    } finally {
      setAnalyzing(false);
    }
  }, []);

  // Fetch cached result on mount (fast loading)
  useEffect(() => {
    const loadCachedResult = async () => {
      setLoading(true);
      setError(null);

      try {
        // Try to get cached result first (fast)
        const cachedResult = await api.fetchDiscoveryResult(undefined);
        if (cachedResult) {
          setResult(cachedResult);

          // Check if data is stale (older than 24h)
          const analyzedAt = new Date(cachedResult.analyzed_at).getTime();
          const now = Date.now();
          const ageHours = (now - analyzedAt) / (1000 * 60 * 60);
          if (ageHours > 24) {
            setStale(true);
          }
        }
        // If no cached result, leave result as null - user can trigger analysis
      } catch (e) {
        // Silently fail - user can trigger fresh analysis
        console.debug('[Discovery] No cached result available');
      } finally {
        setLoading(false);
      }
    };

    loadCachedResult();
  }, []);

  return { loading, analyzing, result, error, stale, runAnalysis };
}

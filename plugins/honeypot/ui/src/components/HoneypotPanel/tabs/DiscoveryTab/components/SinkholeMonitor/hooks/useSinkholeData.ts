/**
 * Custom hooks for extracting and processing Sinkhole data
 */

import { useMemo } from 'react';
import type { DiscoveryResult } from '../../../../../../types/discovery';

export function useSinkholeData(result: DiscoveryResult) {
  const threatIntel = result.summary?.threat_intel;
  const featureMeta = result.summary?.feature_meta;
  const exploitPatterns = result.summary?.exploit_patterns;

  // JA4 Fingerprints
  const ja4Fingerprints = useMemo(() => {
    const fps = featureMeta?.top_ja4_fingerprints;
    if (!Array.isArray(fps)) return [];
    return fps.slice(0, 5);
  }, [featureMeta]);

  // DNS Anomalies
  const dnsAnomalies = useMemo(() => {
    return result.anomalies
      .filter(
        (a) =>
          a.anomaly_type.includes('dga') ||
          a.anomaly_type.includes('dns') ||
          a.anomaly_type.includes('tunnel')
      )
      .slice(0, 8);
  }, [result.anomalies]);

  // Botnet clusters sorted by size
  const clusters = useMemo(() => {
    return [...result.botnets].sort((a, b) => b.size - a.size).slice(0, 5);
  }, [result.botnets]);

  // IOC Counts
  const iocCount = useMemo(() => {
    const counts = threatIntel?.ioc_count;
    return {
      ips: counts?.ips ?? 0,
      domains: counts?.domains ?? 0,
      hashes: counts?.hashes ?? 0,
    };
  }, [threatIntel]);

  const yaraCount = threatIntel?.yara_rules_generated ?? 0;
  const confidence = threatIntel?.confidence ?? 0;
  const severity = threatIntel?.severity ?? 'info';
  const attackTypes = threatIntel?.attack_types ?? [];
  const mitreTechniques = exploitPatterns?.mitre_techniques ?? [];

  // Get IOC data for modal - data is in anomaly.details (from IOCBundle.to_dict())
  const iocs = useMemo(() => {
    const intelAnomaly = result.anomalies.find(
      (a) => a.anomaly_type === 'threat_intel_generated' || a.anomaly_type.includes('threat_intel')
    );
    const data = intelAnomaly?.details?.iocs;
    return {
      ips: Array.isArray(data?.ips) ? data.ips : [],
      domains: Array.isArray(data?.domains) ? data.domains : [],
      hashes: Array.isArray(data?.hashes) ? data.hashes : [],
    };
  }, [result.anomalies]);

  const yaraRules = useMemo(() => {
    const intelAnomaly = result.anomalies.find(
      (a) => a.anomaly_type === 'threat_intel_generated' || a.anomaly_type.includes('threat_intel')
    );
    return Array.isArray(intelAnomaly?.details?.yara_rules) ? intelAnomaly.details.yara_rules : [];
  }, [result.anomalies]);

  // Recent events for activity feed
  const recentEvents = result.anomalies.slice(0, 8);

  const hasIntelData =
    iocCount.ips > 0 || iocCount.domains > 0 || iocCount.hashes > 0 || yaraCount > 0;

  return {
    ja4Fingerprints,
    dnsAnomalies,
    clusters,
    iocCount,
    yaraCount,
    confidence,
    severity,
    attackTypes,
    mitreTechniques,
    iocs,
    yaraRules,
    recentEvents,
    hasIntelData,
  };
}

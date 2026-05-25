export const getSeverityClass = (severity: string) => {
  switch (severity) {
    case 'critical':
      return 'severity-critical';
    case 'high':
      return 'severity-high';
    case 'medium':
      return 'severity-medium';
    case 'low':
      return 'severity-low';
    default:
      return 'severity-info';
  }
};

export const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

export const filterAnomalies = (result: any, types: string[]) => {
  if (!result) return [];
  return result.anomalies.filter((a: any) => types.some((t: string) => a.anomaly_type.includes(t)));
};

export const getCounts = (result: any, zerodayAnomalies: any[], exploitAnomalies: any[]) => {
  const zerodayCount =
    result?.summary?.zeroday_detection?.zeroday_candidates || zerodayAnomalies.length;
  const exploitCount =
    result?.summary?.exploit_patterns?.patterns_detected || exploitAnomalies.length;
  const iocCount = result?.summary?.threat_intel?.ioc_count || {
    ips: 0,
    domains: 0,
    hashes: 0,
  };
  return { zerodayCount, exploitCount, iocCount };
};

export const getFlagEmoji = (countryCode: string) => {
  if (!countryCode || countryCode.length !== 2) return '';
  const codePoints = countryCode
    .toUpperCase()
    .split('')
    .map((char) => 127397 + char.charCodeAt(0));
  return String.fromCodePoint(...codePoints);
};

import React from 'react';
import { Shield, Zap, Activity, Globe, Target, Users, AlertTriangle } from 'lucide-react';

// Calculate threat score from severity distribution
export const calculateThreatScore = (
  severityBreakdown: Record<string, number> | undefined
): number => {
  if (!severityBreakdown) return 0;
  const weights = { critical: 100, high: 70, medium: 40, low: 15, info: 5 };
  let totalScore = 0;
  let totalEvents = 0;

  Object.entries(severityBreakdown).forEach(([severity, count]) => {
    const weight = weights[severity as keyof typeof weights] || 0;
    totalScore += weight * count;
    totalEvents += count;
  });

  return totalEvents > 0 ? Math.min(100, Math.round(totalScore / totalEvents)) : 0;
};

// Get threat level label from score
export const getThreatLabel = (score: number): string => {
  if (score >= 80) return 'CRITICAL';
  if (score >= 60) return 'HIGH';
  if (score >= 40) return 'ELEVATED';
  if (score >= 20) return 'MODERATE';
  return 'LOW';
};

// Get category icon
export const getCategoryIcon = (category: string) => {
  switch (category.toLowerCase()) {
    case 'brute_force':
      return React.createElement(Shield, { size: 18 });
    case 'sql_injection':
      return React.createElement(Zap, { size: 18 });
    case 'command_injection':
      return React.createElement(Activity, { size: 18 });
    case 'path_traversal':
      return React.createElement(Globe, { size: 18 });
    case 'reconnaissance':
      return React.createElement(Target, { size: 18 });
    case 'credential_harvesting':
      return React.createElement(Users, { size: 18 });
    case 'xss':
      return React.createElement(AlertTriangle, { size: 18 });
    default:
      return React.createElement(AlertTriangle, { size: 18 });
  }
};

// Category colors
export const getCategoryColor = (category: string): string => {
  const colors: Record<string, string> = {
    brute_force: '#ff6b6b',
    sql_injection: '#feca57',
    command_injection: '#ff9ff3',
    path_traversal: '#54a0ff',
    reconnaissance: '#5f27cd',
    credential_harvesting: '#00d2d3',
    xss: '#ff9f43',
    malware_delivery: '#ee5253',
    unknown: '#8395a7',
  };
  return colors[category.toLowerCase()] || '#8395a7';
};

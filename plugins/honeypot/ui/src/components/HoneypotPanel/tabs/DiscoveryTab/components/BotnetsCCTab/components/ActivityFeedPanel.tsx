import { Activity, ExternalLink } from 'lucide-react';
import { ActivityItem } from '../../SinkholeMonitor/components/ActivityItem';
import { EmptyState as SinkholeEmptyState } from '../../SinkholeMonitor/components/EmptyState';
import type { NetworkAnomaly } from '../../../../../../types/discovery';

interface ActivityFeedPanelProps {
  recentEvents: NetworkAnomaly[];
  mitreTechniques: string[];
}

// MITRE ATT&CK technique mappings
const MITRE_TECHNIQUES: Record<string, string> = {
  T1059: 'Command Interpreter',
  T1190: 'Exploit Public App',
  T1110: 'Brute Force',
  T1082: 'System Discovery',
  T1071: 'App Layer Protocol',
  T1021: 'Remote Services',
  T1078: 'Valid Accounts',
  T1105: 'Ingress Tool Transfer',
  T1018: 'Remote System Discovery',
  T1046: 'Network Service Discovery',
  T1595: 'Active Scanning',
  T1055: 'Process Injection',
};

export function ActivityFeedPanel({ recentEvents, mitreTechniques }: ActivityFeedPanelProps) {
  return (
    <>
      {recentEvents.length > 0 ? (
        <div className="activity-feed">
          {recentEvents.map((event: NetworkAnomaly, i: number) => (
            <ActivityItem key={i} event={event} />
          ))}
        </div>
      ) : (
        <SinkholeEmptyState icon={<Activity />} message="No recent activity" />
      )}

      {/* MITRE Techniques */}
      {mitreTechniques.length > 0 && (
        <div style={{ marginTop: '1.5rem' }}>
          <h4
            style={{
              fontSize: '0.75rem',
              color: 'rgba(255,255,255,0.5)',
              marginBottom: '0.75rem',
              textTransform: 'uppercase',
            }}
          >
            MITRE ATT&CK Techniques
          </h4>
          <div className="mitre-list">
            {mitreTechniques.slice(0, 6).map((tech: string) => (
              <a
                key={tech}
                href={`https://attack.mitre.org/techniques/${tech}/`}
                target="_blank"
                rel="noopener noreferrer"
                className="mitre-tag"
              >
                {tech}
                {MITRE_TECHNIQUES[tech] && ` - ${MITRE_TECHNIQUES[tech]}`}
                <ExternalLink />
              </a>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

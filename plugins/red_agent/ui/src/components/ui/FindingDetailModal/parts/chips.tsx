import { Chip } from '../../Badge';
import { Icon } from '../../Icon';
import { riskTone } from '../utils';
import type { AttackTechnique } from '../types';

export function RiskScoreChip({
  score,
  evidence,
}: {
  score: number;
  evidence: Record<string, unknown>;
}) {
  const band = typeof evidence.risk_band === 'string' ? evidence.risk_band : null;
  return (
    <span title={`VPR-style risk score${band ? ` · ${band}` : ''}`}>
      <Chip tone={riskTone(score)}>
        <Icon.Activity size={11} />
        Risk {score.toFixed(1)}
        {band && <span className="opacity-75">· {band}</span>}
      </Chip>
    </span>
  );
}

export function ThreatIntelChips({ evidence }: { evidence: Record<string, unknown> }) {
  const kev = evidence.kev_listed === true;
  const epssRaw = evidence.epss_score;
  const epss = typeof epssRaw === 'string' || typeof epssRaw === 'number' ? Number(epssRaw) : null;
  const techniques = Array.isArray(evidence.attack_techniques)
    ? (evidence.attack_techniques as AttackTechnique[]).slice(0, 2)
    : [];
  const reachableRaw = evidence.reachable;
  const reachable = typeof reachableRaw === 'boolean' ? reachableRaw : null;
  const vexStatusRaw = evidence.vex_status;
  const vexStatus =
    typeof vexStatusRaw === 'string' && vexStatusRaw.length > 0 ? vexStatusRaw : null;
  const greynoiseRaw = evidence.greynoise_classification;
  const greynoise =
    typeof greynoiseRaw === 'string' && greynoiseRaw.length > 0 ? greynoiseRaw : null;
  return (
    <>
      {kev && (
        <span title="CISA Known Exploited Vulnerabilities catalog">
          <Chip tone="critical">
            <Icon.Bug size={11} />
            KEV
          </Chip>
        </span>
      )}
      {epss != null && Number.isFinite(epss) && (
        <span title="FIRST EPSS exploitation probability (next 30 days)">
          <Chip tone={epss >= 0.5 ? 'critical' : epss >= 0.1 ? 'warn' : 'neutral'}>
            EPSS {(epss * 100).toFixed(1)}%
          </Chip>
        </span>
      )}
      {techniques.map((t) => (
        <span key={t.id} title={t.name}>
          <Chip>{t.id}</Chip>
        </span>
      ))}
      {reachable !== null && (
        <span
          title={
            reachable
              ? 'Vulnerable package referenced in source tree'
              : 'No call-graph or import reaches the vulnerable package'
          }
        >
          <Chip tone={reachable ? 'warn' : 'good'}>{reachable ? 'reachable' : 'unreachable'}</Chip>
        </span>
      )}
      {vexStatus && (
        <span title="VEX vendor attestation status">
          <Chip
            tone={
              vexStatus === 'not_affected' || vexStatus === 'fixed'
                ? 'good'
                : vexStatus === 'affected'
                  ? 'critical'
                  : 'neutral'
            }
          >
            VEX {vexStatus.replace(/_/g, ' ')}
          </Chip>
        </span>
      )}
      {greynoise && (
        <span title="GreyNoise reputation classification">
          <Chip tone={greynoise === 'malicious' ? 'critical' : 'neutral'}>GN {greynoise}</Chip>
        </span>
      )}
    </>
  );
}

export function ComplianceChips({ controls }: { controls: string[] }) {
  if (!controls.length) return null;
  const visible = controls.slice(0, 4);
  const overflow = controls.length - visible.length;
  return (
    <>
      {visible.map((c) => (
        <span key={c} title="Compliance control">
          <Chip tone="good">
            <Icon.ShieldCheck size={11} />
            {c}
          </Chip>
        </span>
      ))}
      {overflow > 0 && <Chip tone="neutral">+{overflow}</Chip>}
    </>
  );
}

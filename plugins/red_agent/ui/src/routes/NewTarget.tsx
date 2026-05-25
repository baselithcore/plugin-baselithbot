import { useEffect, useMemo, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api, type ScanIntensity, type TargetCreate, type TargetKind } from '../lib/api';
import { Button, Icon, PageHeader } from '../components/ui';
import {
  type CloudProvider,
  ConfigStep,
  IdentityStep,
  KindStep,
  ProfileStep,
  ReviewStep,
} from './new_target/wizard_steps';
import { scannersForTargetKind } from '../lib/scanners';

const STEPS = ['Kind', 'Identity', 'Configuration', 'Profile', 'Review'] as const;

type Step = 0 | 1 | 2 | 3 | 4;

export function NewTarget() {
  const nav = useNavigate();
  const [step, setStep] = useState<Step>(0);
  const [kind, setKind] = useState<TargetKind | null>(null);
  const [name, setName] = useState('');
  const [environment, setEnvironment] = useState('production');
  const [owner, setOwner] = useState('');
  const [tags, setTags] = useState('');
  const [description, setDescription] = useState('');

  // Web
  const [webUrl, setWebUrl] = useState('');
  // Network
  const [netRange, setNetRange] = useState('');
  // Cloud
  const [cloudProvider, setCloudProvider] = useState<CloudProvider>('aws');
  const [cloudAccountId, setCloudAccountId] = useState('');
  const [cloudCredential, setCloudCredential] = useState('');
  const [cloudRegion, setCloudRegion] = useState('us-east-1');
  // Host
  const [hostAgentUuid, setHostAgentUuid] = useState('');
  // Repo
  const [repoLocation, setRepoLocation] = useState('');
  // Allow loopback / private targets (per-target SSRF bypass)
  const [allowInternal, setAllowInternal] = useState(false);

  // Profile
  const [intensity, setIntensity] = useState<ScanIntensity>('passive');
  const [scanners, setScanners] = useState<string[]>(['nmap', 'nuclei']);
  const [scheduleCron, setScheduleCron] = useState<string>('');

  const targetValue = useMemo(() => {
    if (kind === 'web') return webUrl.trim();
    if (kind === 'network') return netRange.trim();
    if (kind === 'cloud') return `${cloudProvider}:account/${cloudAccountId.trim()}@${cloudRegion}`;
    if (kind === 'host') {
      if (!hostAgentUuid) return '';
      // 'local' is a sentinel chosen in the wizard for "this orchestrator
      // host" — mapped to ``system:local`` so the backend dispatches the
      // in-process self_posture scanner instead of the daemon executor.
      return hostAgentUuid === 'local' ? 'system:local' : `agent:${hostAgentUuid}`;
    }
    if (kind === 'repo') return repoLocation.trim();
    return '';
  }, [
    kind,
    webUrl,
    netRange,
    cloudProvider,
    cloudAccountId,
    cloudRegion,
    hostAgentUuid,
    repoLocation,
  ]);

  const create = useMutation({
    mutationFn: async () => {
      if (!kind) throw new Error('kind missing');
      const body: TargetCreate = {
        kind,
        name: name.trim() || targetValue,
        value: targetValue,
        environment: environment || null,
        owner: owner || null,
        tags: tags
          .split(',')
          .map((t) => t.trim())
          .filter(Boolean),
        description: description || null,
        schedule_cron: scheduleCron || null,
        profile: {
          scanners: targetValue === 'system:local' ? ['self_posture'] : scanners,
          intensity,
        },
        scope_overrides: {
          ...(kind === 'cloud'
            ? {
                cloud: {
                  provider: cloudProvider,
                  account_id: cloudAccountId,
                  region: cloudRegion,
                  credential_ref: cloudCredential,
                },
              }
            : {}),
          ...(allowInternal ? { allow_internal: true } : {}),
        },
      };
      return api.createTarget(body);
    },
    onSuccess: (t) => nav(`/targets/${t.id}`),
  });

  const canContinue = (s: Step): boolean => {
    if (s === 0) return kind !== null;
    if (s === 1) return name.trim().length > 0 || targetValue.length > 0;
    if (s === 2) {
      if (kind === 'web') return /^https?:\/\//.test(webUrl);
      if (kind === 'network') return netRange.length > 0;
      if (kind === 'cloud') return cloudAccountId.length > 0;
      if (kind === 'host') return hostAgentUuid.length > 0;
      if (kind === 'repo') return repoLocation.trim().length > 0;
      return false;
    }
    if (s === 3) return scanners.length > 0;
    return true;
  };

  function next() {
    setStep((s) => Math.min(4, s + 1) as Step);
  }
  function back() {
    setStep((s) => Math.max(0, s - 1) as Step);
  }

  useEffect(() => {
    if (!kind) return;
    const pool = scannersForTargetKind(kind)
      .filter((m) => m.intensities.includes(intensity))
      .map((m) => m.id);
    setScanners((cur) => {
      const filtered = cur.filter((s) => pool.includes(s));
      return filtered.length > 0 ? filtered : pool.slice(0, 2);
    });
  }, [kind, intensity]);

  const resetScannersForIntensity = (i: ScanIntensity) => {
    const pool = kind
      ? scannersForTargetKind(kind)
          .filter((m) => m.intensities.includes(i))
          .map((m) => m.id)
      : [];
    setScanners(pool.slice(0, 2));
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="New target"
        description="Define a persistent target. The Red Agent will scan it on demand or on a schedule and track its security posture over time."
        breadcrumbs={[{ label: 'Targets' }, { label: 'New' }]}
      />

      <ol className="flex flex-wrap gap-2">
        {STEPS.map((label, i) => {
          const active = i === step;
          const done = i < step;
          return (
            <li
              key={label}
              className={`flex items-center gap-2 rounded-md border px-3 py-1.5 text-xs font-mono transition-colors ${
                active
                  ? 'border-brand/60 bg-brand/10 text-brand shadow-glow-soft'
                  : done
                    ? 'border-status-success/40 bg-status-success/10 text-status-success'
                    : 'border-bg-line bg-bg-elevated text-text-muted'
              }`}
            >
              <span className="grid h-4 w-4 place-items-center rounded-full bg-current/20 text-2xs font-semibold">
                {done ? <Icon.Check size={10} /> : i + 1}
              </span>
              <span className="uppercase tracking-wider">{label}</span>
            </li>
          );
        })}
      </ol>

      {step === 0 && <KindStep kind={kind} setKind={setKind} />}

      {step === 1 && (
        <IdentityStep
          name={name}
          setName={setName}
          environment={environment}
          setEnvironment={setEnvironment}
          owner={owner}
          setOwner={setOwner}
          tags={tags}
          setTags={setTags}
          description={description}
          setDescription={setDescription}
        />
      )}

      {step === 2 && (
        <ConfigStep
          kind={kind}
          webUrl={webUrl}
          setWebUrl={setWebUrl}
          netRange={netRange}
          setNetRange={setNetRange}
          cloudProvider={cloudProvider}
          setCloudProvider={setCloudProvider}
          cloudAccountId={cloudAccountId}
          setCloudAccountId={setCloudAccountId}
          cloudCredential={cloudCredential}
          setCloudCredential={setCloudCredential}
          cloudRegion={cloudRegion}
          setCloudRegion={setCloudRegion}
          hostAgentUuid={hostAgentUuid}
          setHostAgentUuid={setHostAgentUuid}
          repoLocation={repoLocation}
          setRepoLocation={setRepoLocation}
          allowInternal={allowInternal}
          setAllowInternal={setAllowInternal}
        />
      )}

      {step === 3 && (
        <ProfileStep
          kind={kind}
          intensity={intensity}
          setIntensity={setIntensity}
          scanners={scanners}
          setScanners={setScanners}
          scheduleCron={scheduleCron}
          setScheduleCron={setScheduleCron}
          resetScannersForIntensity={resetScannersForIntensity}
        />
      )}

      {step === 4 && (
        <ReviewStep
          kind={kind}
          name={name}
          targetValue={targetValue}
          environment={environment}
          owner={owner}
          intensity={intensity}
          scanners={scanners}
          scheduleCron={scheduleCron}
          error={create.error}
        />
      )}

      <div className="flex justify-between">
        <Button variant="ghost" onClick={back} disabled={step === 0}>
          Back
        </Button>
        {step < 4 ? (
          <Button variant="primary" onClick={next} disabled={!canContinue(step)}>
            Continue
            <Icon.ArrowRight size={14} />
          </Button>
        ) : (
          <Button
            variant="primary"
            onClick={() => create.mutate()}
            disabled={create.isPending || !canContinue(step)}
          >
            {create.isPending ? 'Creating…' : 'Create target'}
            <Icon.Bolt size={14} />
          </Button>
        )}
      </div>
    </div>
  );
}

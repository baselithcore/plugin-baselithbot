'use client';

import { useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { useTranslations } from 'next-intl';

import { TopBar } from '@/components/TopBar';
import { PolicyEditorModal, type PolicyMetaForm } from '@/components/policy/PolicyEditorModal';
import { RuleEditorModal } from '@/components/policy/RuleEditorModal';
import { ConfirmDialog } from '@/components/ui/confirm-dialog';
import { CloneDialog, UrlIngestDialog } from '@/components/policy/PolicyDialogs';
import { bumpVersion } from '@/components/policy/PolicyBits';
import { PolicyListAside, type ScopeFilter } from '@/components/policy/PolicyListAside';
import { PolicyDetailPane } from '@/components/policy/PolicyDetailPane';
import { CoverageBanner } from '@/components/policy/CoverageBanner';
import { SuggestRulesDialog } from '@/components/policy/SuggestRulesDialog';
import {
  addRule,
  clonePolicy,
  createPolicy,
  deletePolicy,
  deleteRule,
  exportPolicyYaml,
  importPolicyYaml,
  ingestPolicyFromDocument,
  ingestPolicyFromUrl,
  listPolicies,
  listRules,
  setPolicyActive,
  suggestRulesFromDocument,
  suggestRulesFromUrl,
  updatePolicy,
  updateRule,
  type PolicyRow,
  type RulePayload,
  type RuleRow,
} from '@/lib/api';
import type { SuggestedRule } from '@/lib/api/policies';
import type { CoverageReport } from '@/lib/api/types';

export default function PoliciesPage() {
  const t = useTranslations('policies');
  const qc = useQueryClient();
  const [selected, setSelected] = useState<PolicyRow | null>(null);
  const [query, setQuery] = useState('');
  const [scopeFilter, setScopeFilter] = useState<ScopeFilter>('all');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const docInputRef = useRef<HTMLInputElement>(null);
  const [urlDialogOpen, setUrlDialogOpen] = useState(false);
  const [ingestUrl, setIngestUrl] = useState('');

  const [editorOpen, setEditorOpen] = useState(false);
  const [editorMode, setEditorMode] = useState<'create' | 'edit'>('create');
  const [ruleEditorOpen, setRuleEditorOpen] = useState(false);
  const [ruleEditorMode, setRuleEditorMode] = useState<'create' | 'edit'>('create');
  const [editingRule, setEditingRule] = useState<RuleRow | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<
    null | { kind: 'policy' } | { kind: 'rule'; rule: RuleRow }
  >(null);
  const [confirmClone, setConfirmClone] = useState(false);
  const [cloneVersion, setCloneVersion] = useState('');
  const [suggestOpen, setSuggestOpen] = useState(false);
  const [suggestResults, setSuggestResults] = useState<SuggestedRule[] | null>(null);
  const [lastCoverage, setLastCoverage] = useState<{
    policyId: string;
    policyVersion: string;
    report: CoverageReport;
  } | null>(null);
  const [ingestProgress, setIngestProgress] = useState<{
    phase: 'uploading' | 'processing';
    pct: number;
  } | null>(null);

  const policies = useQuery({ queryKey: ['policies'], queryFn: listPolicies });
  const rules = useQuery({
    queryKey: ['rules', selected?.id, selected?.version],
    queryFn: () => listRules(selected!.id, selected!.version),
    enabled: !!selected,
  });

  const filtered = useMemo(() => {
    const list = policies.data ?? [];
    const q = query.trim().toLowerCase();
    return list.filter((p) => {
      if (scopeFilter !== 'all' && p.scope !== scopeFilter) return false;
      if (!q) return true;
      return p.title.toLowerCase().includes(q) || p.id.toLowerCase().includes(q);
    });
  }, [policies.data, query, scopeFilter]);

  const active = (policies.data ?? []).filter((p) => p.active).length;

  function refreshPolicies() {
    return qc.invalidateQueries({ queryKey: ['policies'] });
  }
  function refreshRules() {
    if (!selected) return Promise.resolve();
    return qc.invalidateQueries({
      queryKey: ['rules', selected.id, selected.version],
    });
  }

  const createMut = useMutation({
    mutationFn: async (args: { form: PolicyMetaForm; firstRule: RulePayload | null }) =>
      createPolicy({
        id: args.form.id,
        version: args.form.version,
        title: args.form.title,
        scope: args.form.scope,
        lang: args.form.lang,
        active: args.form.active,
        rules: args.firstRule ? [args.firstRule] : [],
      }),
    onSuccess: async (row) => {
      toast.success(t('toast.created', { id: row.id, version: row.version }));
      setEditorOpen(false);
      await refreshPolicies();
      setSelected(row);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const updateMut = useMutation({
    mutationFn: async (args: { id: string; version: string; patch: PolicyMetaForm }) =>
      updatePolicy(args.id, args.version, {
        title: args.patch.title,
        scope: args.patch.scope,
        lang: args.patch.lang,
      }),
    onSuccess: async (row) => {
      toast.success(t('toast.updated'));
      setEditorOpen(false);
      await refreshPolicies();
      setSelected(row);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const activeMut = useMutation({
    mutationFn: ({ id, version, active }: { id: string; version: string; active: boolean }) =>
      setPolicyActive(id, version, active),
    onSuccess: async (_d, vars) => {
      toast.success(vars.active ? t('toast.activated') : t('toast.deactivated'));
      await refreshPolicies();
      if (selected && selected.id === vars.id && selected.version === vars.version) {
        setSelected({ ...selected, active: vars.active });
      }
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const cloneMut = useMutation({
    mutationFn: ({
      id,
      version,
      newVersion,
    }: {
      id: string;
      version: string;
      newVersion: string;
    }) => clonePolicy(id, version, newVersion),
    onSuccess: async (row) => {
      toast.success(t('toast.cloned', { id: row.id, version: row.version }));
      setConfirmClone(false);
      setCloneVersion('');
      await refreshPolicies();
      setSelected(row);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const deleteMut = useMutation({
    mutationFn: ({ id, version, force }: { id: string; version: string; force?: boolean }) =>
      deletePolicy(id, version, force),
    onSuccess: async () => {
      toast.success(t('toast.deleted'));
      setConfirmDelete(null);
      setSelected(null);
      await refreshPolicies();
    },
    onError: (e: Error & { status?: number; detail?: string }, vars) => {
      if (e.status === 409 && !vars.force) {
        const msg = e.detail || e.message;
        if (
          typeof window !== 'undefined' &&
          window.confirm(`${msg}\n\nForzare la cancellazione?`)
        ) {
          deleteMut.mutate({ ...vars, force: true });
          return;
        }
      }
      toast.error(e.detail || e.message);
    },
  });

  const ruleAddMut = useMutation({
    mutationFn: (payload: RulePayload) => addRule(selected!.id, selected!.version, payload),
    onSuccess: async () => {
      toast.success(t('toast.ruleAdded'));
      setRuleEditorOpen(false);
      await Promise.all([refreshRules(), refreshPolicies()]);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const ruleUpdateMut = useMutation({
    mutationFn: (args: { ruleId: string; patch: Partial<RulePayload> }) =>
      updateRule(selected!.id, selected!.version, args.ruleId, args.patch),
    onSuccess: async () => {
      toast.success(t('toast.ruleUpdated'));
      setRuleEditorOpen(false);
      await refreshRules();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const ruleDeleteMut = useMutation({
    mutationFn: (rule: RuleRow) => deleteRule(rule.policy_id, rule.policy_version, rule.id),
    onSuccess: async () => {
      toast.success(t('toast.ruleDeleted'));
      setConfirmDelete(null);
      await Promise.all([refreshRules(), refreshPolicies()]);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const importMut = useMutation({
    mutationFn: async (file: File) => {
      setIngestProgress({ phase: 'uploading', pct: 0 });
      try {
        return await importPolicyYaml(file, (e) =>
          setIngestProgress({ phase: e.phase, pct: e.pct })
        );
      } finally {
        setIngestProgress(null);
      }
    },
    onSuccess: async (row) => {
      toast.success(t('toast.imported', { id: row.id, version: row.version }));
      await refreshPolicies();
      setSelected(row);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const ingestUrlMut = useMutation({
    mutationFn: async (url: string) => {
      setIngestProgress({ phase: 'processing', pct: 0 });
      try {
        return await ingestPolicyFromUrl(url);
      } finally {
        setIngestProgress(null);
      }
    },
    onSuccess: async (row) => {
      toast.success(t('toast.ingestUrl', { id: row.id, version: row.version }));
      setUrlDialogOpen(false);
      setIngestUrl('');
      await refreshPolicies();
      setSelected(row);
      if (row.coverage) {
        setLastCoverage({
          policyId: row.id,
          policyVersion: row.version,
          report: row.coverage,
        });
      }
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const ingestDocMut = useMutation({
    mutationFn: async (file: File) => {
      setIngestProgress({ phase: 'uploading', pct: 0 });
      try {
        return await ingestPolicyFromDocument(file, (e) =>
          setIngestProgress({ phase: e.phase, pct: e.pct })
        );
      } finally {
        setIngestProgress(null);
      }
    },
    onSuccess: async (row) => {
      toast.success(t('toast.ingestDoc', { id: row.id, version: row.version }));
      await refreshPolicies();
      setSelected(row);
      if (row.coverage) {
        setLastCoverage({
          policyId: row.id,
          policyVersion: row.version,
          report: row.coverage,
        });
      }
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const suggestFetchMut = useMutation({
    mutationFn: async (url: string) => {
      if (!selected) throw new Error('no policy selected');
      return await suggestRulesFromUrl(selected.id, selected.version, url);
    },
    onSuccess: (rows) => setSuggestResults(rows),
    onError: (e: Error) => toast.error(e.message),
  });

  const suggestFetchDocMut = useMutation({
    mutationFn: async (file: File) => {
      if (!selected) throw new Error('no policy selected');
      return await suggestRulesFromDocument(selected.id, selected.version, file);
    },
    onSuccess: (rows) => setSuggestResults(rows),
    onError: (e: Error) => toast.error(e.message),
  });

  const suggestApplyMut = useMutation({
    mutationFn: async (picked: SuggestedRule[]) => {
      if (!selected) throw new Error('no policy selected');
      // Sequential add: keeps audit log ordering deterministic and avoids
      // bursts against the LLM-free CRUD endpoint.
      for (const r of picked) {
        await addRule(selected.id, selected.version, {
          rule_type: r.rule_type as RulePayload['rule_type'],
          severity: r.severity as RulePayload['severity'],
          excerpt: r.excerpt,
          matcher: r.matcher ?? null,
        });
      }
      return picked.length;
    },
    onSuccess: async (n) => {
      toast.success(t('toast.suggestApplied', { n }));
      setSuggestOpen(false);
      setSuggestResults(null);
      if (selected) {
        await qc.invalidateQueries({
          queryKey: ['rules', selected.id, selected.version],
        });
      }
    },
    onError: (e: Error) => toast.error(e.message),
  });

  function onImportClick() {
    fileInputRef.current?.click();
  }
  function onFilePicked(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    e.target.value = '';
    if (f) importMut.mutate(f);
  }
  function onIngestDocClick() {
    docInputRef.current?.click();
  }
  function onDocPicked(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    e.target.value = '';
    if (f) ingestDocMut.mutate(f);
  }
  async function onExport() {
    if (!selected) return;
    try {
      await exportPolicyYaml(selected.id, selected.version);
    } catch (ex) {
      toast.error(ex instanceof Error ? ex.message : t('toast.exportFailed'));
    }
  }
  function openCreate() {
    setEditorMode('create');
    setEditorOpen(true);
  }
  function openEdit() {
    if (!selected) return;
    setEditorMode('edit');
    setEditorOpen(true);
  }
  function openRuleCreate() {
    setRuleEditorMode('create');
    setEditingRule(null);
    setRuleEditorOpen(true);
  }
  function openRuleEdit(r: RuleRow) {
    setRuleEditorMode('edit');
    setEditingRule(r);
    setRuleEditorOpen(true);
  }

  return (
    <div className="h-screen flex flex-col">
      <TopBar />
      <main className="flex-1 overflow-hidden grid grid-cols-1 xl:grid-cols-[460px_1fr]">
        <PolicyListAside
          active={active}
          totalVersions={policies.data?.length ?? 0}
          query={query}
          onQuery={setQuery}
          scopeFilter={scopeFilter}
          onScopeFilter={setScopeFilter}
          onCreate={openCreate}
          onImportClick={onImportClick}
          onUrlIngestOpen={() => setUrlDialogOpen(true)}
          onIngestDocClick={onIngestDocClick}
          importPending={importMut.isPending}
          ingestUrlPending={ingestUrlMut.isPending}
          ingestDocPending={ingestDocMut.isPending}
          fileInputRef={fileInputRef}
          docInputRef={docInputRef}
          onFilePicked={onFilePicked}
          onDocPicked={onDocPicked}
          isLoading={policies.isLoading}
          error={policies.error}
          filtered={filtered}
          selected={selected}
          onSelect={setSelected}
        />

        <div className="flex flex-col overflow-auto">
          {lastCoverage ? (
            <div className="px-4 pt-4">
              <CoverageBanner
                policyId={lastCoverage.policyId}
                policyVersion={lastCoverage.policyVersion}
                coverage={lastCoverage.report}
                onDismiss={() => setLastCoverage(null)}
              />
            </div>
          ) : null}
          <PolicyDetailPane
            selected={selected}
            rulesData={rules.data}
            rulesLoading={rules.isLoading}
            activePending={activeMut.isPending}
            onToggleActive={() => {
              if (!selected) return;
              activeMut.mutate({
                id: selected.id,
                version: selected.version,
                active: !selected.active,
              });
            }}
            onEdit={openEdit}
            onCloneRequest={() => {
              if (!selected) return;
              setCloneVersion(bumpVersion(selected.version));
              setConfirmClone(true);
            }}
            onExport={onExport}
            onDeletePolicy={() => setConfirmDelete({ kind: 'policy' })}
            onCreateRule={openRuleCreate}
            onSuggestRules={() => {
              if (!selected) return;
              setSuggestResults(null);
              setSuggestOpen(true);
            }}
            onEditRule={openRuleEdit}
            onDeleteRule={(r) => setConfirmDelete({ kind: 'rule', rule: r })}
          />
        </div>
      </main>

      <PolicyEditorModal
        open={editorOpen}
        mode={editorMode}
        initial={
          editorMode === 'edit' && selected
            ? {
                id: selected.id,
                version: selected.version,
                title: selected.title,
                scope: selected.scope,
                lang: selected.lang,
                active: selected.active,
              }
            : undefined
        }
        busy={
          createMut.isPending ||
          updateMut.isPending ||
          ingestUrlMut.isPending ||
          ingestDocMut.isPending ||
          importMut.isPending
        }
        progress={ingestProgress}
        onClose={() => setEditorOpen(false)}
        onSubmit={async (form, firstRule) => {
          if (editorMode === 'create') {
            await createMut.mutateAsync({ form, firstRule });
          } else if (selected) {
            await updateMut.mutateAsync({
              id: selected.id,
              version: selected.version,
              patch: form,
            });
          }
          setEditorOpen(false);
        }}
        onIngest={async (payload) => {
          if (payload.kind === 'url') {
            await ingestUrlMut.mutateAsync(payload.url);
          } else if (payload.kind === 'doc') {
            await ingestDocMut.mutateAsync(payload.file);
          } else {
            await importMut.mutateAsync(payload.file);
          }
          setEditorOpen(false);
        }}
      />

      <RuleEditorModal
        open={ruleEditorOpen}
        mode={ruleEditorMode}
        initial={editingRule}
        busy={ruleAddMut.isPending || ruleUpdateMut.isPending}
        onClose={() => setRuleEditorOpen(false)}
        onSubmit={async (payload) => {
          if (ruleEditorMode === 'create') {
            await ruleAddMut.mutateAsync(payload);
          } else if (editingRule) {
            await ruleUpdateMut.mutateAsync({
              ruleId: editingRule.id,
              patch: {
                rule_type: payload.rule_type,
                severity: payload.severity,
                excerpt: payload.excerpt,
                matcher: payload.matcher,
              },
            });
          }
        }}
      />

      <ConfirmDialog
        open={confirmDelete?.kind === 'policy'}
        onOpenChange={(v) => {
          if (!v) setConfirmDelete(null);
        }}
        title={t('delete.title', {
          id: selected?.id ?? '',
          version: selected?.version ?? '',
        })}
        description={t('delete.description')}
        destructive
        confirmLabel={t('delete.confirm')}
        busy={deleteMut.isPending}
        onConfirm={() => {
          if (!selected) return;
          deleteMut.mutate({ id: selected.id, version: selected.version });
        }}
      />

      <ConfirmDialog
        open={confirmDelete?.kind === 'rule'}
        onOpenChange={(v) => {
          if (!v) setConfirmDelete(null);
        }}
        title={
          confirmDelete?.kind === 'rule' ? t('deleteRule.title', { id: confirmDelete.rule.id }) : ''
        }
        description={t('deleteRule.description')}
        destructive
        confirmLabel={t('deleteRule.confirm')}
        busy={ruleDeleteMut.isPending}
        onConfirm={() => {
          if (confirmDelete?.kind === 'rule') ruleDeleteMut.mutate(confirmDelete.rule);
        }}
      />

      <UrlIngestDialog
        open={urlDialogOpen}
        url={ingestUrl}
        busy={ingestUrlMut.isPending}
        onChange={setIngestUrl}
        onClose={() => setUrlDialogOpen(false)}
        onConfirm={() => {
          const u = ingestUrl.trim();
          if (u) ingestUrlMut.mutate(u);
        }}
      />

      {selected ? (
        <SuggestRulesDialog
          open={suggestOpen}
          policyId={selected.id}
          policyVersion={selected.version}
          fetching={suggestFetchMut.isPending || suggestFetchDocMut.isPending}
          applying={suggestApplyMut.isPending}
          suggestions={suggestResults}
          onFetchUrl={async (u) => {
            await suggestFetchMut.mutateAsync(u);
          }}
          onFetchFile={async (f) => {
            await suggestFetchDocMut.mutateAsync(f);
          }}
          onApply={async (picked) => {
            await suggestApplyMut.mutateAsync(picked);
          }}
          onClose={() => {
            setSuggestOpen(false);
            setSuggestResults(null);
          }}
        />
      ) : null}

      <CloneDialog
        open={confirmClone}
        version={cloneVersion}
        onChange={setCloneVersion}
        busy={cloneMut.isPending}
        onClose={() => setConfirmClone(false)}
        onConfirm={() => {
          if (!selected) return;
          cloneMut.mutate({
            id: selected.id,
            version: selected.version,
            newVersion: cloneVersion,
          });
        }}
      />
    </div>
  );
}

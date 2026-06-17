import { useState } from 'react';
import { Panel } from '../../../../components/Panel';
import { Icon, paths } from '../../../../lib/icons';
import { useSkillAuthorForm } from './hooks';
import type { SkillAuthorProps } from './types';
import { BasicFields } from './parts/BasicFields';
import { InstructionsField } from './parts/InstructionsField';
import { OpenClawSection } from './parts/OpenClawSection';
import { FormActions } from './parts/FormActions';

export { SURFACES, OPENCLAW_OS, SLUG_RE, DEFAULT_TEMPLATE } from './types';
export type { Surface, OpenClawOs, SkillAuthorProps, SubmitPayload } from './types';
export type { SkillAuthorForm } from './hooks';

export function SkillAuthor({
  workspaces,
  installedSlugs,
  pending,
  lastCreated,
  onSubmit,
}: SkillAuthorProps) {
  const [expanded, setExpanded] = useState(false);
  const form = useSkillAuthorForm(installedSlugs, pending);

  const handleSubmit = () => {
    if (!form.canSubmit) return;
    onSubmit(form.buildPayload());
  };

  const handleCancel = () => {
    form.reset();
    setExpanded(false);
  };

  return (
    <Panel title="Author custom skill" tag={expanded ? 'composer' : 'closed'}>
      <div className="skills-callout">
        <div className="skills-callout-title">Create a workspace skill from the UI</div>
        <div className="skills-callout-body">
          The composer writes a validated <code>SKILL.md</code> (YAML frontmatter + instructions)
          and <code>MANIFEST.yaml</code> (bundle version, supported surfaces, passing{' '}
          <code>tested_on</code> entry) bundle, then rescans the workspace so the registry reflects
          the new skill immediately.
        </div>
      </div>

      {!expanded ? (
        <button
          type="button"
          className="btn primary"
          onClick={() => setExpanded(true)}
          style={{ marginTop: 12 }}
        >
          <Icon path={paths.plus} size={12} />
          New custom skill
        </button>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 12 }}>
          <BasicFields form={form} workspaces={workspaces} />
          <InstructionsField
            instructions={form.instructions}
            setInstructions={form.setInstructions}
          />
          <OpenClawSection
            openclawEnabled={form.openclawEnabled}
            setOpenclawEnabled={form.setOpenclawEnabled}
            ocHomepage={form.ocHomepage}
            setOcHomepage={form.setOcHomepage}
            ocUserInvocable={form.ocUserInvocable}
            setOcUserInvocable={form.setOcUserInvocable}
            ocDisableModel={form.ocDisableModel}
            setOcDisableModel={form.setOcDisableModel}
            ocDispatch={form.ocDispatch}
            setOcDispatch={form.setOcDispatch}
            ocCommandTool={form.ocCommandTool}
            setOcCommandTool={form.setOcCommandTool}
            ocCommandArgMode={form.ocCommandArgMode}
            setOcCommandArgMode={form.setOcCommandArgMode}
            ocAlways={form.ocAlways}
            setOcAlways={form.setOcAlways}
            ocEmoji={form.ocEmoji}
            setOcEmoji={form.setOcEmoji}
            ocOs={form.ocOs}
            toggleOcOs={form.toggleOcOs}
            ocPrimaryEnv={form.ocPrimaryEnv}
            setOcPrimaryEnv={form.setOcPrimaryEnv}
            ocSkillKey={form.ocSkillKey}
            setOcSkillKey={form.setOcSkillKey}
            ocReqBins={form.ocReqBins}
            setOcReqBins={form.setOcReqBins}
            ocReqAnyBins={form.ocReqAnyBins}
            setOcReqAnyBins={form.setOcReqAnyBins}
            ocReqEnv={form.ocReqEnv}
            setOcReqEnv={form.setOcReqEnv}
            ocReqConfig={form.ocReqConfig}
            setOcReqConfig={form.setOcReqConfig}
            dispatchConsistent={form.dispatchConsistent}
          />
          <FormActions
            canSubmit={form.canSubmit}
            pending={pending}
            overwrite={form.overwrite}
            setOverwrite={form.setOverwrite}
            lastCreated={lastCreated}
            onSubmit={handleSubmit}
            onCancel={handleCancel}
            onReset={form.reset}
          />
        </div>
      )}
    </Panel>
  );
}

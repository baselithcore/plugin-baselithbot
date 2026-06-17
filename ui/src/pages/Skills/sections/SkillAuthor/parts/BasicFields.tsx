import type { WorkspaceInfo } from '../../../../../lib/api';
import { SURFACES } from '../types';
import type { SkillAuthorForm } from '../hooks';

interface BasicFieldsProps {
  form: Pick<
    SkillAuthorForm,
    | 'slug'
    | 'setSlug'
    | 'name'
    | 'setName'
    | 'description'
    | 'setDescription'
    | 'version'
    | 'setVersion'
    | 'surfaces'
    | 'toggleSurface'
    | 'tagsInput'
    | 'setTagsInput'
    | 'workspace'
    | 'setWorkspace'
    | 'slugValid'
    | 'slugCollides'
  >;
  workspaces: WorkspaceInfo[];
}

export function BasicFields({ form, workspaces }: BasicFieldsProps) {
  const {
    slug,
    setSlug,
    name,
    setName,
    description,
    setDescription,
    version,
    setVersion,
    surfaces,
    toggleSurface,
    tagsInput,
    setTagsInput,
    workspace,
    setWorkspace,
    slugValid,
    slugCollides,
  } = form;

  return (
    <>
      <div className="form-row">
        <label htmlFor="skill-author-slug">Slug</label>
        <input
          id="skill-author-slug"
          className="input"
          placeholder="kebab-or-snake-case, e.g. lead-qualifier"
          value={slug}
          onChange={(event) => setSlug(event.target.value)}
          autoComplete="off"
          spellCheck={false}
        />
        {!slugValid && (
          <div className="info-block" style={{ color: 'var(--danger, #d14)' }}>
            Slug must be 2-63 chars: lowercase letters, digits, <code>-</code> or
            <code> _</code>, starting with a letter or digit.
          </div>
        )}
        {slugCollides && (
          <div className="info-block" style={{ color: 'var(--warn, #c90)' }}>
            A skill with this slug already exists. Toggle "overwrite" to replace it.
          </div>
        )}
      </div>

      <div className="form-row">
        <label htmlFor="skill-author-name">Display name</label>
        <input
          id="skill-author-name"
          className="input"
          placeholder="Lead Qualifier"
          value={name}
          onChange={(event) => setName(event.target.value)}
          maxLength={120}
        />
      </div>

      <div className="form-row">
        <label htmlFor="skill-author-description">Short description</label>
        <input
          id="skill-author-description"
          className="input"
          placeholder="One-sentence trigger describing when the agent should load this skill."
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          maxLength={500}
        />
        <div className="info-block">
          Tight triggers help the orchestrator decide when to activate the skill.
        </div>
      </div>

      <div className="form-row">
        <label htmlFor="skill-author-version">Version</label>
        <input
          id="skill-author-version"
          className="input"
          placeholder="0.1.0"
          value={version}
          onChange={(event) => setVersion(event.target.value)}
          maxLength={32}
        />
      </div>

      <div className="form-row">
        <label>Surfaces</label>
        <div className="skills-chip-row">
          {SURFACES.map((surface) => {
            const active = surfaces.includes(surface);
            return (
              <button
                key={surface}
                type="button"
                className={`badge ${active ? 'ok' : 'muted'}`}
                onClick={() => toggleSurface(surface)}
                style={{ cursor: 'pointer' }}
              >
                {surface}
              </button>
            );
          })}
        </div>
        <div className="info-block">
          Select every surface the skill was authored for. At least one is required.
        </div>
      </div>

      <div className="form-row">
        <label htmlFor="skill-author-tags">Tags (comma separated)</label>
        <input
          id="skill-author-tags"
          className="input"
          placeholder="sales, crm, qualification"
          value={tagsInput}
          onChange={(event) => setTagsInput(event.target.value)}
        />
      </div>

      <div className="form-row">
        <label htmlFor="skill-author-workspace">Workspace</label>
        <select
          id="skill-author-workspace"
          className="input"
          value={workspace}
          onChange={(event) => setWorkspace(event.target.value)}
        >
          <option value="">Global (state root)</option>
          {workspaces.map((ws) => (
            <option key={ws.name} value={ws.name}>
              {ws.name}
              {ws.primary ? ' · primary' : ''}
            </option>
          ))}
        </select>
      </div>
    </>
  );
}

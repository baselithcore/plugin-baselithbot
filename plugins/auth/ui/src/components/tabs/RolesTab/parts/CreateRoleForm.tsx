/** Inline "new role" form with an optional start-from-template selector. */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { RoleTemplate } from '../../../../types';

export interface NewRole {
  slug: string;
  name: string;
  description: string;
}

interface Props {
  templates: RoleTemplate[];
  onCreate: (role: NewRole, template: RoleTemplate | null) => Promise<void>;
  onCancel: () => void;
}

const CreateRoleForm = ({ templates, onCreate, onCancel }: Props) => {
  const { t } = useTranslation();
  const [form, setForm] = useState<NewRole>({ slug: '', name: '', description: '' });
  const [templateSlug, setTemplateSlug] = useState('');
  const [busy, setBusy] = useState(false);

  const pickTemplate = (slug: string) => {
    setTemplateSlug(slug);
    const tpl = templates.find((x) => x.slug === slug);
    if (tpl) {
      setForm((f) => ({
        slug: f.slug || tpl.slug,
        name: f.name || tpl.name,
        description: f.description || tpl.description,
      }));
    }
  };

  const submit = async () => {
    if (!form.slug || !form.name || busy) return;
    setBusy(true);
    try {
      await onCreate(form, templates.find((x) => x.slug === templateSlug) ?? null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="admin-card role-create">
      <input
        className="admin-input"
        placeholder={t('roles.slug')}
        value={form.slug}
        onChange={(e) => setForm({ ...form, slug: e.target.value })}
      />
      <input
        className="admin-input"
        placeholder={t('roles.name')}
        value={form.name}
        onChange={(e) => setForm({ ...form, name: e.target.value })}
      />
      <input
        className="admin-input"
        placeholder={t('roles.description')}
        value={form.description}
        onChange={(e) => setForm({ ...form, description: e.target.value })}
      />
      {templates.length > 0 && (
        <select
          className="admin-input admin-select"
          value={templateSlug}
          onChange={(e) => pickTemplate(e.target.value)}
          aria-label={t('roles.template')}
        >
          <option value="">{t('roles.templateNone')}</option>
          {templates.map((tpl) => (
            <option key={tpl.slug} value={tpl.slug}>
              {tpl.name}
            </option>
          ))}
        </select>
      )}
      <button className="admin-btn admin-btn-primary" onClick={submit} disabled={busy}>
        {t('common.create')}
      </button>
      <button className="admin-btn admin-btn-ghost" onClick={onCancel} disabled={busy}>
        {t('common.cancel')}
      </button>
    </div>
  );
};

export default CreateRoleForm;

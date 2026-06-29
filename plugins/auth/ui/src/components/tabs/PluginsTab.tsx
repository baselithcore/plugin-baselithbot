/**
 * Plugins tab — per-plugin tenancy-mode overrides.
 *
 * Each loaded plugin declares a tenancy model in its manifest (`shared` =
 * 1 tenant ⇒ N users, deployment-derived; `personal` = 1 user ⇒ 1 tenant). An
 * admin can override that at runtime here. Changing a plugin that already holds
 * data only changes which tenant key *new* reads/writes use — existing rows stay
 * under their old key — so the screen warns before a switch takes effect.
 */

import { useEffect, useState } from 'react';
import { Puzzle, AlertTriangle, Lock } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  getPluginTenancy,
  setPluginTenancy,
  type PluginTenancyRow,
  type TenancyMode,
} from '../../api/plugins';

export default function PluginsTab() {
  const { t } = useTranslation();
  const [rows, setRows] = useState<PluginTenancyRow[]>([]);
  const [msg, setMsg] = useState('');
  const [loaded, setLoaded] = useState(false);

  const reload = () =>
    getPluginTenancy()
      .then((d) => setRows(d.plugins))
      .catch((e) => setMsg(e instanceof Error ? e.message : 'Error'))
      .finally(() => setLoaded(true));

  useEffect(() => {
    reload();
  }, []);

  const onChange = async (row: PluginTenancyRow, value: string) => {
    const mode: TenancyMode | null = value === '' ? null : (value as TenancyMode);
    // A switch re-scopes future reads/writes — confirm the migration caveat.
    if (mode !== row.override && !window.confirm(t('plugins.confirm_switch'))) return;
    try {
      await setPluginTenancy(row.plugin_name, mode);
      await reload();
      setMsg(t('plugins.saved'));
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Error');
    }
  };

  return (
    <div className="admin-tab-content">
      <div className="admin-section-header">
        <h2>
          <Puzzle size={20} /> {t('plugins.title')}
        </h2>
        <p>{t('plugins.description')}</p>
      </div>

      {msg && <div className="admin-alert">{msg}</div>}

      <div
        className="admin-card"
        style={{ padding: 14, marginBottom: 18, display: 'flex', gap: 10 }}
      >
        <AlertTriangle size={18} style={{ flexShrink: 0, color: 'var(--admin-warning, #b45309)' }} />
        <p style={{ margin: 0, fontSize: 13, opacity: 0.85 }}>{t('plugins.migration_warning')}</p>
      </div>

      <div className="admin-card" style={{ padding: 0, overflow: 'hidden' }}>
        <table className="admin-table" style={{ width: '100%' }}>
          <thead>
            <tr>
              <th>{t('plugins.col_plugin')}</th>
              <th>{t('plugins.col_declared')}</th>
              <th>{t('plugins.col_override')}</th>
              <th>{t('plugins.col_effective')}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.plugin_name}>
                <td>
                  {r.plugin_name}
                  {r.version && <span style={{ opacity: 0.5 }}> v{r.version}</span>}
                  {r.system && (
                    <span
                      style={{
                        marginLeft: 6,
                        fontSize: 10,
                        padding: '1px 6px',
                        borderRadius: 6,
                        background: 'var(--admin-chip-bg, rgba(127,127,127,0.15))',
                      }}
                    >
                      {t('plugins.system')}
                    </span>
                  )}
                </td>
                <td>
                  <code style={{ fontSize: 12 }}>{t(`plugins.mode_${r.declared_tenancy}`)}</code>
                </td>
                <td>
                  {r.locked ? (
                    <span
                      title={t('plugins.locked_reason')}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 5,
                        fontSize: 12,
                        opacity: 0.7,
                      }}
                    >
                      <Lock size={13} /> {t('plugins.locked')}
                    </span>
                  ) : (
                    <select
                      className="admin-input"
                      value={r.override ?? ''}
                      onChange={(e) => onChange(r, e.target.value)}
                      style={{ width: 160 }}
                    >
                      <option value="">{t('plugins.inherit')}</option>
                      <option value="shared">{t('plugins.mode_shared')}</option>
                      <option value="personal">{t('plugins.mode_personal')}</option>
                    </select>
                  )}
                </td>
                <td>
                  <strong style={{ fontSize: 12 }}>
                    {t(`plugins.mode_${r.effective_tenancy}`)}
                  </strong>
                  {r.override && (
                    <span style={{ marginLeft: 6, fontSize: 11, opacity: 0.6 }}>
                      {t('plugins.overridden')}
                    </span>
                  )}
                </td>
              </tr>
            ))}
            {loaded && rows.length === 0 && (
              <tr>
                <td colSpan={4} style={{ textAlign: 'center', padding: 24, opacity: 0.7 }}>
                  {t('plugins.empty')}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

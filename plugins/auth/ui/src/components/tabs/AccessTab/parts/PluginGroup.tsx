/** A collapsible section grouping all discovered tabs of one plugin. */

import { useState } from 'react';
import { ChevronDown, ChevronRight, Puzzle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { RbacRole } from '../../../../types';
import type { PluginGroupData } from '../helpers';
import TabRow from './TabRow';

interface Props {
  group: PluginGroupData;
  grantableRoles: RbacRole[];
  hasWildcardRole: boolean;
  onSetRestricted: (plugin: string, tabId: string, restricted: boolean) => void;
  onToggleRole: (role: RbacRole, slug: string, granted: boolean) => void;
}

const PluginGroup = ({
  group,
  grantableRoles,
  hasWildcardRole,
  onSetRestricted,
  onToggleRole,
}: Props) => {
  const { t } = useTranslation();
  const [open, setOpen] = useState(true);

  return (
    <section className="pgroup">
      <button type="button" className="pgroup-head" onClick={() => setOpen((v) => !v)}>
        {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        <span className="pgroup-ico">
          <Puzzle size={18} />
        </span>
        <span className="pgroup-meta">
          <span className="pgroup-name">
            {group.label}
            {group.system && <span className="sys-badge">{t('access.system')}</span>}
          </span>
          <code className="pgroup-slug">{group.plugin}</code>
        </span>
        <span className="pgroup-count">{t('access.tabsCount', { count: group.tabs.length })}</span>
      </button>

      {open &&
        group.tabs.map((tab) => (
          <TabRow
            key={`${tab.plugin}:${tab.tab_id}`}
            tab={tab}
            grantableRoles={grantableRoles}
            hasWildcardRole={hasWildcardRole}
            onSetRestricted={(restricted) => onSetRestricted(tab.plugin, tab.tab_id, restricted)}
            onToggleRole={onToggleRole}
          />
        ))}
    </section>
  );
};

export default PluginGroup;

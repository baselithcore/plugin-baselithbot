import type { ReactElement } from 'react';
import { useAuth } from '@auth';
import { useTranslation } from 'react-i18next';

import { Shell } from './components/Shell';
import { useUI } from './store/useUI';
import { IncidentsPage } from './pages/IncidentsPage';
import { DoraPage } from './pages/DoraPage';
import { DsrPage } from './pages/DsrPage';
import { ThirdPartyPage } from './pages/ThirdPartyPage';
import { TransparencyPage } from './pages/TransparencyPage';
import type { TabId } from './types';

const PAGES: Record<TabId, () => ReactElement> = {
  incidents: IncidentsPage,
  dora: DoraPage,
  dsr: DsrPage,
  thirdparty: ThirdPartyPage,
  transparency: TransparencyPage,
};

export default function App() {
  const { tab } = useUI();
  const { canAccessTab } = useAuth();
  const { t } = useTranslation();

  // Per-tab visibility from the central RBAC matrix (default-allow until known).
  const visible = canAccessTab(tab, 'compliance');
  const Page = PAGES[tab];

  return <Shell>{visible ? <Page /> : <p className="empty">{t('access.denied')}</p>}</Shell>;
}

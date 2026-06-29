import type { ReactElement } from 'react';
import { useAuth } from '@auth';
import { useTranslation } from 'react-i18next';

import { Shell } from './components/Shell';
import { useTheme } from './theme';
import { useUI } from './store/useUI';
import { OverviewPage } from './pages/OverviewPage';
import { IncidentsPage } from './pages/IncidentsPage';
import { DoraPage } from './pages/DoraPage';
import { DsrPage } from './pages/DsrPage';
import { ThirdPartyPage } from './pages/ThirdPartyPage';
import { TransparencyPage } from './pages/TransparencyPage';
import type { TabId } from './types';

const PAGES: Record<TabId, () => ReactElement> = {
  overview: OverviewPage,
  incidents: IncidentsPage,
  dora: DoraPage,
  dsr: DsrPage,
  thirdparty: ThirdPartyPage,
  transparency: TransparencyPage,
};

export default function App() {
  useTheme(); // applies the persisted theme to <html data-theme> on first paint
  const { tab } = useUI();
  const { canAccessTab } = useAuth();
  const { t } = useTranslation();

  // Per-tab visibility from the central RBAC matrix (default-allow until known).
  const visible = tab === 'overview' || canAccessTab(tab, 'compliance');
  const Page = PAGES[tab];

  return <Shell>{visible ? <Page /> : <p className="empty">{t('access.denied')}</p>}</Shell>;
}

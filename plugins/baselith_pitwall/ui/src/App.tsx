import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@auth';
import { ProtectedRoute } from '@auth/login';
import { usePitwall } from './hooks/usePitwall';
import type { SectionId } from './lib/sections';
import { TopHud } from './components/shell/TopHud';
import { SideNav } from './components/shell/SideNav';
import { MainArea } from './components/shell/MainArea';
import { RecommendationFeed } from './components/RecommendationFeed';

const TAB_ID = 'baselith_pitwall';

export default function App() {
  return (
    <ProtectedRoute>
      <PitwallApp />
    </ProtectedRoute>
  );
}

function PitwallApp() {
  const { t } = useTranslation();
  const { user, logout, canAccessTab } = useAuth();
  const pit = usePitwall();
  const [section, setSection] = useState<SectionId>('command');

  // Central RBAC gate (default-allow: never blocks normal use, no login wall).
  if (!canAccessTab(TAB_ID, 'baselith_pitwall')) {
    return (
      <div className="grid min-h-screen place-items-center px-4 text-center">
        <div>
          <h1 className="font-display text-xl font-bold text-ink">{t('accessDenied')}</h1>
          <p className="mt-2 text-sm text-faint">{t('accessDeniedBody')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <TopHud
        status={pit.status}
        cars={pit.cars}
        car={pit.car}
        onCar={pit.setCar}
        user={user}
        onLogout={() => logout()}
        onSessionChange={pit.setSession}
      />

      <div className="mx-auto grid max-w-[1700px] gap-4 p-4 lg:grid-cols-[196px_minmax(0,1fr)_360px] lg:p-5">
        <SideNav active={section} onSelect={setSection} />

        <main className="min-w-0">
          <MainArea
            section={section}
            car={pit.car}
            stint={pit.stint}
            scenario={pit.scenario}
            simulate={pit.simulate}
            busy={pit.busy}
            signals={pit.signals}
            recs={pit.recs}
            session={pit.session}
          />
        </main>

        <aside className="lg:sticky lg:top-[92px] lg:h-[calc(100vh-112px)]">
          <RecommendationFeed recs={pit.recs} />
        </aside>
      </div>
    </div>
  );
}

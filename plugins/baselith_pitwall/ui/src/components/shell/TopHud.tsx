import { useTranslation } from 'react-i18next';
import { LogOut } from 'lucide-react';
import type { Status } from '../../types';
import { Select } from '../ui';
import { Brand } from './Brand';
import { TelemetryStrip } from './TelemetryStrip';
import { SessionBar } from '../SessionBar';
import { LangSwitch } from '../LangSwitch';

interface User {
  username?: string | null;
  email?: string | null;
}

interface Props {
  status: Status | null;
  cars: string[];
  car: string | null;
  onCar: (id: string) => void;
  user: User | null;
  onLogout: () => void;
  onSessionChange: (id: string) => void;
}

/** Sticky command-bar header: identity, session control, live telemetry, and
 * the active-car / locale / account controls. */
export function TopHud({ status, cars, car, onCar, user, onLogout, onSessionChange }: Props) {
  const { t } = useTranslation();
  return (
    <header className="glass sticky top-0 z-30 rounded-none border-x-0 border-t-0 px-4 py-3 lg:px-6">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-3">
        <Brand />

        <div className="order-3 w-full lg:order-2 lg:w-auto lg:flex-1">
          <TelemetryStrip status={status} />
        </div>

        <div className="order-2 ml-auto flex flex-wrap items-center gap-2 lg:order-3">
          <SessionBar onSessionChange={onSessionChange} />
          {cars.length > 0 && (
            <Select value={car ?? ''} onChange={onCar} ariaLabel={t('selectCar')} className="w-32">
              {cars.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </Select>
          )}
          <LangSwitch />
          {user && (
            <div className="flex items-center gap-1.5">
              <span className="hidden rounded-lg border border-hair bg-surface-2 px-3 py-1.5 text-sm text-dim sm:block">
                {user.username || user.email}
              </span>
              <button
                onClick={onLogout}
                title={t('logout')}
                className="grid h-9 w-9 place-items-center rounded-lg border border-hair bg-surface-2 text-dim transition hover:border-ember/40 hover:text-ember"
              >
                <LogOut size={16} />
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

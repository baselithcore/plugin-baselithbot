import { useTranslation } from 'react-i18next';
import { SECTIONS, type SectionId } from '../../lib/sections';

interface Props {
  active: SectionId;
  onSelect: (id: SectionId) => void;
  /** Per-section live counts (e.g. pending acks) shown as a dot. */
  badges?: Partial<Record<SectionId, boolean>>;
}

/** Vertical icon rail for switching the main work area. Labels show on wide
 * viewports; on narrow it collapses to a horizontal icon bar. */
export function SideNav({ active, onSelect, badges = {} }: Props) {
  const { t } = useTranslation();
  return (
    <nav className="flex gap-1.5 lg:flex-col lg:gap-2">
      {SECTIONS.map(({ id, icon: Icon, labelKey }) => {
        const on = id === active;
        return (
          <button
            key={id}
            onClick={() => onSelect(id)}
            title={t(labelKey)}
            aria-current={on ? 'page' : undefined}
            className={`group relative flex flex-1 items-center gap-3 rounded-xl border px-3 py-2.5 text-sm font-medium transition lg:flex-none ${
              on
                ? 'border-ember/40 bg-ember/10 text-ink'
                : 'border-transparent text-dim hover:border-hair hover:bg-surface-2/60 hover:text-ink'
            }`}
          >
            <span
              className={`absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-ember transition-opacity ${
                on ? 'opacity-100' : 'opacity-0'
              }`}
            />
            <Icon size={18} className={on ? 'text-ember' : ''} />
            <span className="hidden lg:inline">{t(labelKey)}</span>
            {badges[id] && (
              <span className="ml-auto hidden h-1.5 w-1.5 rounded-full bg-caution lg:block" />
            )}
          </button>
        );
      })}
    </nav>
  );
}

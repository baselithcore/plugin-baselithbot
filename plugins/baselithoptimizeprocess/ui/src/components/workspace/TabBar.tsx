import { motion, useReducedMotion } from 'motion/react';
import { useAuth } from '@auth';

import { cn } from '../../lib/ui';
import { PLUGIN, TABS, type Tab } from './types';

interface TabBarProps {
  active: Tab;
  onChange: (tab: Tab) => void;
}

/**
 * Horizontal, scrollable tab bar with an animated active indicator — a real
 * segmented control instead of a wall of cards.
 */
export function TabBar({ active, onChange }: TabBarProps) {
  const reduceMotion = useReducedMotion();
  const { canAccessTab } = useAuth();
  // Hide sections the central RBAC policy denies for this caller.
  const tabs = TABS.filter((t) => canAccessTab(t.id, PLUGIN));
  const activeDetail = tabs.find((t) => t.id === active)?.detail;

  return (
    <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2">
      <div
        role="tablist"
        aria-label="Process workspace sections"
        className="-mx-1 flex min-w-0 flex-1 items-center gap-0.5 overflow-x-auto px-1 pb-px
          [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {tabs.map(({ id, label, icon: Icon }) => {
          const isActive = id === active;
          return (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={isActive}
              aria-current={isActive ? 'page' : undefined}
              onClick={() => onChange(id)}
              className={cn('tab', isActive && 'bg-accent/[0.06]')}
            >
              <Icon
                size={16}
                strokeWidth={2}
                className={cn(isActive ? 'text-accent-soft' : 'text-slate-500')}
                aria-hidden="true"
              />
              {label}
              {isActive &&
                (reduceMotion ? (
                  <span className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-accent" />
                ) : (
                  <motion.span
                    layoutId="tab-underline"
                    transition={{ type: 'spring', stiffness: 480, damping: 38 }}
                    className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-accent"
                  />
                ))}
            </button>
          );
        })}
      </div>
      <p className="hidden shrink-0 text-xs text-slate-500 lg:block">{activeDetail}</p>
    </div>
  );
}

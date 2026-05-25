import React from 'react';
import { DEFAULT_NODE_COLORS, DEFAULT_NODE_LABELS_EN } from './constants';

interface GraphLegendProps {
  legendData?: Record<string, { color: string; label: string }>;
  activeFilters: Set<string>;
  toggleFilter: (group: string) => void;
}

export const GraphLegend: React.FC<GraphLegendProps> = ({
  legendData,
  activeFilters,
  toggleFilter,
}) => {
  const groups = legendData ? Object.keys(legendData) : Object.keys(DEFAULT_NODE_COLORS);

  return (
    <div className="absolute top-4 right-4 bg-white/90 dark:bg-slate-900/90 backdrop-blur p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xl max-h-[80%] overflow-y-auto z-10">
      <h3 className="text-sm font-bold mb-3 text-slate-800 dark:text-slate-100 uppercase tracking-wider">
        Legend & Filters
      </h3>
      <div className="flex flex-col gap-2">
        {groups.map((group) => {
          const color = legendData?.[group]?.color || DEFAULT_NODE_COLORS[group] || '#6b7280';
          const label = legendData?.[group]?.label || DEFAULT_NODE_LABELS_EN[group] || group;
          const isActive = activeFilters.has(group);

          return (
            <button
              key={group}
              onClick={() => toggleFilter(group)}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200 text-left border ${
                isActive
                  ? 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 shadow-sm opacity-100'
                  : 'bg-slate-50 dark:bg-slate-900/50 border-transparent opacity-50 grayscale-[0.5]'
              } hover:opacity-100 hover:grayscale-0`}
            >
              <div className="w-3 h-3 rounded-full shadow-sm" style={{ backgroundColor: color }} />
              <span className="text-xs font-medium text-slate-700 dark:text-slate-300">
                {label}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};

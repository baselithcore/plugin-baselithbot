import React from 'react';
import { Node } from './types';
import { cleanText } from './utils';

interface GraphTooltipProps {
  node: Node | null;
}

export const GraphTooltip: React.FC<GraphTooltipProps> = ({ node }) => {
  if (!node) return null;

  return (
    <div className="absolute bottom-6 left-6 p-6 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md rounded-2xl border border-slate-200 dark:border-slate-700 shadow-2xl max-w-sm pointer-events-none z-20 animate-in fade-in slide-in-from-bottom-4 duration-300">
      <div className="flex items-center gap-3 mb-4">
        <div
          className="w-4 h-4 rounded-full shadow-sm ring-4 ring-white dark:ring-slate-800"
          style={{ backgroundColor: node.group === 'Story' ? '#f59e0b' : '#3b82f6' }}
        />
        <h4 className="text-sm font-bold text-slate-900 dark:text-slate-50 uppercase tracking-widest">
          {node.group} Details
        </h4>
      </div>

      <p className="text-base font-semibold text-slate-800 dark:text-slate-100 leading-relaxed mb-4">
        {cleanText(node.label)}
      </p>

      <div className="space-y-3">
        {node.properties &&
          Object.entries(node.properties).map(([key, value]) => {
            if (['id', 'label', 'group', 'content'].includes(key)) return null;
            if (!value) return null;

            return (
              <div key={key} className="flex flex-col gap-1">
                <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-tighter">
                  {key.replace(/_/g, ' ')}
                </span>
                <span className="text-xs font-medium text-slate-600 dark:text-slate-300 line-clamp-3">
                  {typeof value === 'string' ? cleanText(value) : JSON.stringify(value)}
                </span>
              </div>
            );
          })}
      </div>
    </div>
  );
};

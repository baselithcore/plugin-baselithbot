import type { ReactNode } from 'react';
import { motion } from 'motion/react';
import { fadeUp } from '../lib/motion';

interface GlassPanelProps {
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

/** Frosted-glass surface used as the primary content container. */
export function GlassPanel({
  title,
  subtitle,
  actions,
  children,
  className = '',
}: GlassPanelProps) {
  return (
    <motion.section
      variants={fadeUp}
      initial="hidden"
      animate="show"
      className={`glass rounded-2xl shadow-glass p-5 ${className}`}
    >
      {(title || actions) && (
        <header className="mb-4 flex items-start justify-between gap-4">
          <div>
            {title && (
              <h2 className="text-base font-semibold tracking-tight text-slate-100">{title}</h2>
            )}
            {subtitle && <p className="mt-1 text-sm text-slate-400">{subtitle}</p>}
          </div>
          {actions}
        </header>
      )}
      {children}
    </motion.section>
  );
}

import type { ReactNode } from 'react';
import { motion } from 'framer-motion';

interface Props {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ icon, title, description, action }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="h-full flex flex-col items-center justify-center text-center px-8 py-12 gap-3"
    >
      {icon && (
        <div
          className="w-10 h-10 rounded-lg flex items-center justify-center border"
          style={{
            background: 'rgb(var(--surface-2) / 0.58)',
            color: 'rgb(var(--text-muted))',
            borderColor: 'rgb(var(--border-subtle))',
          }}
        >
          {icon}
        </div>
      )}
      <div className="flex flex-col gap-1 max-w-sm">
        <h3 className="text-sm font-semibold">{title}</h3>
        {description && (
          <p className="text-[12px] leading-relaxed" style={{ color: 'rgb(var(--text-muted))' }}>
            {description}
          </p>
        )}
      </div>
      {action && <div className="mt-2">{action}</div>}
    </motion.div>
  );
}

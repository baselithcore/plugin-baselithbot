import { AnimatePresence, motion } from 'framer-motion';
import { RotateCcw, Save } from 'lucide-react';
import type { RoleSummary } from '../../../lib/api/rbac';
import { Button } from '../../ui';
import { RoleBadge } from '../users/atoms';

interface Props {
  dirtyRoles: RoleSummary[];
  saving: boolean;
  onSaveAll: () => void;
  onDiscardAll: () => void;
}

export function FloatingSaveBar({ dirtyRoles, saving, onSaveAll, onDiscardAll }: Props) {
  return (
    <AnimatePresence>
      {dirtyRoles.length > 0 && (
        <motion.div
          key="bar"
          initial={{ y: 60, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 60, opacity: 0 }}
          transition={{ duration: 0.18, ease: 'easeOut' }}
          className="pointer-events-none sticky bottom-0 z-40 mt-2 flex justify-center px-5 pb-4"
        >
          <div
            role="status"
            className="pointer-events-auto flex w-full max-w-2xl items-center gap-3 rounded-xl border border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-3.5 py-2 shadow-lg"
          >
            <div className="min-w-0 flex-1">
              <p className="text-[12px] font-semibold text-ink">
                {dirtyRoles.length === 1
                  ? '1 ruolo con modifiche non salvate'
                  : `${dirtyRoles.length} ruoli con modifiche non salvate`}
              </p>
              <div className="mt-1 flex flex-wrap items-center gap-1">
                {dirtyRoles.map((r) => (
                  <RoleBadge key={r.id} slug={r.slug} />
                ))}
              </div>
            </div>
            <Button
              size="sm"
              variant="secondary"
              leadingIcon={RotateCcw}
              onClick={onDiscardAll}
              disabled={saving}
            >
              Annulla tutto
            </Button>
            <Button
              size="sm"
              variant="primary"
              leadingIcon={Save}
              onClick={onSaveAll}
              loading={saving}
            >
              Salva tutto
            </Button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

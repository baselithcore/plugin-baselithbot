import { motion, AnimatePresence } from 'motion/react';
import type { Recommendation, Scenario, Stint } from '../../types';
import type { SectionId } from '../../lib/sections';
import { StintPanel } from '../StintPanel';
import { SwarmField } from '../SwarmField';
import { RaceControlPanel } from '../RaceControlPanel';
import { StrategyPanel } from '../StrategyPanel';
import { IntelPanel } from '../IntelPanel';
import { GovernancePanel } from '../GovernancePanel';

interface Props {
  section: SectionId;
  car: string | null;
  stint: Stint | null;
  scenario: Scenario | null;
  simulate: () => void;
  busy: boolean;
  signals: Record<string, number>;
  recs: Recommendation[];
  session: string;
}

/** Swaps the main work area per active section, with a fade/slide transition.
 * The car stint card stays as left-column context across analytical views. */
export function MainArea(p: Props) {
  const stint = (
    <StintPanel stint={p.stint} scenario={p.scenario} onSimulate={p.simulate} busy={p.busy} />
  );

  let body: React.ReactNode;
  if (p.section === 'command') {
    body = (
      <div className="grid gap-4 xl:grid-cols-2">
        <div className="space-y-4">{stint}</div>
        <div className="space-y-4">
          <SwarmField signals={p.signals} />
          <RaceControlPanel />
        </div>
      </div>
    );
  } else if (p.section === 'strategy') {
    body = (
      <div className="grid gap-4 xl:grid-cols-2">
        <div className="space-y-4">{stint}</div>
        <StrategyPanel car={p.car} />
      </div>
    );
  } else if (p.section === 'intel') {
    body = (
      <div className="grid gap-4 xl:grid-cols-2">
        <div className="space-y-4">{stint}</div>
        <IntelPanel car={p.car} />
      </div>
    );
  } else {
    body = <GovernancePanel recs={p.recs} sessionId={p.session} />;
  }

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={p.section}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.18 }}
      >
        {body}
      </motion.div>
    </AnimatePresence>
  );
}

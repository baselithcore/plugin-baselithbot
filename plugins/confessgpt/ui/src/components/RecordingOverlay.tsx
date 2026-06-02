import { AnimatePresence, motion } from 'framer-motion';
import { Mic } from 'lucide-react';

interface RecordingOverlayProps {
  open: boolean;
  levels: number[];
  onStop: () => void;
}

// Full-screen mic capture overlay with breathing crimson orb and
// real-time waveform bars sourced from useVoiceRecording.
export function RecordingOverlay({ open, levels, onStop }: RecordingOverlayProps) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          role="dialog"
          aria-modal="true"
          aria-label="Registrazione audio in corso"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
          className="fixed inset-0 z-50 grid place-items-center bg-[rgba(10,7,18,0.85)] backdrop-blur-2xl"
          onClick={onStop}
        >
          <motion.button
            type="button"
            aria-label="Ferma la registrazione"
            onClick={(e) => {
              e.stopPropagation();
              onStop();
            }}
            initial={{ scale: 0.94 }}
            animate={{ scale: [1, 1.04, 1] }}
            transition={{
              duration: 2.4,
              repeat: Infinity,
              ease: [0.65, 0, 0.35, 1],
            }}
            className="relative grid h-56 w-56 place-items-center rounded-full bg-[radial-gradient(circle,#8b1a2a_0%,#1d1730_70%)] shadow-glow-crimson"
          >
            {/* Waveform bars rotated around the orb circumference */}
            <div className="pointer-events-none absolute inset-0 flex items-center justify-center gap-1">
              {levels.map((lvl, i) => (
                <span
                  key={i}
                  aria-hidden
                  className="w-[3px] rounded bg-parchment/70"
                  style={{ height: `${8 + lvl * 80}px` }}
                />
              ))}
            </div>
            <Mic className="relative h-16 w-16 text-parchment" strokeWidth={1.5} />
          </motion.button>

          <div className="pointer-events-none absolute bottom-[14%] text-center font-serif text-2xl italic text-parchment">
            Ascolto il tuo cuore…
          </div>
          <div className="pointer-events-none absolute bottom-[8%] text-[0.7rem] uppercase tracking-[0.24em] text-ash">
            Tocca o premi Spazio per concludere
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

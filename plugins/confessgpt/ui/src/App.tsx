import { useCallback, useEffect, useState } from 'react';
import { Composer } from './components/Composer';
import { Dialogue } from './components/Dialogue';
import { Header } from './components/Header';
import { PhaseRosary } from './components/PhaseRosary';
import { RecordingOverlay } from './components/RecordingOverlay';
import { StatusBar } from './components/StatusBar';
import { Toast } from './components/Toast';
import { Welcome } from './components/Welcome';
import { useConfession } from './hooks/useConfession';
import { useVoiceRecording } from './hooks/useVoiceRecording';

export default function App() {
  const {
    sessionId,
    currentPhase,
    closed,
    pending,
    dialogue,
    error,
    begin,
    sayText,
    sayVoice,
    dismissError,
  } = useConfession();

  const [recError, setRecError] = useState<string | null>(null);

  const handleVoiceComplete = useCallback(
    (b64: string) => {
      void sayVoice(b64);
    },
    [sayVoice]
  );

  const { recording, levels, start, stop, supported } = useVoiceRecording({
    onComplete: handleVoiceComplete,
    onError: setRecError,
  });

  const toggleMic = useCallback(() => {
    if (recording) stop();
    else void start();
  }, [recording, start, stop]);

  // Global Space-to-record while no input is focused — guarded so we
  // do not steal keystrokes from the textarea.
  useEffect(() => {
    if (!sessionId || closed) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.code !== 'Space') return;
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === 'TEXTAREA' || target.tagName === 'INPUT')) return;
      if (recording) {
        e.preventDefault();
        stop();
      } else if (!pending && supported) {
        e.preventDefault();
        void start();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [closed, pending, recording, sessionId, start, stop, supported]);

  const started = sessionId !== null || dialogue.length > 0;

  const statusLevel = closed ? 'warn' : sessionId ? 'ok' : pending ? 'warn' : 'idle';

  const statusMessage = closed
    ? 'Sessione sigillata · sigillum sacramentale onorato'
    : sessionId
      ? `Sessione ${sessionId.slice(0, 8)} · sigillum attivo`
      : pending
        ? 'Apertura della sessione…'
        : 'Sessione non aperta';

  return (
    <div className="mx-auto grid h-full max-w-[1240px] grid-rows-[auto_auto_1fr_auto_auto] gap-3 p-3 sm:gap-5 sm:p-5">
      <Header />
      <PhaseRosary current={currentPhase} />

      <main className="relative flex min-h-[420px] flex-col gap-4 overflow-hidden rounded-2xl border border-gold-subtle bg-gradient-to-b from-surface-1 via-transparent to-surface-1 px-3 py-6 sm:px-5">
        {!started ? (
          <Welcome onBegin={() => void begin()} pending={pending} />
        ) : (
          <Dialogue turns={dialogue} thinking={pending} />
        )}
      </main>

      {started && !closed && (
        <Composer
          pending={pending}
          recording={recording}
          onSubmitText={(t) => void sayText(t)}
          onToggleMic={toggleMic}
        />
      )}

      <StatusBar
        level={statusLevel}
        message={statusMessage}
        meta="Sigillum attivo · zero persistenza"
      />

      <RecordingOverlay open={recording} levels={levels} onStop={stop} />
      <Toast message={error} onDismiss={dismissError} level="err" />
      <Toast message={recError} onDismiss={() => setRecError(null)} level="err" />
    </div>
  );
}

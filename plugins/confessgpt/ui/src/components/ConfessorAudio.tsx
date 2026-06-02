import { Pause, Play } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { isValidBase64, sanitizeAudioMime } from '../lib/phases';

interface ConfessorAudioProps {
  audioBase64: string;
  audioMime: string | null;
}

// Inline TTS playback for a confessor turn. Auto-plays once on mount
// (browsers may block until a user gesture — in that case the user
// can still play manually). Base64 + mime are validated against an
// allowlist before constructing the data: URL to avoid XSS via the
// attribute boundary.
export function ConfessorAudio({ audioBase64, audioMime }: ConfessorAudioProps) {
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const dataUrl = useMemo(() => {
    if (!isValidBase64(audioBase64)) return null;
    const mime = sanitizeAudioMime(audioMime);
    return `data:${mime};base64,${audioBase64}`;
  }, [audioBase64, audioMime]);

  useEffect(() => {
    if (!dataUrl) return;
    const a = audioRef.current;
    if (!a) return;
    a.play().catch(() => {
      // Silently fall back to manual playback when autoplay is blocked.
    });
  }, [dataUrl]);

  if (!dataUrl) return null;

  return (
    <div className="mt-1 flex w-fit items-center gap-3 rounded-full border border-gold-subtle bg-surface-1 px-3 py-1.5 text-[0.7rem] uppercase tracking-[0.1em] text-ash">
      <button
        type="button"
        aria-label={playing ? 'Ferma la voce del sacerdote' : 'Ascolta la voce del sacerdote'}
        onClick={() => {
          const a = audioRef.current;
          if (!a) return;
          if (playing) {
            a.pause();
            a.currentTime = 0;
          } else {
            a.play().catch(() => undefined);
          }
        }}
        className="grid h-7 w-7 place-items-center rounded-full border border-gold-medium bg-surface-2 text-gold transition-colors hover:border-gold hover:bg-gold hover:text-void"
      >
        {playing ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
      </button>
      Voce del sacerdote
      <audio
        ref={audioRef}
        src={dataUrl}
        preload="auto"
        className="hidden"
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
      />
    </div>
  );
}

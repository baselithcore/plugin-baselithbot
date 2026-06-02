// Voice capture hook.
//
// Owns the MediaRecorder + WebAudio AnalyserNode lifecycle and surfaces
// a simple start/stop API plus a normalized FFT array for waveform
// rendering. The hook releases mic tracks aggressively on stop/unmount
// so the browser indicator goes dark even if the parent forgets.

import { useCallback, useEffect, useRef, useState } from 'react';

const BAR_COUNT = 16;

export interface UseVoiceRecordingOptions {
  onComplete: (audioBase64: string) => void;
  onError?: (message: string) => void;
}

export interface UseVoiceRecordingResult {
  recording: boolean;
  levels: number[];
  start: () => Promise<void>;
  stop: () => void;
  supported: boolean;
}

export function useVoiceRecording({
  onComplete,
  onError,
}: UseVoiceRecordingOptions): UseVoiceRecordingResult {
  const [recording, setRecording] = useState(false);
  const [levels, setLevels] = useState<number[]>(() => Array.from({ length: BAR_COUNT }, () => 0));

  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const rafRef = useRef<number | null>(null);

  const supported =
    typeof navigator !== 'undefined' &&
    !!navigator.mediaDevices &&
    typeof window !== 'undefined' &&
    typeof window.MediaRecorder !== 'undefined';

  const cleanup = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (sourceRef.current) {
      try {
        sourceRef.current.disconnect();
      } catch {
        // ignore
      }
      sourceRef.current = null;
    }
    if (audioCtxRef.current) {
      try {
        void audioCtxRef.current.close();
      } catch {
        // ignore
      }
      audioCtxRef.current = null;
    }
    analyserRef.current = null;
    recorderRef.current = null;
    chunksRef.current = [];
    setLevels(Array.from({ length: BAR_COUNT }, () => 0));
  }, []);

  const start = useCallback(async () => {
    if (!supported) {
      onError?.('Microfono non disponibile nel browser.');
      return;
    }
    if (recorderRef.current) return;

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      onError?.('Permesso microfono negato.');
      return;
    }

    streamRef.current = stream;
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : 'audio/webm';

    const rec = new MediaRecorder(stream, { mimeType });
    recorderRef.current = rec;
    chunksRef.current = [];
    rec.addEventListener('dataavailable', (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    });
    rec.addEventListener('stop', () => {
      const blob = new Blob(chunksRef.current, { type: rec.mimeType });
      cleanup();
      setRecording(false);
      if (blob.size === 0) return;
      blobToBase64(blob).then(
        (b64) => onComplete(b64),
        () => onError?.('Lettura audio fallita.')
      );
    });
    rec.start();

    // WebAudio analyser for the waveform visualization.
    const AudioCtxClass =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (AudioCtxClass) {
      const ctx = new AudioCtxClass();
      const src = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 64;
      src.connect(analyser);
      audioCtxRef.current = ctx;
      sourceRef.current = src;
      analyserRef.current = analyser;
      const data = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(data);
        const next: number[] = [];
        for (let i = 0; i < BAR_COUNT; i++) {
          next.push(data[i % data.length] / 255);
        }
        setLevels(next);
        rafRef.current = requestAnimationFrame(tick);
      };
      tick();
    }

    setRecording(true);
  }, [cleanup, onComplete, onError, supported]);

  const stop = useCallback(() => {
    const rec = recorderRef.current;
    if (!rec) return;
    try {
      rec.stop();
    } catch {
      // ignore — state machine handles cleanup
    }
  }, []);

  useEffect(() => {
    return () => {
      cleanup();
    };
  }, [cleanup]);

  return { recording, levels, start, stop, supported };
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onloadend = () => {
      const result = r.result;
      if (typeof result !== 'string') {
        resolve('');
        return;
      }
      const idx = result.indexOf(',');
      resolve(idx >= 0 ? result.slice(idx + 1) : result);
    };
    r.onerror = reject;
    r.readAsDataURL(blob);
  });
}

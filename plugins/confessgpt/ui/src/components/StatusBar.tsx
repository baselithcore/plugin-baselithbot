import clsx from 'clsx';

type Level = 'ok' | 'warn' | 'err' | 'idle';

interface StatusBarProps {
  level: Level;
  message: string;
  meta?: string;
}

export function StatusBar({ level, message, meta }: StatusBarProps) {
  return (
    <footer className="flex items-center justify-between gap-3 px-2 text-[0.62rem] font-medium uppercase tracking-[0.2em] text-ash sm:text-[0.65rem]">
      <div className="flex items-center gap-3">
        <span className="flex items-center gap-2">
          <span
            aria-hidden
            className={clsx(
              'inline-block h-1.5 w-1.5 rounded-full',
              level === 'ok' && 'bg-emerald shadow-[0_0_6px_#4a7d5a]',
              level === 'warn' && 'bg-gold shadow-[0_0_6px_#c9a86a]',
              level === 'err' && 'bg-crimson-glow shadow-[0_0_6px_#c44056]',
              level === 'idle' && 'bg-ash'
            )}
          />
          {message}
        </span>
      </div>
      {meta && <div className="hidden sm:block">{meta}</div>}
    </footer>
  );
}

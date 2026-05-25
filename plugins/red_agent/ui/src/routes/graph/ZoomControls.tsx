import { Icon } from '../../components/ui';

export function ZoomControls(props: {
  onIn: () => void;
  onOut: () => void;
  onFit: () => void;
  onCenter: () => void;
}) {
  return (
    <div
      className="absolute bottom-4 left-4 z-20 flex flex-col gap-1.5"
      role="toolbar"
      aria-label="zoom controls"
    >
      <Btn onClick={props.onIn} label="Zoom in" icon={<Icon.Plus size={14} />} />
      <Btn onClick={props.onOut} label="Zoom out" icon={<Icon.Minus size={14} />} />
      <Btn onClick={props.onFit} label="Fit graph" icon={<Icon.Maximize size={14} />} />
      <Btn onClick={props.onCenter} label="Center graph" icon={<Icon.Locate size={14} />} />
    </div>
  );
}

function Btn({
  onClick,
  label,
  icon,
}: {
  onClick: () => void;
  label: string;
  icon: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      className="grid h-8 w-8 place-items-center rounded-md border border-bg-line bg-bg-elevated/90 text-text-muted backdrop-blur transition hover:border-bg-line-strong hover:text-text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/40"
    >
      {icon}
    </button>
  );
}

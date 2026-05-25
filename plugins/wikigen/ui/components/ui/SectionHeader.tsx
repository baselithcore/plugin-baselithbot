import { type LucideIcon } from 'lucide-react';
import { cn } from '../../lib/cn';

interface SectionHeaderProps {
  /** Visible title. Rendered as <h3> for landmark semantics. */
  title: React.ReactNode;
  icon?: LucideIcon;
  /** Right-aligned slot — counts, controls, links. */
  trailing?: React.ReactNode;
  className?: string;
  /** Override the heading level. */
  as?: 'h2' | 'h3' | 'h4';
}

export function SectionHeader({
  title,
  icon: Icon,
  trailing,
  className,
  as: Tag = 'h3',
}: SectionHeaderProps) {
  return (
    <div className={cn('mb-2 flex items-center justify-between gap-2', className)}>
      <Tag className="section-label inline-flex items-center gap-1.5">
        {Icon && <Icon size={11} className="text-ink-subtle" aria-hidden />}
        {title}
      </Tag>
      {trailing && <div className="shrink-0">{trailing}</div>}
    </div>
  );
}

'use client';

import { forwardRef } from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/cn';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors duration-150 ease-smooth disabled:pointer-events-none disabled:opacity-50 ring-focus select-none',
  {
    variants: {
      variant: {
        primary: 'bg-status-info text-white hover:bg-status-info/90 active:bg-status-info/80',
        secondary:
          'border border-border bg-bg-panel text-text-primary hover:bg-bg-panel-elev hover:border-border-strong shadow-sm',
        ghost: 'text-text-secondary hover:bg-bg-panel-elev hover:text-text-primary',
        outline:
          'border border-border bg-transparent text-text-secondary hover:bg-bg-panel-elev hover:text-text-primary',
        danger: 'bg-status-danger text-white hover:bg-status-danger/90',
        success: 'bg-status-success text-white hover:bg-status-success/90',
        gradient: 'gradient-border bg-bg-panel text-text-primary hover:bg-bg-panel-elev',
      },
      size: {
        sm: 'h-8 px-3 text-xs',
        md: 'h-9 px-3.5',
        lg: 'h-10 px-4',
        xl: 'h-11 px-5 text-[15px]',
        icon: 'h-9 w-9 p-0',
        'icon-sm': 'h-8 w-8 p-0',
      },
    },
    defaultVariants: { variant: 'secondary', size: 'md' },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...props} />
    );
  }
);
Button.displayName = 'Button';

export { buttonVariants };

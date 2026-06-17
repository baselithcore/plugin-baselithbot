import { useEffect } from 'react';
import { motion, useMotionValue, useReducedMotion, useSpring, useTransform } from 'motion/react';

interface Props {
  value: number;
  className?: string;
}

// Counts up to `value` with a soft spring (mounts from 0, re-animates on change).
// Honors the OS "reduce motion" setting by rendering the final value statically.
export function AnimatedNumber({ value, className }: Props) {
  const reduce = useReducedMotion();
  const mv = useMotionValue(0);
  const spring = useSpring(mv, { stiffness: 140, damping: 24, mass: 0.6 });
  const text = useTransform(spring, (v) => Math.round(v).toLocaleString());

  useEffect(() => {
    mv.set(value);
  }, [mv, value]);

  if (reduce) return <span className={className}>{value.toLocaleString()}</span>;
  return <motion.span className={className}>{text}</motion.span>;
}

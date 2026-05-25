"use client";

import { AgentPipeline } from "./AgentPipeline";

interface Props {
  phase: string;
  progress: { current: number; total: number; label?: string } | null;
  done: boolean;
  error: string | null;
}

export function PhaseIndicator(props: Props) {
  return <AgentPipeline {...props} variant="compact" />;
}

import React from 'react';
import { Brain, Zap, FileText, Link2, Download } from 'lucide-react';

export const CATEGORY_ICONS: Record<
  string,
  { icon: React.ReactNode; label: string; color: string }
> = {
  prompt_injection: { icon: <Brain size={12} />, label: 'Injection', color: '#ff6b6b' },
  jailbreak: { icon: <Zap size={12} />, label: 'Jailbreak', color: '#ffd93d' },
  sql_injection: { icon: <FileText size={12} />, label: 'SQLi', color: '#6bcb77' },
  social_engineering: { icon: <Link2 size={12} />, label: 'Social Eng', color: '#4d96ff' },
  data_extraction: { icon: <Download size={12} />, label: 'Exfil', color: '#9b59b6' },
};

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@/i18n';
import { HealthBadge } from './HealthBadge';

describe('HealthBadge', () => {
  it('renders the localized state label', () => {
    render(<HealthBadge state="active" />);
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('exposes the tooltip detail via title', () => {
    render(<HealthBadge state="failed" title="latency 5ms" />);
    expect(screen.getByText('Failed')).toBeInTheDocument();
    expect(screen.getByTitle('latency 5ms')).toBeInTheDocument();
  });
});

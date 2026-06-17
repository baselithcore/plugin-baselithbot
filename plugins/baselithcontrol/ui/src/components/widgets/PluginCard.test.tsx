import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@/i18n';
import { PluginCard } from './PluginCard';
import type { PluginCard as Card } from '@/types';

const card: Card = {
  name: 'demo',
  version: '1.0.0',
  description: 'a demo plugin',
  category: 'demo',
  group: 'Ops',
  icon: '',
  instance: null,
  state: 'active',
  healthy: true,
  initialized: true,
  provides_routes: true,
  router_prefix: '/api/demo',
  surfaces: [],
  tags: [],
};

describe('PluginCard RBAC gating', () => {
  it('shows lifecycle controls when canControl is true', () => {
    render(<PluginCard card={card} onOpen={() => {}} canControl />);
    expect(screen.getByText('Reload')).toBeInTheDocument();
    expect(screen.getByText('Disable')).toBeInTheDocument();
  });

  it('hides lifecycle controls when canControl is false', () => {
    render(<PluginCard card={card} onOpen={() => {}} canControl={false} />);
    expect(screen.queryByText('Reload')).not.toBeInTheDocument();
    expect(screen.queryByText('Disable')).not.toBeInTheDocument();
  });
});

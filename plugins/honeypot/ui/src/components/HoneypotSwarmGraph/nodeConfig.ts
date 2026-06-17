import { Terminal, Globe, Radio, Link2, Bot, Hexagon, Shield, Search } from 'lucide-react';

export const SWARM_NODES = {
  SSH: {
    x: 0.5, // Top center
    y: 0.15,
    color: '#00ff88',
    label: 'SSH Handler',
    icon: Terminal,
    angle: -90,
  },
  HTTP: {
    x: 0.78, // Top right
    y: 0.27,
    color: '#00d4ff',
    label: 'HTTP Handler',
    icon: Globe,
    angle: -38,
  },
  DISCOVERY: {
    x: 0.85, // Right
    y: 0.58,
    color: '#ff6b9d',
    label: 'Discovery',
    icon: Search,
    angle: 13,
  },
  RESPONDER: {
    x: 0.65, // Bottom right
    y: 0.82,
    color: '#9d4edd',
    label: 'LLM Responder',
    icon: Bot,
    angle: 64,
  },
  TCP: {
    x: 0.35, // Bottom left
    y: 0.82,
    color: '#ff6b35',
    label: 'TCP Handler',
    icon: Radio,
    angle: 116,
  },
  PENTEST: {
    x: 0.15, // Left
    y: 0.58,
    color: '#00ff9d',
    label: 'Pentest',
    icon: Shield,
    angle: 167,
  },
  CORRELATOR: {
    x: 0.22, // Top left
    y: 0.27,
    color: '#ffbe0b',
    label: 'CVE Correlator',
    icon: Link2,
    angle: 218,
  },
  CORE: {
    x: 0.5,
    y: 0.5,
    color: '#ff073a',
    label: 'Coordinator',
    icon: Hexagon,
    angle: 0,
  },
};

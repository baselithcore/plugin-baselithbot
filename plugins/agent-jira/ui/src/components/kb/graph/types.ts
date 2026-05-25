export interface Node {
  id: string;
  label: string;
  group: string;
  is_center?: boolean;
  properties?: Record<string, any>;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  __threeObj?: any; // for react-force-graph
}

export interface Link {
  source: string | Node;
  target: string | Node;
  label: string;
  confidence?: number;
  provenance?: string;
  properties?: Record<string, any>;
}

export interface GraphData {
  nodes: Node[];
  links: Link[];
  legend?: Record<string, { color: string; label: string }>;
}

export interface GraphModalProps {
  isOpen: boolean;
  onClose: () => void;
  centerNodeId: string;
  title?: string;
}

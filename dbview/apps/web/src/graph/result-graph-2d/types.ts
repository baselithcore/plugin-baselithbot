export type LabelMode = 'off' | 'hubs' | 'all';

export interface NodeShape {
  _kind: 'node';
  _labels: string[];
  [k: string]: unknown;
}

export interface RelShape {
  _kind: 'relationship';
  _type: string;
  [k: string]: unknown;
}

export interface ResNode {
  id: string;
  label: string;
  group: string;
  color: string;
  val: number;
  degree: number;
  raw: NodeShape;
  x?: number;
  y?: number;
}

export interface ResLink {
  source: string | ResNode;
  target: string | ResNode;
  type: string;
  color: string;
}

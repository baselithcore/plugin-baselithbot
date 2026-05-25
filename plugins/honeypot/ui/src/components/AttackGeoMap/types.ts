/**
 * AttackGeoMap Type Definitions
 */

import { GraphNode, GraphEdge, HoneypotInfo, HoneypotAttacker } from '../types';
import { ThreatLevel } from '../geoUtils';

import { AttackEvent } from '../types';

/** Props for the main AttackGeoMap component */
export interface AttackGraphProps {
  activeProtocols?: string[];
  events: AttackEvent[];
  /** Aggregated attackers from backend - for persistent node visualization */
  attackers?: HoneypotAttacker[];
  /** Optional honeypot context for per-honeypot visualization */
  honeypotContext?: HoneypotInfo | null;
  /** Callback when a node's detail view is requested */
  onSelectNode?: (node: GraphNode) => void;
  /** When false, animation loop is paused to save CPU */
  isActive?: boolean;
}

/** Canvas render context passed to drawing functions */
export interface CanvasRenderContext {
  ctx: CanvasRenderingContext2D;
  width: number;
  height: number;
  centerX: number;
  centerY: number;
  time: number;
  /** Optional honeypot position in canvas coordinates (if not center) */
  honeypotPosition?: { x: number; y: number };
}

/** Props for node rendering */
export interface NodeRenderProps extends CanvasRenderContext {
  node: GraphNode;
  isHovered: boolean;
  isSelected: boolean;
  threatLevel: ThreatLevel;
}

/** Props for edge rendering */
export interface EdgeRenderProps extends CanvasRenderContext {
  edge: GraphEdge;
  sourceNode: GraphNode;
  targetNode: GraphNode;
}

/** Stats displayed in the header */
export interface GeoMapStats {
  total: number;
  countries: number;
  attackers: number;
}

/** Props for GeoMapHeader component */
export interface GeoMapHeaderProps {
  stats: GeoMapStats;
  isConnected: boolean;
  threatLevel: ThreatLevel;
  attackVelocity: number;
  onRedistribute?: () => void;
  /** Callback to capture screenshot */
  onCapture?: () => void;
  /** Whether a capture is in progress */
  isCapturing?: boolean;
  /** Whether the map is in fullscreen mode */
  isFullscreen?: boolean;
  /** Callback to toggle fullscreen mode */
  onToggleFullscreen?: () => void;
}

/** Props for GeoMapLegend component */
export interface GeoMapLegendProps {
  activeProtocols: string[];
}

/** Props for NodeTooltip component */
export interface NodeTooltipProps {
  node: GraphNode;
}

/** Props for NodeDetailModal component */
export interface NodeDetailModalProps {
  node: GraphNode;
  /** Node position in screen coordinates (relative to canvas) */
  nodePosition?: { x: number; y: number };
  /** Container dimensions for boundary checking */
  containerDimensions?: { width: number; height: number };
  onClose: () => void;
  /** Callback to view full details */
  onViewDetails?: (node: GraphNode) => void;
}

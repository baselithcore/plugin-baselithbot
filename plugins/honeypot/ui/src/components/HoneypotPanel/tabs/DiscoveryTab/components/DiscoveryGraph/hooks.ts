import { useState, useRef, useCallback, useEffect } from 'react';
import type { ForceGraphMethods } from 'react-force-graph-2d';
import type {
  DiscoveryResult,
  DiscoveryGraphNode,
  BotnetCluster,
  HubNode,
} from '../../../../../types';

interface GraphData {
  nodes: any[];
  links: any[];
}

export interface GraphControlsState {
  selectedNode: DiscoveryGraphNode | null;
  hoveredNode: DiscoveryGraphNode | null;
  isFullscreen: boolean;
  showDetailModal: boolean;
  isInitialized: boolean;
  setSelectedNode: (node: DiscoveryGraphNode | null) => void;
  setHoveredNode: (node: DiscoveryGraphNode | null) => void;
  setShowDetailModal: (v: boolean) => void;
  setIsInitialized: (v: boolean) => void;
  handleZoomIn: () => void;
  handleZoomOut: () => void;
  handleFitView: () => void;
  handleRecenter: () => void;
  handleFocusHubs: () => void;
  handleToggleFullscreen: () => void;
  handleExportPNG: () => void;
  handleExportSVG: () => void;
  handleNodeClick: (node: any) => void;
  handleBackgroundClick: () => void;
  handleCloseModal: () => void;
  handleNodeHover: (node: any) => void;
  detailItem: BotnetCluster | HubNode | DiscoveryGraphNode | null;
  detailCategory: 'botnet' | 'hub' | 'attacker' | null;
  displayedNode: DiscoveryGraphNode | null;
}

export function useGraphControls(
  fgRef: React.MutableRefObject<ForceGraphMethods | undefined>,
  containerRef: React.MutableRefObject<HTMLDivElement | null>,
  graphData: GraphData,
  dimensions: { width: number; height: number },
  result: DiscoveryResult
): GraphControlsState {
  const [selectedNode, setSelectedNode] = useState<DiscoveryGraphNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<DiscoveryGraphNode | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);

  const handleZoomIn = () => {
    const currentZoom = fgRef.current?.zoom() || 1;
    fgRef.current?.zoom(currentZoom * 1.5, 300);
  };

  const handleZoomOut = () => {
    const currentZoom = fgRef.current?.zoom() || 1;
    fgRef.current?.zoom(currentZoom / 1.5, 300);
  };

  const handleFitView = () => {
    fgRef.current?.zoomToFit(400, 80);
  };

  const handleRecenter = () => {
    fgRef.current?.centerAt(0, 0, 300);
    fgRef.current?.zoom(1, 300);
  };

  const handleFocusHubs = () => {
    // Focus only on CONFIRMED C&C nodes, not potential ones
    const confirmedCC = graphData.nodes.filter((n: any) => n.is_hub && n.is_confirmed_cc);
    if (confirmedCC.length > 0) {
      const hub = confirmedCC[0] as any;
      fgRef.current?.centerAt(hub.x, hub.y, 500);
      fgRef.current?.zoom(3, 500);
    }
  };

  // Toggle fullscreen mode
  const handleToggleFullscreen = useCallback(() => {
    setIsFullscreen((prev) => !prev);
  }, []);

  // Handle Escape key to exit fullscreen
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isFullscreen) {
        setIsFullscreen(false);
      }
    };

    if (isFullscreen) {
      document.addEventListener('keydown', handleKeyDown);
      // Prevent body scroll when fullscreen
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isFullscreen]);

  // Export to PNG
  const handleExportPNG = useCallback(() => {
    const canvas = containerRef.current?.querySelector('canvas');
    if (!canvas) return;

    const link = document.createElement('a');
    link.download = `network-topology-${new Date().toISOString().split('T')[0]}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  }, [containerRef]);

  // Export to SVG
  const handleExportSVG = useCallback(() => {
    if (!graphData.nodes.length) return;

    const width = dimensions.width || 800;
    const height = dimensions.height || 600;

    // Create SVG element
    let svgContent = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`;

    // Background
    svgContent += `<rect width="100%" height="100%" fill="#0a1628"/>`;

    // Draw links
    graphData.links.forEach((link: any) => {
      const source =
        typeof link.source === 'object'
          ? link.source
          : graphData.nodes.find((n: any) => n.id === link.source);
      const target =
        typeof link.target === 'object'
          ? link.target
          : graphData.nodes.find((n: any) => n.id === link.target);
      if (source?.x && source?.y && target?.x && target?.y) {
        const color = link.is_intra_cluster
          ? 'rgba(46, 213, 115, 0.4)'
          : 'rgba(255, 255, 255, 0.15)';
        svgContent += `<line x1="${source.x + width / 2}" y1="${source.y + height / 2}" x2="${target.x + width / 2}" y2="${target.y + height / 2}" stroke="${color}" stroke-width="1"/>`;
      }
    });

    // Draw nodes
    graphData.nodes.forEach((node: any) => {
      const x = (node.x || 0) + width / 2;
      const y = (node.y || 0) + height / 2;
      const size = node.size || 5;
      const color = node.is_hub
        ? node.is_confirmed_cc
          ? '#ff4757'
          : '#ffaa00'
        : node.community_id !== undefined
          ? [
              '#2ed573',
              '#1e90ff',
              '#a55eea',
              '#ffa502',
              '#00d2d3',
              '#ff6b81',
              '#7bed9f',
              '#70a1ff',
            ][node.community_id % 8]
          : '#2ed573';

      if (node.is_hub) {
        // Hexagon for hubs
        const points = [];
        for (let i = 0; i < 6; i++) {
          const angle = (Math.PI / 3) * i - Math.PI / 2;
          points.push(`${x + size * Math.cos(angle)},${y + size * Math.sin(angle)}`);
        }
        svgContent += `<polygon points="${points.join(' ')}" fill="${color}" stroke="white" stroke-width="2"/>`;
        svgContent += `<text x="${x}" y="${y}" fill="white" text-anchor="middle" dominant-baseline="middle" font-size="10" font-weight="bold">${node.is_confirmed_cc ? '⚡' : '?'}</text>`;
      } else {
        // Circle for regular nodes
        svgContent += `<circle cx="${x}" cy="${y}" r="${size}" fill="${color}" stroke="rgba(255,255,255,0.6)" stroke-width="1.5"/>`;
      }

      // Label
      svgContent += `<text x="${x}" y="${y + size + 12}" fill="white" text-anchor="middle" font-size="9" font-family="monospace">${node.id}</text>`;
    });

    svgContent += '</svg>';

    // Download
    const blob = new Blob([svgContent], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.download = `network-topology-${new Date().toISOString().split('T')[0]}.svg`;
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
  }, [graphData, dimensions]);

  const handleNodeClick = (node: any) => {
    setSelectedNode(node as DiscoveryGraphNode);
    // Don't auto-zoom aggressively on every click, just center gently
    fgRef.current?.centerAt(node.x as number, node.y as number, 500);
    fgRef.current?.zoom(3, 500);
  };

  const handleBackgroundClick = () => {
    setSelectedNode(null);
    setShowDetailModal(false);
  };

  const handleCloseModal = () => {
    setShowDetailModal(false);
  };

  // Handle node hover
  const handleNodeHover = useCallback(
    (node: any) => {
      setHoveredNode(node as DiscoveryGraphNode | null);
      if (containerRef.current) {
        containerRef.current.style.cursor = node ? 'pointer' : 'grab';
      }
    },
    [containerRef]
  );

  // Helper to find the actual data object for the modal
  const getDetailItem = (
    node: DiscoveryGraphNode
  ): {
    item: BotnetCluster | HubNode | DiscoveryGraphNode | null;
    category: 'botnet' | 'hub' | 'attacker' | null;
  } => {
    if (!node) return { item: null, category: null };

    if (node.is_hub) {
      const hub = result.hub_nodes.find((h) => h.ip === node.id);
      return { item: hub || null, category: 'hub' };
    } else if (node.cluster_id !== null) {
      const botnet = result.botnets.find((b) => b.cluster_id === String(node.cluster_id));
      return { item: botnet || null, category: 'botnet' };
    }
    return { item: node, category: 'attacker' };
  };

  const { item: detailItem, category: detailCategory } = selectedNode
    ? getDetailItem(selectedNode)
    : { item: null, category: null };

  const displayedNode = selectedNode || hoveredNode;

  return {
    selectedNode,
    hoveredNode,
    isFullscreen,
    showDetailModal,
    isInitialized,
    setSelectedNode,
    setHoveredNode,
    setShowDetailModal,
    setIsInitialized,
    handleZoomIn,
    handleZoomOut,
    handleFitView,
    handleRecenter,
    handleFocusHubs,
    handleToggleFullscreen,
    handleExportPNG,
    handleExportSVG,
    handleNodeClick,
    handleBackgroundClick,
    handleCloseModal,
    handleNodeHover,
    detailItem,
    detailCategory,
    displayedNode,
  };
}

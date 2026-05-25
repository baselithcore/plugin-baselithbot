import React, { useEffect, useState, useRef, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { X, Network, Maximize2, Minimize2, RefreshCw } from 'lucide-react';
import { GraphModalProps, Node, Link } from './graph/types';
import { useGraphData } from './graph/useGraphData';
import { GraphLegend } from './graph/GraphLegend';
import { GraphTooltip } from './graph/GraphTooltip';
import { DEFAULT_NODE_COLORS } from './graph/constants';

/**
 * Knowledge Graph Visualizer Modal.
 * Now modularized for better maintainability.
 */
export const GraphModal: React.FC<GraphModalProps & { documentPath?: string }> = ({
  isOpen,
  onClose,
  centerNodeId: propCenterNodeId,
  documentPath, // Compatibility with old prop name
  title,
}) => {
  const centerNodeId = propCenterNodeId || documentPath || '';
  const { data, loading, error, refresh } = useGraphData(centerNodeId, isOpen);

  const [activeFilters, setActiveFilters] = useState<Set<string>>(new Set());
  const [hoverNode, setHoverNode] = useState<Node | null>(null);
  const [highlightNodes, setHighlightNodes] = useState(new Set<string>());
  const [highlightLinks, setHighlightLinks] = useState(new Set<Link>());

  const fgRef = useRef<any>();

  // Reset and initialize filters when data arrives without useEffect
  const [prevNodes, setPrevNodes] = useState(data.nodes);
  if (data.nodes !== prevNodes) {
    setPrevNodes(data.nodes);
    if (data.nodes.length > 0) {
      const allGroups = new Set(data.nodes.map((n) => n.group));
      setActiveFilters(allGroups);
    }
  }

  // Handle ESC key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const toggleFilter = (group: string) => {
    const next = new Set(activeFilters);
    if (next.has(group)) next.delete(group);
    else next.add(group);
    setActiveFilters(next);
  };

  const filteredData = useMemo(() => {
    const nodes = data.nodes.filter((n) => activeFilters.has(n.group) || n.is_center);
    const nodeIds = new Set(nodes.map((n) => n.id));
    const links = data.links.filter((l) => {
      const sourceId = typeof l.source === 'string' ? l.source : l.source.id;
      const targetId = typeof l.target === 'string' ? l.target : l.target.id;
      return nodeIds.has(sourceId) && nodeIds.has(targetId);
    });
    return { nodes, links };
  }, [data, activeFilters]);

  const handleNodeHover = (node: any) => {
    setHoverNode(node || null);
    const newHighlightNodes = new Set<string>();
    const newHighlightLinks = new Set<Link>();

    if (node) {
      newHighlightNodes.add(node.id);
      data.links.forEach((link) => {
        const sId = typeof link.source === 'string' ? link.source : (link.source as any).id;
        const tId = typeof link.target === 'string' ? link.target : (link.target as any).id;
        if (sId === node.id || tId === node.id) {
          newHighlightLinks.add(link);
          newHighlightNodes.add(sId);
          newHighlightNodes.add(tId);
        }
      });
    }

    setHighlightNodes(newHighlightNodes);
    setHighlightLinks(newHighlightLinks);
  };

  if (!isOpen) return null;

  return (
    <div className="kb-modal-overlay" onClick={onClose}>
      <div className="kb-modal-container" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="kb-modal-header">
          <div className="kb-modal-header-info">
            <div className="kb-modal-icon">
              <Network size={22} />
            </div>
            <div>
              <h2 className="kb-modal-title">
                {title || 'Esplora Knowledge Graph'}
                {loading && <RefreshCw size={14} className="animate-spin" />}
              </h2>
              <p className="kb-modal-path-label">{centerNodeId}</p>
            </div>
          </div>
          <button onClick={onClose} className="kb-modal-close" title="Chiudi">
            <X size={24} />
          </button>
        </div>

        {/* Main Content */}
        <div className="kb-modal-body">
          {error && (
            <div className="kb-modal-error-overlay">
              <div className="kb-modal-error-card">
                <p className="kb-modal-error-title">Recupero Grafo Fallito</p>
                <p className="kb-modal-error-message">{error}</p>
                <button
                  className="btn-kb primary"
                  onClick={() => refresh()}
                  style={{ marginTop: '16px' }}
                >
                  Riprova
                </button>
              </div>
            </div>
          )}

          {loading && !data.nodes.length && (
            <div className="kb-modal-loading-overlay">
              <div className="dot-loader" />
              <span>Caricamento dati grafo...</span>
            </div>
          )}

          <ForceGraph2D
            ref={fgRef}
            graphData={filteredData}
            nodeLabel={() => ''} // Use custom tooltip
            nodeColor={(node: any) => {
              if (highlightNodes.size > 0 && !highlightNodes.has(node.id))
                return 'rgba(148, 163, 184, 0.2)';
              return (
                data.legend?.[node.group]?.color ||
                DEFAULT_NODE_COLORS[node.group] ||
                'var(--muted)'
              );
            }}
            nodeRelSize={7}
            nodeVal={(node: any) => (node.is_center ? 4 : 1)}
            linkColor={(link: any) =>
              highlightLinks.has(link) ? 'var(--accent)' : 'rgba(255, 255, 255, 0.1)'
            }
            linkWidth={(link: any) => (highlightLinks.has(link) ? 3 : 1.5)}
            linkDirectionalArrowLength={4}
            linkDirectionalArrowRelPos={1}
            onNodeHover={handleNodeHover}
            onNodeClick={(node: any) => {
              if (fgRef.current) {
                fgRef.current.centerAt(node.x, node.y, 1000);
                fgRef.current.zoom(2.5, 1000);
              }
            }}
          />

          <GraphLegend
            legendData={data.legend}
            activeFilters={activeFilters}
            toggleFilter={toggleFilter}
          />

          <GraphTooltip node={hoverNode} />
        </div>
      </div>
    </div>
  );
};

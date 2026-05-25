/**
 * Graph Export Utilities
 *
 * Provides functions to export cluster graphs to various formats (PNG, SVG).
 */

interface Node {
  id: string;
  type: 'hub' | 'bot' | 'cluster';
  label: string;
  x: number;
  y: number;
  size: number;
  cluster?: string;
  centrality?: number;
}

interface Edge {
  source: string;
  target: string;
  strength: number;
}

interface GraphData {
  nodes: Node[];
  edges: Edge[];
}

/**
 * Export canvas to PNG
 */
export async function exportToPNG(
  canvas: HTMLCanvasElement,
  filename: string = 'cluster-graph.png'
): Promise<void> {
  try {
    // Convert canvas to blob
    const blob = await new Promise<Blob | null>((resolve) => {
      canvas.toBlob(resolve, 'image/png', 1.0);
    });

    if (!blob) {
      throw new Error('Failed to create PNG blob');
    }

    // Download
    downloadBlob(blob, filename);
  } catch (error) {
    console.error('PNG export failed:', error);
    throw error;
  }
}

/**
 * Export graph to SVG format
 */
export function exportToSVG(
  graphData: GraphData,
  width: number,
  height: number,
  zoom: number,
  pan: { x: number; y: number },
  filename: string = 'cluster-graph.svg'
): void {
  try {
    const svg = generateSVG(graphData, width, height, zoom, pan);
    const blob = new Blob([svg], { type: 'image/svg+xml;charset=utf-8' });
    downloadBlob(blob, filename);
  } catch (error) {
    console.error('SVG export failed:', error);
    throw error;
  }
}

/**
 * Generate SVG string from graph data
 */
function generateSVG(
  graphData: GraphData,
  width: number,
  height: number,
  zoom: number,
  pan: { x: number; y: number }
): string {
  const centerX = width / 2;
  const centerY = height / 2;

  // Build SVG content
  let svgContent = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <defs>
    <style>
      .edge { stroke-linecap: round; }
      .node-label {
        font-family: ui-monospace, monospace;
        font-size: 11px;
        fill: #fff;
        text-anchor: middle;
        dominant-baseline: hanging;
      }
    </style>
  </defs>
  <rect width="${width}" height="${height}" fill="#0a0a0a"/>
  <g transform="translate(${centerX + pan.x}, ${centerY + pan.y}) scale(${zoom}) translate(-${centerX}, -${centerY})">
`;

  // Draw edges
  graphData.edges.forEach((edge) => {
    const source = graphData.nodes.find((n) => n.id === edge.source);
    const target = graphData.nodes.find((n) => n.id === edge.target);
    if (!source || !target) return;

    const alpha = edge.strength * 0.3;
    const strokeWidth = edge.strength * 2;

    svgContent += `    <line class="edge" x1="${source.x}" y1="${source.y}" x2="${target.x}" y2="${target.y}" stroke="rgba(0, 255, 255, ${alpha})" stroke-width="${strokeWidth}"/>
`;
  });

  // Draw nodes
  graphData.nodes.forEach((node) => {
    let fillColor = 'rgba(100, 100, 100, 0.8)';
    let strokeColor = 'rgba(255, 255, 255, 0.3)';

    if (node.type === 'hub') {
      fillColor = 'rgba(255, 71, 87, 0.9)';
      strokeColor = 'rgba(255, 71, 87, 1)';
    } else if (node.type === 'cluster') {
      fillColor = 'rgba(168, 85, 247, 0.8)';
      strokeColor = 'rgba(168, 85, 247, 1)';
    } else if (node.type === 'bot') {
      fillColor = 'rgba(0, 255, 255, 0.6)';
      strokeColor = 'rgba(0, 255, 255, 0.8)';
    }

    svgContent += `    <circle cx="${node.x}" cy="${node.y}" r="${node.size}" fill="${fillColor}" stroke="${strokeColor}" stroke-width="2"/>
`;

    // Add label for hubs and clusters
    if (node.type === 'hub' || node.type === 'cluster') {
      const label = node.label.length > 15 ? node.label.slice(0, 12) + '...' : node.label;
      svgContent += `    <text class="node-label" x="${node.x}" y="${node.y + node.size + 5}">${label}</text>
`;
    }
  });

  svgContent += `  </g>
</svg>`;

  return svgContent;
}

/**
 * Download blob as file
 */
function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.style.display = 'none';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Export graph to JSON (for data analysis)
 */
export function exportToJSON(graphData: GraphData, filename: string = 'cluster-graph.json'): void {
  try {
    const json = JSON.stringify(graphData, null, 2);
    const blob = new Blob([json], { type: 'application/json;charset=utf-8' });
    downloadBlob(blob, filename);
  } catch (error) {
    console.error('JSON export failed:', error);
    throw error;
  }
}

/**
 * Get timestamp for filename
 */
export function getTimestampedFilename(basename: string, extension: string): string {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
  return `${basename}-${timestamp}.${extension}`;
}

import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  RefreshCw,
  Target,
  Download,
  FileImage,
  Expand,
  Shrink,
} from 'lucide-react';

interface GraphControlsProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFitView: () => void;
  onRecenter: () => void;
  onFocusHubs: () => void;
  hasHubs: boolean;
  onExportPNG: () => void;
  onExportSVG: () => void;
  hasConfirmedCC: boolean;
  onToggleFullscreen: () => void;
  isFullscreen: boolean;
}

export function GraphControls({
  onZoomIn,
  onZoomOut,
  onFitView,
  onRecenter,
  onFocusHubs,
  hasHubs,
  onExportPNG,
  onExportSVG,
  hasConfirmedCC,
  onToggleFullscreen,
  isFullscreen,
}: GraphControlsProps) {
  return (
    <div className="graph-controls">
      <button className="graph-control-btn" onClick={onZoomIn} title="Zoom In">
        <ZoomIn size={16} />
      </button>
      <button className="graph-control-btn" onClick={onZoomOut} title="Zoom Out">
        <ZoomOut size={16} />
      </button>
      <div className="control-divider" />
      <button className="graph-control-btn" onClick={onFitView} title="Fit to View">
        <Maximize2 size={16} />
      </button>
      <button className="graph-control-btn" onClick={onRecenter} title="Reset View">
        <RefreshCw size={16} />
      </button>
      {hasHubs && (
        <>
          <div className="control-divider" />
          <button
            className={`graph-control-btn hub-focus ${!hasConfirmedCC ? 'disabled' : ''}`}
            onClick={onFocusHubs}
            title={hasConfirmedCC ? 'Focus on Confirmed C&C' : 'No confirmed C&C detected'}
            disabled={!hasConfirmedCC}
          >
            <Target size={16} />
          </button>
        </>
      )}
      <div className="control-divider" />
      <button
        className={`graph-control-btn fullscreen-btn ${isFullscreen ? 'active' : ''}`}
        onClick={onToggleFullscreen}
        title={isFullscreen ? 'Exit Fullscreen (Esc)' : 'Fullscreen'}
      >
        {isFullscreen ? <Shrink size={16} /> : <Expand size={16} />}
      </button>
      <div className="control-divider" />
      <button className="graph-control-btn" onClick={onExportPNG} title="Export PNG">
        <Download size={16} />
      </button>
      <button className="graph-control-btn" onClick={onExportSVG} title="Export SVG">
        <FileImage size={16} />
      </button>
    </div>
  );
}

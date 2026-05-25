declare module 'globe.gl' {
  import type { Scene, Camera, WebGLRenderer } from 'three';

  interface GlobeInstance {
    (element: HTMLElement): GlobeInstance;

    // Globe appearance
    globeImageUrl(url: string): GlobeInstance;
    bumpImageUrl(url: string): GlobeInstance;
    backgroundColor(color: string): GlobeInstance;
    atmosphereColor(color: string): GlobeInstance;
    atmosphereAltitude(alt: number): GlobeInstance;
    showGraticules(show: boolean): GlobeInstance;
    showAtmosphere(show: boolean): GlobeInstance;

    // Points layer
    pointsData(data: any[]): GlobeInstance;
    pointLat(accessor: string | ((d: any) => number)): GlobeInstance;
    pointLng(accessor: string | ((d: any) => number)): GlobeInstance;
    pointAltitude(accessor: string | number | ((d: any) => number)): GlobeInstance;
    pointRadius(accessor: string | number | ((d: any) => number)): GlobeInstance;
    pointColor(accessor: string | ((d: any) => string)): GlobeInstance;
    pointLabel(accessor: string | ((d: any) => string)): GlobeInstance;
    onPointClick(callback: (point: any, event: MouseEvent) => void): GlobeInstance;
    onPointHover(callback: (point: any | null) => void): GlobeInstance;

    // Arcs layer
    arcsData(data: any[]): GlobeInstance;
    arcStartLat(accessor: string | ((d: any) => number)): GlobeInstance;
    arcStartLng(accessor: string | ((d: any) => number)): GlobeInstance;
    arcEndLat(accessor: string | ((d: any) => number)): GlobeInstance;
    arcEndLng(accessor: string | ((d: any) => number)): GlobeInstance;
    arcColor(accessor: string | ((d: any) => any)): GlobeInstance;
    arcStroke(accessor: string | number | ((d: any) => number) | null): GlobeInstance;
    arcDashLength(length: number | ((d: any) => number)): GlobeInstance;
    arcDashGap(gap: number | ((d: any) => number)): GlobeInstance;
    arcDashAnimateTime(ms: number | ((d: any) => number)): GlobeInstance;
    arcAltitudeAutoScale(scale: number): GlobeInstance;
    arcLabel(accessor: string | ((d: any) => string)): GlobeInstance;
    onArcClick(callback: (arc: any, event: MouseEvent) => void): GlobeInstance;

    // Rings layer
    ringsData(data: any[]): GlobeInstance;
    ringLat(accessor: string | ((d: any) => number)): GlobeInstance;
    ringLng(accessor: string | ((d: any) => number)): GlobeInstance;
    ringMaxRadius(accessor: string | number | ((d: any) => number)): GlobeInstance;
    ringPropagationSpeed(accessor: string | number | ((d: any) => number)): GlobeInstance;
    ringRepeatPeriod(accessor: string | number | ((d: any) => number)): GlobeInstance;
    ringColor(accessor: string | ((d: any) => (t: number) => string)): GlobeInstance;

    // Labels layer
    labelsData(data: any[]): GlobeInstance;
    labelLat(accessor: string | ((d: any) => number)): GlobeInstance;
    labelLng(accessor: string | ((d: any) => number)): GlobeInstance;
    labelText(accessor: string | ((d: any) => string)): GlobeInstance;
    labelSize(accessor: string | number | ((d: any) => number)): GlobeInstance;
    labelColor(accessor: string | ((d: any) => string)): GlobeInstance;

    // Camera / controls
    pointOfView(
      pov: { lat?: number; lng?: number; altitude?: number },
      transitionMs?: number
    ): GlobeInstance;
    camera(): Camera;
    controls(): any;
    scene(): Scene;
    renderer(): WebGLRenderer;
    getGlobeRadius(): number;

    // Sizing
    width(w: number): GlobeInstance;
    width(): number;
    height(h: number): GlobeInstance;
    height(): number;

    // Animation
    pauseAnimation(): GlobeInstance;
    resumeAnimation(): GlobeInstance;

    // Utils
    getScreenCoords(lat: number, lng: number, altitude?: number): { x: number; y: number };

    // Internal
    _destructor?: () => void;
  }

  function Globe(): GlobeInstance;
  export default Globe;
}

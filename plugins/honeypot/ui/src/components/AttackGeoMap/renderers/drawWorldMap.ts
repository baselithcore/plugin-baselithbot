/**
 * Draw world map specific for the Globe tab
 * Uses D3 and TopoJSON for high-quality, accurate rendering
 */

import * as d3 from 'd3';
import * as topojson from 'topojson-client';
import { CanvasRenderContext } from '../types';
import { CANVAS_COLORS } from '../constants';
import landData from '../data/land-110m.json';

// Reuse the same feature extraction logic or just do it here.
// Ideally should be consistent with the hook.
const landFeature = topojson.feature(landData as any, (landData as any).objects.land) as any;

// Filter Antarctica logic (simplified/copied)
let geometryToFilter: any = null;
if (landFeature.type === 'FeatureCollection' && landFeature.features.length > 0) {
  geometryToFilter = landFeature.features[0].geometry;
} else {
  geometryToFilter = landFeature.type === 'Feature' ? landFeature.geometry : landFeature;
}
if (geometryToFilter?.type === 'MultiPolygon') {
  geometryToFilter.coordinates = geometryToFilter.coordinates.filter(
    (p: any[]) => p[0][0][1] > -60
  );
}

export interface DrawWorldMapParams extends CanvasRenderContext {
  projection: d3.GeoProjection;
}

export function drawWorldMap({ ctx, projection }: DrawWorldMapParams): void {
  ctx.save();

  const pathGenerator = d3.geoPath(projection).context(ctx);

  ctx.beginPath();
  pathGenerator(landFeature);

  ctx.strokeStyle = CANVAS_COLORS.MAP_STROKE || '#1F2937';
  ctx.lineWidth = 1;
  ctx.stroke();

  ctx.fillStyle = CANVAS_COLORS.MAP_FILL || '#111827';
  ctx.fill();

  pathGenerator.context(null);

  ctx.restore();
}

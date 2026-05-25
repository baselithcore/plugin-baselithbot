import { useMemo } from 'react';
import * as d3 from 'd3';
import * as topojson from 'topojson-client';
import landData from '../AttackGeoMap/data/land-110m.json';

// Prepare feature once
const landFeature = topojson.feature(landData as any, (landData as any).objects.land) as any;

let geometryToFilter: any = null;
if (landFeature.type === 'FeatureCollection' && landFeature.features.length > 0) {
  geometryToFilter = landFeature.features[0].geometry;
} else if (landFeature.type === 'Feature') {
  geometryToFilter = landFeature.geometry;
} else {
  geometryToFilter = landFeature;
}

if (geometryToFilter && geometryToFilter.type === 'MultiPolygon') {
  geometryToFilter.coordinates = geometryToFilter.coordinates.filter((polygon: any[]) => {
    const outerRing = polygon[0];
    const firstPoint = outerRing[0];
    const lat = firstPoint[1];
    return lat > -60;
  });
}

export const useWorldMapProjection = (width: number, height: number) => {
  const projection = useMemo(() => {
    if (width === 0 || height === 0) return d3.geoMercator();

    const proj = d3.geoMercator();

    // Calculate scale to fit the map in the container
    // Slightly smaller scale (larger divisors) = more world visible
    // Original: 5.5, 2.6 - Now: 7.0, 3.5 (~30% more coverage)
    const scale = Math.min(width / 7.0, height / 3.5);

    // Center on 0° longitude (Greenwich) with lower latitude to show more southern hemisphere
    // 20°N shows good balance between north (Europe) and south (S. America, Africa, Australia)
    const MAP_CENTER: [number, number] = [0, 20];

    // Reduced vertical offset to show more northern countries
    const VISUAL_OFFSET_Y = 60;

    proj
      .scale(scale)
      .center(MAP_CENTER)
      .translate([width / 2, height / 2 - VISUAL_OFFSET_Y]);

    return proj;
  }, [width, height]);

  return { projection, landFeature };
};

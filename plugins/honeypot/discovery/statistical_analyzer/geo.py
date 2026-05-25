"""Geolocation Clustering Analysis."""

import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Set, Tuple

from ...models import AttackEvent
from ..models import NetworkAnomaly
from .utils import calculate_severity


def detect_geo_clustering(
    events: List[AttackEvent], geo_cluster_threshold: int
) -> List[NetworkAnomaly]:
    """Detect anomalous geographic clustering patterns.

    Multiple levels of analysis:
    - Country-level: unusual concentration from single country
    - City-level: suspicious clustering in same city (proxy farms)
    - Coordinate proximity: IPs with very close lat/lon (data center)
    """
    anomalies: List[NetworkAnomaly] = []

    # Collect geo data per IP (take first occurrence)
    ip_geo: Dict[str, Dict[str, Any]] = {}

    for event in events:
        if event.source_ip not in ip_geo and event.geo:
            ip_geo[event.source_ip] = {
                "country_code": event.geo.country_code,
                "country": event.geo.country,
                "city": event.geo.city,
                "lat": event.geo.latitude,
                "lon": event.geo.longitude,
            }

    if len(ip_geo) < 2:
        return anomalies

    # 1. Country-level clustering
    country_clusters = _detect_country_clustering(ip_geo, geo_cluster_threshold)
    anomalies.extend(country_clusters)

    # 2. City-level clustering
    city_clusters = _detect_city_clustering(ip_geo, geo_cluster_threshold)
    anomalies.extend(city_clusters)

    # 3. Coordinate proximity clustering
    coord_clusters = _detect_coordinate_clustering(ip_geo, geo_cluster_threshold)
    anomalies.extend(coord_clusters)

    return anomalies


def _detect_country_clustering(
    ip_geo: Dict[str, Dict[str, Any]], threshold: int
) -> List[NetworkAnomaly]:
    """Detect unusual concentration from single country."""
    anomalies = []

    # Group by country
    country_ips: Dict[str, Set[str]] = defaultdict(set)
    for ip, geo in ip_geo.items():
        country = geo.get("country_code") or "unknown"
        country_ips[country].add(ip)

    total_ips = len(ip_geo)

    for country, ips in country_ips.items():
        if country == "unknown":
            continue

        count = len(ips)
        concentration = count / total_ips if total_ips > 0 else 0

        # Anomalous if:
        # - High concentration (>40%) from single country with enough IPs
        # - Or absolute count threshold
        if (concentration >= 0.4 and count >= threshold) or count >= 10:
            anomaly = NetworkAnomaly(
                anomaly_id=str(uuid.uuid4())[:8],
                anomaly_type="geo_country_cluster",
                involved_ips=list(ips),
                description=(
                    f"{count} IPs ({concentration:.0%}) from {country} - "
                    f"geographic concentration anomaly"
                ),
                severity=calculate_severity(count, 5, 10, 20),
                confidence=min(0.9, concentration + 0.3),
                detected_at=datetime.now(),
                metadata={
                    "country_code": country,
                    "ip_count": count,
                    "concentration": round(concentration, 2),
                },
            )
            anomalies.append(anomaly)

    return anomalies


def _detect_city_clustering(
    ip_geo: Dict[str, Dict[str, Any]], threshold: int
) -> List[NetworkAnomaly]:
    """Detect suspicious clustering in same city (proxy farms)."""
    anomalies = []

    # Group by city + country
    city_ips: Dict[str, Set[str]] = defaultdict(set)
    for ip, geo in ip_geo.items():
        city = geo.get("city")
        country = geo.get("country_code")
        if city and country:
            key = f"{city}, {country}"
            city_ips[key].add(ip)

    for city_key, ips in city_ips.items():
        if len(ips) >= threshold:
            anomaly = NetworkAnomaly(
                anomaly_id=str(uuid.uuid4())[:8],
                anomaly_type="geo_city_cluster",
                involved_ips=list(ips),
                description=f"{len(ips)} IPs from {city_key} - possible proxy farm",
                severity="medium" if len(ips) >= 5 else "low",
                confidence=min(1.0, len(ips) / 8),
                detected_at=datetime.now(),
                metadata={
                    "city": city_key,
                    "ip_count": len(ips),
                },
            )
            anomalies.append(anomaly)

    return anomalies


def _detect_coordinate_clustering(
    ip_geo: Dict[str, Dict[str, Any]],
    threshold: int,
    distance_threshold_km: float = 5.0,
) -> List[NetworkAnomaly]:
    """Detect IPs with very close coordinates (same data center)."""
    anomalies = []

    # Get IPs with valid coordinates
    ip_coords: List[Tuple[str, float, float]] = []
    for ip, geo in ip_geo.items():
        lat = geo.get("lat")
        lon = geo.get("lon")
        if lat is not None and lon is not None:
            ip_coords.append((ip, lat, lon))

    if len(ip_coords) < 2:
        return anomalies

    # Simple clustering by grid
    # ~5km at equator ≈ 0.045 degrees
    grid_size = distance_threshold_km / 111.0  # km to degrees approx

    grid_clusters: Dict[Tuple[int, int], Set[str]] = defaultdict(set)

    for ip, lat, lon in ip_coords:
        grid_key = (int(lat / grid_size), int(lon / grid_size))
        grid_clusters[grid_key].add(ip)

    for grid_key, ips in grid_clusters.items():
        if len(ips) >= threshold:
            # Get approximate center
            avg_lat = sum(ip_geo[ip]["lat"] for ip in ips) / len(ips)
            avg_lon = sum(ip_geo[ip]["lon"] for ip in ips) / len(ips)

            anomaly = NetworkAnomaly(
                anomaly_id=str(uuid.uuid4())[:8],
                anomaly_type="geo_coord_cluster",
                involved_ips=list(ips),
                description=(
                    f"{len(ips)} IPs within ~{distance_threshold_km}km - "
                    f"possible data center or VPN exit"
                ),
                severity="high" if len(ips) >= 5 else "medium",
                confidence=min(1.0, len(ips) / 5),
                detected_at=datetime.now(),
                metadata={
                    "center_lat": round(avg_lat, 4),
                    "center_lon": round(avg_lon, 4),
                    "radius_km": distance_threshold_km,
                    "ip_count": len(ips),
                },
            )
            anomalies.append(anomaly)

    return anomalies

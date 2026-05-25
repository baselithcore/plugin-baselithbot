from core.observability.logging import get_logger

from ...models import AttackEvent, GeoLocation
from ...utils import is_private_or_local

logger = get_logger(__name__)


async def enrich_event_with_geo(event: AttackEvent) -> None:
    """Enrich attack event with geographic location data.

    Performs async geo lookup for the source IP and populates
    the event.geo field. Handles private/local IPs gracefully.

    Args:
        event: Attack event to enrich
    """
    from ...geo import get_geo_service

    # Skip if already has geo data
    if event.geo is not None:
        return

    # Handle private/local IPs
    if is_private_or_local(event.source_ip):
        event.geo = GeoLocation(
            country="Local Network",
            country_code="LAN",
            city="LAN",
            latitude=None,
            longitude=None,
        )
        return

    # Perform geo lookup
    try:
        geo_service = get_geo_service()
        geo_data = await geo_service.lookup(event.source_ip)
        if geo_data:
            event.geo = geo_data
        else:
            # Mark as unknown if lookup returns None
            event.geo = GeoLocation(
                country="Unknown",
                country_code="UNK",
                city=None,
                latitude=None,
                longitude=None,
            )
    except Exception as e:
        logger.debug(f"Geo lookup failed for {event.source_ip}: {e}")
        # Set unknown geo to prevent repeated lookup attempts
        event.geo = GeoLocation(
            country="Unknown",
            country_code="UNK",
            city=None,
            latitude=None,
            longitude=None,
        )

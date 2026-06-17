"""Dry↔wet compound crossover logic.

When the track wets (or dries), there is a *crossover* point at which a wet or
intermediate tyre becomes faster than a slick (or vice-versa). Getting this lap
right wins races; getting it wrong loses them. This module maps a
:class:`~.models.WeatherState` onto the correct compound and flags an urgent
crossover when the current tyre no longer matches conditions.
"""

from __future__ import annotations

from .models import TyreCompound, WeatherState

# Wetness thresholds at which each compound becomes the fastest legal choice.
_WET_THRESHOLD = 0.6  # full wet tyre territory
_INTER_THRESHOLD = 0.3  # intermediate territory


class WeatherModel:
    """Recommends the compound matching conditions and detects crossovers."""

    @staticmethod
    def ideal_compound(weather: WeatherState) -> TyreCompound:
        """The fastest legal compound for the current surface state."""
        if weather.track_wetness >= _WET_THRESHOLD or weather.rain_intensity >= 0.6:
            return TyreCompound.WET
        if weather.track_wetness >= _INTER_THRESHOLD or weather.rain_intensity >= 0.25:
            return TyreCompound.INTERMEDIATE
        return TyreCompound.MEDIUM  # representative slick

    @classmethod
    def crossover_needed(cls, current: TyreCompound, weather: WeatherState) -> bool:
        """True when the fitted tyre family no longer matches the surface.

        Crossing a slick onto a wet surface (or a wet onto a drying line) is a
        safety/performance imperative that overrides ordinary deg strategy.
        """
        ideal = cls.ideal_compound(weather)
        dry_family = {TyreCompound.SOFT, TyreCompound.MEDIUM, TyreCompound.HARD}
        on_slick = current in dry_family
        want_slick = ideal in dry_family
        return on_slick != want_slick

    @classmethod
    def urgency(cls, current: TyreCompound, weather: WeatherState) -> float:
        """0..1 urgency of a crossover (drives recommendation confidence)."""
        if not cls.crossover_needed(current, weather):
            return 0.0
        dry_family = {TyreCompound.SOFT, TyreCompound.MEDIUM, TyreCompound.HARD}
        if current in dry_family:
            # On slicks while it rains — escalates with wetness.
            return min(1.0, 0.5 + weather.track_wetness)
        # On wets while the line dries — escalates as wetness falls.
        return min(1.0, 0.5 + (1.0 - weather.track_wetness))


__all__ = ["WeatherModel"]

"""
Distance measurement utilities for GIS.
"""

from typing import Union
from dataclasses import dataclass
import math


@dataclass
class Distance:
    """
    Distance measurement with unit support.

    Example:
        from faststack.contrib.gis import D

        # Create distance in different units
        d1 = D(km=5)
        d2 = D(mi=3)
        d3 = D(m=1000)

        # Convert between units
        d1.in_miles()  # ~3.1 miles
        d2.in_km()     # ~4.8 km
    """

    # Distance in meters (internal representation)
    _meters: float = 0.0

    # Conversion factors to meters
    UNITS = {
        'm': 1.0,
        'meter': 1.0,
        'meters': 1.0,
        'metre': 1.0,
        'metres': 1.0,
        'km': 1000.0,
        'kilometer': 1000.0,
        'kilometers': 1000.0,
        'kilometre': 1000.0,
        'kilometres': 1000.0,
        'mi': 1609.344,
        'mile': 1609.344,
        'miles': 1609.344,
        'ft': 0.3048,
        'foot': 0.3048,
        'feet': 0.3048,
        'yd': 0.9144,
        'yard': 0.9144,
        'yards': 0.9144,
        'in': 0.0254,
        'inch': 0.0254,
        'inches': 0.0254,
        'nm': 1852.0,
        'nautical_mile': 1852.0,
        'nautical_miles': 1852.0,
    }

    def __init__(self, **kwargs):
        """Initialize distance with any unit."""
        if not kwargs:
            self._meters = 0.0
            return

        if len(kwargs) > 1:
            raise ValueError("Only one unit can be specified")

        unit, value = next(iter(kwargs.items()))
        unit = unit.lower()

        if unit not in self.UNITS:
            raise ValueError(f"Unknown unit: {unit}. Valid units: {list(self.UNITS.keys())}")

        self._meters = float(value) * self.UNITS[unit]

    def __repr__(self) -> str:
        return f"D(m={self._meters:.2f})"

    def __float__(self) -> float:
        return self._meters

    def __int__(self) -> int:
        return int(self._meters)

    def __add__(self, other: Union['Distance', float, int]) -> 'Distance':
        if isinstance(other, Distance):
            return Distance(m=self._meters + other._meters)
        return Distance(m=self._meters + other)

    def __radd__(self, other: float) -> 'Distance':
        return self.__add__(other)

    def __sub__(self, other: Union['Distance', float, int]) -> 'Distance':
        if isinstance(other, Distance):
            return Distance(m=self._meters - other._meters)
        return Distance(m=self._meters - other)

    def __rsub__(self, other: float) -> 'Distance':
        if isinstance(other, Distance):
            return Distance(m=other._meters - self._meters)
        return Distance(m=other - self._meters)

    def __mul__(self, other: float) -> 'Distance':
        return Distance(m=self._meters * other)

    def __rmul__(self, other: float) -> 'Distance':
        return self.__mul__(other)

    def __truediv__(self, other: float) -> 'Distance':
        return Distance(m=self._meters / other)

    def __floordiv__(self, other: float) -> 'Distance':
        return Distance(m=self._meters // other)

    def __lt__(self, other: Union['Distance', float]) -> bool:
        if isinstance(other, Distance):
            return self._meters < other._meters
        return self._meters < other

    def __le__(self, other: Union['Distance', float]) -> bool:
        if isinstance(other, Distance):
            return self._meters <= other._meters
        return self._meters <= other

    def __gt__(self, other: Union['Distance', float]) -> bool:
        if isinstance(other, Distance):
            return self._meters > other._meters
        return self._meters > other

    def __ge__(self, other: Union['Distance', float]) -> bool:
        if isinstance(other, Distance):
            return self._meters >= other._meters
        return self._meters >= other

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Distance):
            return self._meters == other._meters
        if isinstance(other, (int, float)):
            return self._meters == other
        return False

    def __bool__(self) -> bool:
        return self._meters != 0

    # Unit conversions

    @property
    def m(self) -> float:
        """Get distance in meters."""
        return self._meters

    @property
    def km(self) -> float:
        """Get distance in kilometers."""
        return self._meters / 1000.0

    @property
    def mi(self) -> float:
        """Get distance in miles."""
        return self._meters / 1609.344

    @property
    def ft(self) -> float:
        """Get distance in feet."""
        return self._meters / 0.3048

    @property
    def yd(self) -> float:
        """Get distance in yards."""
        return self._meters / 0.9144

    @property
    def inch(self) -> float:
        """Get distance in inches."""
        return self._meters / 0.0254

    @property
    def nm(self) -> float:
        """Get distance in nautical miles."""
        return self._meters / 1852.0

    # Conversion methods

    def in_meters(self) -> float:
        return self._meters

    def in_km(self) -> float:
        return self.km

    def in_miles(self) -> float:
        return self.mi

    def in_feet(self) -> float:
        return self.ft

    def in_yards(self) -> float:
        return self.yd

    def in_inches(self) -> float:
        return self.inch

    def in_nautical_miles(self) -> float:
        return self.nm

    # Creation class methods

    @classmethod
    def from_meters(cls, meters: float) -> 'Distance':
        return cls(m=meters)

    @classmethod
    def from_km(cls, km: float) -> 'Distance':
        return cls(km=km)

    @classmethod
    def from_miles(cls, miles: float) -> 'Distance':
        return cls(mi=miles)

    @classmethod
    def from_feet(cls, feet: float) -> 'Distance':
        return cls(ft=feet)

    @classmethod
    def from_yards(cls, yards: float) -> 'Distance':
        return cls(yd=yards)

    @classmethod
    def from_inches(cls, inches: float) -> 'Distance':
        return cls(in=inches)

    @classmethod
    def from_nautical_miles(cls, nm: float) -> 'Distance':
        return cls(nm=nm)


# Alias for convenience
D = Distance


def approximate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> Distance:
    """
    Calculate approximate distance between two points using Haversine formula.

    Args:
        lat1, lon1: First point (degrees)
        lat2, lon2: Second point (degrees)

    Returns:
        Distance object
    """
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    # Haversine formula
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # Earth's radius in meters
    R = 6371000

    return Distance(m=R * c)


def degrees_to_meters(degrees: float, latitude: float) -> float:
    """
    Convert degrees to meters at given latitude.

    Args:
        degrees: Degrees to convert
        latitude: Latitude for conversion

    Returns:
        Meters
    """
    # Earth's radius at equator
    R = 6378137

    # Meters per degree at latitude
    m_per_deg = R * math.cos(math.radians(latitude)) * math.pi / 180

    return degrees * m_per_deg


def meters_to_degrees(meters: float, latitude: float) -> float:
    """
    Convert meters to degrees at given latitude.

    Args:
        meters: Meters to convert
        latitude: Latitude for conversion

    Returns:
        Degrees
    """
    return meters / degrees_to_meters(1, latitude)

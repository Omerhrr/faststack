"""
GIS Spatial Functions for PostGIS queries.
"""

from typing import Any, Optional, Tuple, Union
from abc import ABC, abstractmethod
from .fields import Point, LineString, Polygon


class SpatialFunction(ABC):
    """Base class for spatial functions."""

    name: str = ''

    @abstractmethod
    def to_sql(self, field: str) -> str:
        """Generate SQL for this function."""
        pass


class Distance(SpatialFunction):
    """
    Calculate distance between geometries.

    Example:
        # Find stores within 5km
        stores = await Store.filter(
            location__distance_lte=(point, D(km=5))
        )
    """

    name = 'ST_Distance'

    def __init__(self, geom1: Any, geom2: Any, spheroid: bool = True):
        self.geom1 = geom1
        self.geom2 = geom2
        self.spheroid = spheroid

    def to_sql(self, field: str) -> str:
        if self.spheroid:
            return f"ST_DistanceSphere({field}, {self._geom_to_sql(self.geom2)})"
        return f"ST_Distance({field}, {self._geom_to_sql(self.geom2)})"

    def _geom_to_sql(self, geom: Any) -> str:
        if hasattr(geom, 'to_wkt'):
            return f"ST_GeomFromText('{geom.to_wkt()}')"
        return str(geom)


class Within(SpatialFunction):
    """
    Check if geometry is within another geometry.

    Example:
        stores = await Store.filter(location__within=city_boundary)
    """

    name = 'ST_Within'

    def __init__(self, geom: Any):
        self.geom = geom

    def to_sql(self, field: str) -> str:
        return f"ST_Within({field}, {self._geom_to_sql(self.geom)})"

    def _geom_to_sql(self, geom: Any) -> str:
        if hasattr(geom, 'to_wkt'):
            return f"ST_GeomFromText('{geom.to_wkt()}')"
        return str(geom)


class Contains(SpatialFunction):
    """
    Check if geometry contains another geometry.

    Example:
        regions = await Region.filter(boundary__contains=point)
    """

    name = 'ST_Contains'

    def __init__(self, geom: Any):
        self.geom = geom

    def to_sql(self, field: str) -> str:
        return f"ST_Contains({field}, {self._geom_to_sql(self.geom)})"

    def _geom_to_sql(self, geom: Any) -> str:
        if hasattr(geom, 'to_wkt'):
            return f"ST_GeomFromText('{geom.to_wkt()}')"
        return str(geom)


class Intersects(SpatialFunction):
    """Check if geometries intersect."""

    name = 'ST_Intersects'

    def __init__(self, geom: Any):
        self.geom = geom

    def to_sql(self, field: str) -> str:
        return f"ST_Intersects({field}, {self._geom_to_sql(self.geom)})"

    def _geom_to_sql(self, geom: Any) -> str:
        if hasattr(geom, 'to_wkt'):
            return f"ST_GeomFromText('{geom.to_wkt()}')"
        return str(geom)


class Touches(SpatialFunction):
    """Check if geometries touch."""

    name = 'ST_Touches'

    def __init__(self, geom: Any):
        self.geom = geom

    def to_sql(self, field: str) -> str:
        return f"ST_Touches({field}, {self._geom_to_sql(self.geom)})"

    def _geom_to_sql(self, geom: Any) -> str:
        if hasattr(geom, 'to_wkt'):
            return f"ST_GeomFromText('{geom.to_wkt()}')"
        return str(geom)


class Crosses(SpatialFunction):
    """Check if geometries cross."""

    name = 'ST_Crosses'

    def __init__(self, geom: Any):
        self.geom = geom

    def to_sql(self, field: str) -> str:
        return f"ST_Crosses({field}, {self._geom_to_sql(self.geom)})"

    def _geom_to_sql(self, geom: Any) -> str:
        if hasattr(geom, 'to_wkt'):
            return f"ST_GeomFromText('{geom.to_wkt()}')"
        return str(geom)


class Overlaps(SpatialFunction):
    """Check if geometries overlap."""

    name = 'ST_Overlaps'

    def __init__(self, geom: Any):
        self.geom = geom

    def to_sql(self, field: str) -> str:
        return f"ST_Overlaps({field}, {self._geom_to_sql(self.geom)})"

    def _geom_to_sql(self, geom: Any) -> str:
        if hasattr(geom, 'to_wkt'):
            return f"ST_GeomFromText('{geom.to_wkt()}')"
        return str(geom)


class Equals(SpatialFunction):
    """Check if geometries are equal."""

    name = 'ST_Equals'

    def __init__(self, geom: Any):
        self.geom = geom

    def to_sql(self, field: str) -> str:
        return f"ST_Equals({field}, {self._geom_to_sql(self.geom)})"

    def _geom_to_sql(self, geom: Any) -> str:
        if hasattr(geom, 'to_wkt'):
            return f"ST_GeomFromText('{geom.to_wkt()}')"
        return str(geom)


class Disjoint(SpatialFunction):
    """Check if geometries are disjoint."""

    name = 'ST_Disjoint'

    def __init__(self, geom: Any):
        self.geom = geom

    def to_sql(self, field: str) -> str:
        return f"ST_Disjoint({field}, {self._geom_to_sql(self.geom)})"

    def _geom_to_sql(self, geom: Any) -> str:
        if hasattr(geom, 'to_wkt'):
            return f"ST_GeomFromText('{geom.to_wkt()}')"
        return str(geom)


class Relate(SpatialFunction):
    """Check spatial relationship using DE-9IM pattern."""

    name = 'ST_Relate'

    def __init__(self, geom: Any, pattern: str):
        self.geom = geom
        self.pattern = pattern

    def to_sql(self, field: str) -> str:
        return f"ST_Relate({field}, {self._geom_to_sql(self.geom)}, '{self.pattern}')"

    def _geom_to_sql(self, geom: Any) -> str:
        if hasattr(geom, 'to_wkt'):
            return f"ST_GeomFromText('{geom.to_wkt()}')"
        return str(geom)


class Transform(SpatialFunction):
    """Transform geometry to a different SRID."""

    name = 'ST_Transform'

    def __init__(self, srid: int):
        self.srid = srid

    def to_sql(self, field: str) -> str:
        return f"ST_Transform({field}, {self.srid})"


class Buffer(SpatialFunction):
    """
    Create a buffer around a geometry.

    Example:
        # Create 1km buffer
        buffered = Buffer(location, distance=1000)
    """

    name = 'ST_Buffer'

    def __init__(self, distance: float, segments: int = 8):
        self.distance = distance
        self.segments = segments

    def to_sql(self, field: str) -> str:
        return f"ST_Buffer({field}, {self.distance}, {self.segments})"


class Envelope(SpatialFunction):
    """Get bounding box envelope of geometry."""

    name = 'ST_Envelope'

    def to_sql(self, field: str) -> str:
        return f"ST_Envelope({field})"


class Centroid(SpatialFunction):
    """Get centroid of geometry."""

    name = 'ST_Centroid'

    def to_sql(self, field: str) -> str:
        return f"ST_Centroid({field})"


class ConvexHull(SpatialFunction):
    """Get convex hull of geometry."""

    name = 'ST_ConvexHull'

    def to_sql(self, field: str) -> str:
        return f"ST_ConvexHull({field})"


class Union(SpatialFunction):
    """Union of geometries."""

    name = 'ST_Union'

    def __init__(self, geom: Any):
        self.geom = geom

    def to_sql(self, field: str) -> str:
        return f"ST_Union({field}, {self._geom_to_sql(self.geom)})"

    def _geom_to_sql(self, geom: Any) -> str:
        if hasattr(geom, 'to_wkt'):
            return f"ST_GeomFromText('{geom.to_wkt()}')"
        return str(geom)


class Intersection(SpatialFunction):
    """Intersection of geometries."""

    name = 'ST_Intersection'

    def __init__(self, geom: Any):
        self.geom = geom

    def to_sql(self, field: str) -> str:
        return f"ST_Intersection({field}, {self._geom_to_sql(self.geom)})"

    def _geom_to_sql(self, geom: Any) -> str:
        if hasattr(geom, 'to_wkt'):
            return f"ST_GeomFromText('{geom.to_wkt()}')"
        return str(geom)


class Difference(SpatialFunction):
    """Difference of geometries."""

    name = 'ST_Difference'

    def __init__(self, geom: Any):
        self.geom = geom

    def to_sql(self, field: str) -> str:
        return f"ST_Difference({field}, {self._geom_to_sql(self.geom)})"

    def _geom_to_sql(self, geom: Any) -> str:
        if hasattr(geom, 'to_wkt'):
            return f"ST_GeomFromText('{geom.to_wkt()}')"
        return str(geom)


class SymDifference(SpatialFunction):
    """Symmetric difference of geometries."""

    name = 'ST_SymDifference'

    def __init__(self, geom: Any):
        self.geom = geom

    def to_sql(self, field: str) -> str:
        return f"ST_SymDifference({field}, {self._geom_to_sql(self.geom)})"

    def _geom_to_sql(self, geom: Any) -> str:
        if hasattr(geom, 'to_wkt'):
            return f"ST_GeomFromText('{geom.to_wkt()}')"
        return str(geom)


class Area(SpatialFunction):
    """Calculate area of geometry."""

    name = 'ST_Area'

    def __init__(self, spheroid: bool = False):
        self.spheroid = spheroid

    def to_sql(self, field: str) -> str:
        if self.spheroid:
            return f"ST_Area({field}::geography, true)"
        return f"ST_Area({field})"


class Length(SpatialFunction):
    """Calculate length of geometry."""

    name = 'ST_Length'

    def __init__(self, spheroid: bool = False):
        self.spheroid = spheroid

    def to_sql(self, field: str) -> str:
        if self.spheroid:
            return f"ST_Length({field}::geography)"
        return f"ST_Length({field})"


class Perimeter(SpatialFunction):
    """Calculate perimeter of geometry."""

    name = 'ST_Perimeter'

    def to_sql(self, field: str) -> str:
        return f"ST_Perimeter({field})"


class AsGeoJSON(SpatialFunction):
    """Convert geometry to GeoJSON."""

    name = 'ST_AsGeoJSON'

    def __init__(self, precision: int = 15, options: int = 0):
        self.precision = precision
        self.options = options

    def to_sql(self, field: str) -> str:
        return f"ST_AsGeoJSON({field}, {self.precision}, {self.options})"


class AsGML(SpatialFunction):
    """Convert geometry to GML."""

    name = 'ST_AsGML'

    def __init__(self, version: int = 2):
        self.version = version

    def to_sql(self, field: str) -> str:
        return f"ST_AsGML({self.version}, {field})"


class AsKML(SpatialFunction):
    """Convert geometry to KML."""

    name = 'ST_AsKML'

    def __init__(self, precision: int = 15):
        self.precision = precision

    def to_sql(self, field: str) -> str:
        return f"ST_AsKML({field}, {self.precision})"


class AsSVG(SpatialFunction):
    """Convert geometry to SVG."""

    name = 'ST_AsSVG'

    def __init__(self, rel: bool = False, precision: int = 15):
        self.rel = rel
        self.precision = precision

    def to_sql(self, field: str) -> str:
        rel_flag = 1 if self.rel else 0
        return f"ST_AsSVG({field}, {rel_flag}, {self.precision})"


class GeoHash(SpatialFunction):
    """Encode geometry as geohash."""

    name = 'ST_GeoHash'

    def __init__(self, precision: int = None):
        self.precision = precision

    def to_sql(self, field: str) -> str:
        if self.precision:
            return f"ST_GeoHash({field}, {self.precision})"
        return f"ST_GeoHash({field})"


class DWithin(SpatialFunction):
    """
    Check if geometry is within distance of another.

    Example:
        stores = await Store.filter(
            location__dwithin=(point, 5000)  # 5km
        )
    """

    name = 'ST_DWithin'

    def __init__(self, geom: Any, distance: float, use_spheroid: bool = False):
        self.geom = geom
        self.distance = distance
        self.use_spheroid = use_spheroid

    def to_sql(self, field: str) -> str:
        geom_sql = self._geom_to_sql(self.geom)
        if self.use_spheroid:
            return f"ST_DWithin({field}::geography, {geom_sql}::geography, {self.distance})"
        return f"ST_DWithin({field}, {geom_sql}, {self.distance})"

    def _geom_to_sql(self, geom: Any) -> str:
        if hasattr(geom, 'to_wkt'):
            return f"ST_GeomFromText('{geom.to_wkt()}')"
        return str(geom)

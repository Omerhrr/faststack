"""
GeoModel base class with spatial methods.
"""

from typing import Any, List, Optional, Type
from .fields import Point, Polygon
from .measure import Distance


class GeoModel:
    """
    Base class for models with geometry fields.

    Provides spatial query methods.

    Example:
        class Store(GeoModel, Model):
            name = CharField()
            location = PointField()

        # Find nearby stores
        nearby = await Store.nearby(location, radius=5000)

        # Find stores within polygon
        in_area = await Store.within(polygon)
    """

    # Geometry field name (override in subclass)
    geometry_field: str = 'geometry'

    @classmethod
    async def nearby(
        cls,
        point: Point,
        radius: float,
        unit: str = 'm',
        limit: int = None
    ) -> List['GeoModel']:
        """
        Find objects within radius of a point.

        Args:
            point: Center point
            radius: Search radius
            unit: Unit ('m', 'km', 'mi', 'ft')
            limit: Max results

        Returns:
            List of nearby objects
        """
        # Convert radius to meters
        d = Distance(**{unit: radius})
        radius_meters = d.m

        # Use DWithin for efficient spatial query
        # This would be implemented with actual ORM integration
        query = cls.filter(**{
            f'{cls.geometry_field}__dwithin': (point, radius_meters)
        })

        if limit:
            query = query.limit(limit)

        return await query

    @classmethod
    async def within(cls, polygon: Polygon) -> List['GeoModel']:
        """
        Find objects within a polygon.

        Args:
            polygon: Search polygon

        Returns:
            List of objects within polygon
        """
        return await cls.filter(**{
            f'{cls.geometry_field}__within': polygon
        })

    @classmethod
    async def containing(cls, point: Point) -> List['GeoModel']:
        """
        Find objects containing a point.

        Args:
            point: Point to search for

        Returns:
            List of objects containing the point
        """
        return await cls.filter(**{
            f'{cls.geometry_field}__contains': point
        })

    @classmethod
    async def bounds(cls) -> tuple:
        """
        Get bounding box of all geometries.

        Returns:
            Tuple of (min_x, min_y, max_x, max_y)
        """
        # This would query for extent
        pass

    def distance_to(self, other: 'GeoModel') -> Distance:
        """
        Calculate distance to another geometry.

        Args:
            other: Other model instance

        Returns:
            Distance object
        """
        # This would calculate distance
        pass

    def buffer(self, distance: float, unit: str = 'm') -> Polygon:
        """
        Create buffer around geometry.

        Args:
            distance: Buffer distance
            unit: Distance unit

        Returns:
            Polygon buffer
        """
        pass


class GeoQuerySet:
    """
    QuerySet mixin for spatial queries.
    """

    def distance(self, point: Point) -> 'GeoQuerySet':
        """
        Annotate with distance to point.

        Args:
            point: Reference point

        Returns:
            QuerySet with distance annotation
        """
        # Add distance annotation
        return self.annotate(distance=f'ST_Distance({self.geometry_field}, ST_MakePoint({point.x}, {point.y}))')

    def within_distance(self, point: Point, distance: float) -> 'GeoQuerySet':
        """
        Filter objects within distance of point.

        Args:
            point: Reference point
            distance: Maximum distance in meters

        Returns:
            Filtered QuerySet
        """
        return self.filter(**{
            f'{self.geometry_field}__dwithin': (point, distance)
        })

    def within_polygon(self, polygon: Polygon) -> 'GeoQuerySet':
        """Filter objects within polygon."""
        return self.filter(**{
            f'{self.geometry_field}__within': polygon
        })

    def intersects(self, geometry: Any) -> 'GeoQuerySet':
        """Filter objects that intersect geometry."""
        return self.filter(**{
            f'{self.geometry_field}__intersects': geometry
        })

    def contains(self, geometry: Any) -> 'GeoQuerySet':
        """Filter objects that contain geometry."""
        return self.filter(**{
            f'{self.geometry_field}__contains': geometry
        })

    def bounding_box(self) -> tuple:
        """Get bounding box of queryset."""
        pass

    def centroid(self) -> 'GeoQuerySet':
        """Annotate with centroid."""
        return self.annotate(centroid=f'ST_Centroid({self.geometry_field})')

    def transform(self, srid: int) -> 'GeoQuerySet':
        """Transform to different SRID."""
        return self.annotate(geom_transformed=f'ST_Transform({self.geometry_field}, {srid})')

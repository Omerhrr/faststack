"""
FastStack GIS/GeoDjango Support

PostGIS spatial queries and geometry fields.

Example:
    from faststack.contrib.gis import GeometryField, PointField, PolygonField
    from faststack.contrib.gis import distance, within, contains

    class Store(Model):
        name = CharField()
        location = PointField()

        class Meta:
            indexes = [GISTIndex('location')]

    # Find stores within 5km
    stores = await Store.filter(
        location__distance_lte=(point, D(km=5))
    )

    # Find stores in a polygon
    stores = await Store.filter(
        location__within=city_boundary
    )
"""

from .fields import (
    GeometryField,
    PointField,
    LineStringField,
    PolygonField,
    MultiPointField,
    MultiLineStringField,
    MultiPolygonField,
    GeometryCollectionField,
)
from .functions import (
    Distance,
    Within,
    Contains,
    Intersects,
    Touches,
    Crosses,
    Overlaps,
    Equals,
    Disjoint,
    Relate,
    Transform,
    Buffer,
    Envelope,
    Centroid,
    ConvexHull,
    Union,
    Intersection,
    Difference,
    SymDifference,
    Area,
    Length,
    Perimeter,
    AsGeoJSON,
    AsGML,
    AsKML,
    AsSVG,
    GeoHash,
)
from .measure import Distance as D
from .models import GeoModel

__all__ = [
    # Fields
    'GeometryField',
    'PointField',
    'LineStringField',
    'PolygonField',
    'MultiPointField',
    'MultiLineStringField',
    'MultiPolygonField',
    'GeometryCollectionField',
    # Functions
    'Distance',
    'Within',
    'Contains',
    'Intersects',
    'Touches',
    'Crosses',
    'Overlaps',
    'Equals',
    'Disjoint',
    'Relate',
    'Transform',
    'Buffer',
    'Envelope',
    'Centroid',
    'ConvexHull',
    'Union',
    'Intersection',
    'Difference',
    'SymDifference',
    'Area',
    'Length',
    'Perimeter',
    'AsGeoJSON',
    'AsGML',
    'AsKML',
    'AsSVG',
    'GeoHash',
    # Utils
    'D',
    'GeoModel',
]

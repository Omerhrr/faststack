"""
GIS Geometry Fields for PostGIS support.
"""

from typing import Any, Dict, Optional, Tuple, Union
from dataclasses import dataclass
import json
import re


@dataclass
class Point:
    """A 2D or 3D point."""
    x: float
    y: float
    z: Optional[float] = None
    srid: int = 4326

    def __repr__(self) -> str:
        if self.z is not None:
            return f"Point({self.x}, {self.y}, {self.z})"
        return f"Point({self.x}, {self.y})"

    @classmethod
    def from_wkt(cls, wkt: str) -> 'Point':
        """Parse from WKT format."""
        match = re.match(r'POINT\s*\(\s*([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?\s*\)', wkt, re.I)
        if match:
            x = float(match.group(1))
            y = float(match.group(2))
            z = float(match.group(3)) if match.group(3) else None
            return cls(x, x, z)
        raise ValueError(f"Invalid WKT: {wkt}")

    def to_wkt(self) -> str:
        """Convert to WKT format."""
        if self.z is not None:
            return f"POINT({self.x} {self.y} {self.z})"
        return f"POINT({self.x} {self.y})"

    def to_geojson(self) -> dict:
        """Convert to GeoJSON."""
        coords = [self.x, self.y]
        if self.z is not None:
            coords.append(self.z)
        return {
            'type': 'Point',
            'coordinates': coords
        }

    @classmethod
    def from_geojson(cls, data: Union[str, dict]) -> 'Point':
        """Create from GeoJSON."""
        if isinstance(data, str):
            data = json.loads(data)

        coords = data['coordinates']
        return cls(
            x=coords[0],
            y=coords[1],
            z=coords[2] if len(coords) > 2 else None
        )


@dataclass
class LineString:
    """A line string (polyline)."""
    points: list  # List of Point
    srid: int = 4326

    def __repr__(self) -> str:
        return f"LineString({len(self.points)} points)"

    def to_wkt(self) -> str:
        """Convert to WKT."""
        coords = []
        for p in self.points:
            coords.append(f"{p.x} {p.y}")
        return f"LINESTRING({', '.join(coords)})"

    def to_geojson(self) -> dict:
        """Convert to GeoJSON."""
        coords = []
        for p in self.points:
            coords.append([p.x, p.y])
        return {
            'type': 'LineString',
            'coordinates': coords
        }


@dataclass
class Polygon:
    """A polygon with optional holes."""
    exterior: list  # List of Point
    holes: list = None  # List of rings (each ring is a list of Points)
    srid: int = 4326

    def __repr__(self) -> str:
        holes_count = len(self.holes) if self.holes else 0
        return f"Polygon({len(self.exterior)} points, {holes_count} holes)"

    def to_wkt(self) -> str:
        """Convert to WKT."""
        rings = []

        # Exterior ring
        coords = [f"{p.x} {p.y}" for p in self.exterior]
        rings.append(f"({', '.join(coords)})")

        # Holes
        if self.holes:
            for hole in self.holes:
                coords = [f"{p.x} {p.y}" for p in hole]
                rings.append(f"({', '.join(coords)})")

        return f"POLYGON({', '.join(rings)})"

    def to_geojson(self) -> dict:
        """Convert to GeoJSON."""
        rings = []

        # Exterior ring
        rings.append([[p.x, p.y] for p in self.exterior])

        # Holes
        if self.holes:
            for hole in self.holes:
                rings.append([[p.x, p.y] for p in hole])

        return {
            'type': 'Polygon',
            'coordinates': rings
        }


class GeometryField:
    """
    Base geometry field for GIS support.

    Attributes:
        srid: Spatial Reference System ID (default: 4326 for WGS84)
        dim: Dimension (2 or 3)
        geography: Use geography type (lat/lon) vs geometry (projected)

    Example:
        class Location(Model):
            name = CharField()
            geom = GeometryField(srid=4326)
    """

    # Field type identifier
    field_type = 'geometry'

    # GEOS geometry type name
    geom_type = 'GEOMETRY'

    def __init__(
        self,
        srid: int = 4326,
        dim: int = 2,
        geography: bool = False,
        null: bool = True,
        blank: bool = True,
        default: Any = None,
        **kwargs
    ):
        self.srid = srid
        self.dim = dim
        self.geography = geography
        self.null = null
        self.blank = blank
        self.default = default
        self.kwargs = kwargs

    def __repr__(self) -> str:
        return f"GeometryField(srid={self.srid}, type={self.geom_type})"

    def get_sql_type(self, dialect: str = 'postgresql') -> str:
        """Get SQL column type for the database."""
        if dialect == 'postgresql':
            geom_type = self.geom_type
            if self.dim == 3:
                geom_type += 'Z'

            if self.geography:
                return f"GEOGRAPHY({geom_type}, {self.srid})"
            return f"GEOMETRY({geom_type}, {self.srid})"

        # Fallback for other databases
        return 'TEXT'

    def to_python(self, value: Any) -> Any:
        """Convert database value to Python."""
        if value is None:
            return None

        if isinstance(value, (Point, LineString, Polygon)):
            return value

        if isinstance(value, str):
            return self.from_wkt(value)

        if isinstance(value, dict):
            return self.from_geojson(value)

        return value

    def from_wkt(self, wkt: str) -> Any:
        """Parse WKT string to geometry object."""
        wkt = wkt.strip().upper()

        if wkt.startswith('POINT'):
            return Point.from_wkt(wkt)
        elif wkt.startswith('LINESTRING'):
            # Parse linestring
            match = re.search(r'\((.*)\)', wkt)
            if match:
                coords = []
                for pair in match.group(1).split(','):
                    x, y = pair.strip().split()
                    coords.append(Point(float(x), float(y)))
                return LineString(coords)
        elif wkt.startswith('POLYGON'):
            # Parse polygon
            match = re.search(r'\((.*)\)', wkt)
            if match:
                # This is simplified - real implementation would handle holes
                coords = []
                pairs = match.group(1).split(',')
                for pair in pairs:
                    x, y = pair.strip().split()
                    coords.append(Point(float(x), float(y)))
                return Polygon(coords)

        return wkt

    def from_geojson(self, data: Union[str, dict]) -> Any:
        """Parse GeoJSON to geometry object."""
        if isinstance(data, str):
            data = json.loads(data)

        geom_type = data.get('type')
        coords = data.get('coordinates', [])

        if geom_type == 'Point':
            return Point(coords[0], coords[1], coords[2] if len(coords) > 2 else None)
        elif geom_type == 'LineString':
            points = [Point(c[0], c[1]) for c in coords]
            return LineString(points)
        elif geom_type == 'Polygon':
            exterior = [Point(c[0], c[1]) for c in coords[0]]
            holes = [[Point(c[0], c[1]) for c in ring] for ring in coords[1:]] if len(coords) > 1 else None
            return Polygon(exterior, holes)

        return data

    def to_db(self, value: Any) -> Any:
        """Convert Python value to database format."""
        if value is None:
            return None

        if hasattr(value, 'to_wkt'):
            return value.to_wkt()

        if isinstance(value, dict):
            return json.dumps(value)

        return str(value)


class PointField(GeometryField):
    """Field for storing Point geometries."""
    geom_type = 'POINT'


class LineStringField(GeometryField):
    """Field for storing LineString geometries."""
    geom_type = 'LINESTRING'


class PolygonField(GeometryField):
    """Field for storing Polygon geometries."""
    geom_type = 'POLYGON'


class MultiPointField(GeometryField):
    """Field for storing MultiPoint geometries."""
    geom_type = 'MULTIPOINT'


class MultiLineStringField(GeometryField):
    """Field for storing MultiLineString geometries."""
    geom_type = 'MULTILINESTRING'


class MultiPolygonField(GeometryField):
    """Field for storing MultiPolygon geometries."""
    geom_type = 'MULTIPOLYGON'


class GeometryCollectionField(GeometryField):
    """Field for storing GeometryCollection."""
    geom_type = 'GEOMETRYCOLLECTION'


class GISTIndex:
    """
    GiST index for geometry fields.

    Example:
        class Store(Model):
            location = PointField()

            class Meta:
                indexes = [GISTIndex('location')]
    """

    def __init__(self, field: str, name: str = None):
        self.field = field
        self.name = name or f"idx_{field}_gist"

    def get_sql(self, table: str) -> str:
        """Get CREATE INDEX SQL."""
        return f"CREATE INDEX {self.name} ON {table} USING GIST ({self.field})"


class SpatialIndex:
    """Spatial index for geometry columns."""

    def __init__(self, field: str, name: str = None):
        self.field = field
        self.name = name or f"idx_{field}_spatial"

    def get_sql(self, table: str, dialect: str = 'postgresql') -> str:
        """Get CREATE INDEX SQL."""
        if dialect == 'mysql':
            return f"CREATE SPATIAL INDEX {self.name} ON {table} ({self.field})"
        elif dialect == 'sqlite':
            return f"SELECT CreateSpatialIndex('{table}', '{self.field}')"
        else:  # PostgreSQL
            return f"CREATE INDEX {self.name} ON {table} USING GIST ({self.field})"

"""Work out which room the robot is in from the map and its position."""

from __future__ import annotations

import json
import logging

from deebot_client.rs.util import decompress_base64_data

_LOGGER = logging.getLogger(__name__)

type Polygon = list[tuple[float, float]]

# Map info layer that holds the room outlines, as "<room id>;x,y;x,y;...".
_ROOM_LAYER = "2"


def parse_room_polygons(map_info: str) -> dict[int, Polygon]:
    """Return the room outlines from compressed map info, keyed by room id."""
    try:
        layers = json.loads(decompress_base64_data(map_info))
    except (ValueError, TypeError):
        _LOGGER.debug("Could not decode map info", exc_info=True)
        return {}

    rooms: dict[int, Polygon] = {}
    for layer in layers:
        if not layer or layer[0] != _ROOM_LAYER:
            continue
        for entry in layer[1:]:
            room_id, _, points = entry.partition(";")
            if (polygon := parse_polygon(points)) and room_id.lstrip("-").isdigit():
                rooms[int(room_id)] = polygon
    return rooms


def parse_polygon(points: str) -> Polygon:
    """Parse "x,y;x,y;..." into a polygon with at least three points."""
    polygon: Polygon = []
    for point in points.split(";"):
        x, _, y = point.partition(",")
        try:
            polygon.append((float(x), float(y.split(",")[0])))
        except ValueError:
            continue
    return polygon if len(polygon) >= 3 else []


def contains(polygon: Polygon, x: float, y: float) -> bool:
    """Return whether the point lies inside the polygon (ray casting)."""
    inside = False
    j = len(polygon) - 1
    for i, (xi, yi) in enumerate(polygon):
        xj, yj = polygon[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def find_room(polygons: dict[int, Polygon], x: float, y: float) -> int | None:
    """Return the id of the room containing the point, if any."""
    for room_id, polygon in polygons.items():
        if contains(polygon, x, y):
            return room_id
    return None

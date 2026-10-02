"""Geometry and spatial data structures for document layout modeling.

Provides BoundingBox calculations, intersection tests, normalization, and scaling.
"""

from __future__ import annotations
from typing import List, Tuple, Union
from pydantic import BaseModel, Field, model_validator


class BoundingBox(BaseModel):
    """Represents a rectangular bounding box with coordinates [x1, y1, x2, y2].

    x1: left coordinate
    y1: top coordinate
    x2: right coordinate
    y2: bottom coordinate
    """

    x1: float = Field(..., description="Left / minimum x coordinate")
    y1: float = Field(..., description="Top / minimum y coordinate")
    x2: float = Field(..., description="Right / maximum x coordinate")
    y2: float = Field(..., description="Bottom / maximum y coordinate")

    @model_validator(mode="after")
    def validate_coordinates(self) -> BoundingBox:
        """Ensures that x2 >= x1 and y2 >= y1 by ordering if inverted."""
        if self.x1 > self.x2:
            self.x1, self.x2 = self.x2, self.x1
        if self.y1 > self.y2:
            self.y1, self.y2 = self.y2, self.y1
        return self

    @property
    def left(self) -> float:
        return self.x1

    @property
    def top(self) -> float:
        return self.y1

    @property
    def right(self) -> float:
        return self.x2

    @property
    def bottom(self) -> float:
        return self.y2

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> Tuple[float, float]:
        return (self.x1 + self.width / 2.0, self.y1 + self.height / 2.0)

    @property
    def center_x(self) -> float:
        return self.x1 + self.width / 2.0

    @property
    def center_y(self) -> float:
        return self.y1 + self.height / 2.0

    def to_list(self) -> List[float]:
        """Returns [x1, y1, x2, y2]."""
        return [self.x1, self.y1, self.x2, self.y2]

    def to_xywh(self) -> Tuple[float, float, float, float]:
        """Returns (x1, y1, width, height)."""
        return (self.x1, self.y1, self.width, self.height)

    @classmethod
    def from_xywh(cls, x: float, y: float, w: float, h: float) -> BoundingBox:
        """Constructs a bounding box from top-left (x, y) and dimensions (w, h)."""
        return cls(x1=x, y1=y, x2=x + w, y2=y + h)

    @classmethod
    def from_points(cls, points: List[Union[List[float], Tuple[float, float]]]) -> BoundingBox:
        """Constructs an axis-aligned bounding box encompassing polygon points (e.g. from OCR)."""
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return cls(x1=min(xs), y1=min(ys), x2=max(xs), y2=max(ys))

    def scale(self, scale_x: float, scale_y: float) -> BoundingBox:
        """Returns a scaled bounding box."""
        return BoundingBox(
            x1=self.x1 * scale_x,
            y1=self.y1 * scale_y,
            x2=self.x2 * scale_x,
            y2=self.y2 * scale_y,
        )

    def translate(self, dx: float, dy: float) -> BoundingBox:
        """Translates the bounding box by (dx, dy)."""
        return BoundingBox(
            x1=self.x1 + dx,
            y1=self.y1 + dy,
            x2=self.x2 + dx,
            y2=self.y2 + dy,
        )

    def contains(self, other: BoundingBox) -> bool:
        """Checks if this bounding box completely encloses another bounding box."""
        return (
            self.x1 <= other.x1
            and self.y1 <= other.y1
            and self.x2 >= other.x2
            and self.y2 >= other.y2
        )

    def contains_point(self, x: float, y: float) -> bool:
        """Checks if a 2D coordinate point lies within this bounding box."""
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2

    def intersects(self, other: BoundingBox) -> bool:
        """Checks if this bounding box intersects with another."""
        return not (
            self.x2 < other.x1
            or self.x1 > other.x2
            or self.y2 < other.y1
            or self.y1 > other.y2
        )

    def intersection(self, other: BoundingBox) -> Union[BoundingBox, None]:
        """Calculates the intersection box with another bounding box, or None if disjoint."""
        if not self.intersects(other):
            return None
        return BoundingBox(
            x1=max(self.x1, other.x1),
            y1=max(self.y1, other.y1),
            x2=min(self.x2, other.x2),
            y2=min(self.y2, other.y2),
        )

    def union(self, other: BoundingBox) -> BoundingBox:
        """Returns the bounding box encompassing both bounding boxes."""
        return BoundingBox(
            x1=min(self.x1, other.x1),
            y1=min(self.y1, other.y1),
            x2=max(self.x2, other.x2),
            y2=max(self.y2, other.y2),
        )

    def iou(self, other: BoundingBox) -> float:
        """Computes Intersection over Union (IoU) with another bounding box."""
        inter = self.intersection(other)
        if inter is None:
            return 0.0
        inter_area = inter.area
        union_area = self.area + other.area - inter_area
        return inter_area / union_area if union_area > 0.0 else 0.0

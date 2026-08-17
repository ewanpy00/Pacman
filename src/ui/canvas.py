"""A hand-rolled pixel framebuffer and the few primitives the game needs.

Everything is drawn by writing bytes into an RGB buffer we own. That is
exactly the model MiniLibX offers: allocate an image, take its data
address, write pixels, then put the image to the window once. MLX has no
drawing primitives at all, so lines, discs, polygons and translucent
veils are all built here on top of single-pixel and horizontal-span
writes.

Spans matter for speed: filling a run of pixels with one slice
assignment is orders of magnitude faster in Python than looping over
them, so every filled shape is expressed as a stack of spans.
"""

from __future__ import annotations

from math import isqrt

Color = tuple[int, int, int]

_BYTES_PER_PIXEL = 3


class Canvas:
    """An RGB pixel buffer that can be handed to the window as an image."""

    def __init__(self, width: int, height: int) -> None:
        """Allocate a black buffer of ``width`` x ``height`` pixels.

        Args:
            width: Buffer width in pixels.
            height: Buffer height in pixels.
        """
        self.width = width
        self.height = height
        self._buf = bytearray(width * height * _BYTES_PER_PIXEL)
        self._dim_tables: dict[int, bytes] = {}

    def to_bytes(self) -> bytes:
        """Return the raw RGB bytes, ready to be shown as an image."""
        return bytes(self._buf)

    def copy_from(self, other: "Canvas") -> None:
        """Overwrite this buffer with another one of the same size.

        Args:
            other: The canvas to copy; must have identical dimensions.
        """
        self._buf[:] = other._buf

    def clear(self, color: Color) -> None:
        """Fill the whole buffer with a single colour."""
        self._buf[:] = bytes(color) * (self.width * self.height)

    def set_pixel(self, x: int, y: int, color: Color) -> None:
        """Write one pixel, ignoring coordinates outside the buffer."""
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return
        offset = (y * self.width + x) * _BYTES_PER_PIXEL
        self._buf[offset:offset + _BYTES_PER_PIXEL] = bytes(color)

    def span(self, x0: int, x1: int, y: int, color: Color) -> None:
        """Fill the inclusive horizontal run ``x0``..``x1`` on row ``y``.

        The run is clipped to the buffer, so callers never need to.

        Args:
            x0: One end of the run.
            x1: The other end; may be smaller than ``x0``.
            y: Row to fill.
            color: Colour to write.
        """
        if y < 0 or y >= self.height:
            return
        if x1 < x0:
            x0, x1 = x1, x0
        if x1 < 0 or x0 >= self.width:
            return
        x0 = max(0, x0)
        x1 = min(self.width - 1, x1)
        start = (y * self.width + x0) * _BYTES_PER_PIXEL
        end = (y * self.width + x1 + 1) * _BYTES_PER_PIXEL
        self._buf[start:end] = bytes(color) * (x1 - x0 + 1)

    def filled_rect(self, x: int, y: int, w: int, h: int,
                    color: Color) -> None:
        """Fill an axis-aligned rectangle.

        Args:
            x: Left edge.
            y: Top edge.
            w: Width in pixels.
            h: Height in pixels.
            color: Colour to write.
        """
        if w <= 0 or h <= 0:
            return
        for row in range(max(0, y), min(self.height, y + h)):
            self.span(x, x + w - 1, row, color)

    def line(self, x0: int, y0: int, x1: int, y1: int, color: Color,
             thickness: int = 1) -> None:
        """Draw a straight line with Bresenham's algorithm.

        Thickness is achieved with a square brush, which is enough for
        the axis-aligned maze walls this game draws.

        Args:
            x0: Start column.
            y0: Start row.
            x1: End column.
            y1: End row.
            color: Colour to write.
            thickness: Brush size in pixels.
        """
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        half = thickness // 2
        while True:
            if thickness <= 1:
                self.set_pixel(x0, y0, color)
            else:
                self.filled_rect(x0 - half, y0 - half,
                                 thickness, thickness, color)
            if x0 == x1 and y0 == y1:
                break
            err2 = 2 * err
            if err2 >= dy:
                err += dy
                x0 += sx
            if err2 <= dx:
                err += dx
                y0 += sy

    def filled_circle(self, cx: int, cy: int, radius: int,
                      color: Color) -> None:
        """Fill a disc centred on ``(cx, cy)``.

        Each row's half-width comes from an integer square root, so the
        whole disc is drawn as ``2 * radius`` spans.

        Args:
            cx: Centre column.
            cy: Centre row.
            radius: Radius in pixels.
            color: Colour to write.
        """
        if radius <= 0:
            return
        for dy in range(-radius, radius + 1):
            dx = isqrt(radius * radius - dy * dy)
            self.span(cx - dx, cx + dx, cy + dy, color)

    def filled_polygon(self, points: list[tuple[int, int]],
                       color: Color) -> None:
        """Fill a polygon using an even-odd scanline rule.

        Args:
            points: The vertices, in order; the shape is closed for you.
            color: Colour to write.
        """
        if len(points) < 3:
            return
        ys = [p[1] for p in points]
        top = max(0, min(ys))
        bottom = min(self.height - 1, max(ys))
        count = len(points)
        for y in range(top, bottom + 1):
            crossings: list[float] = []
            for i in range(count):
                ax, ay = points[i]
                bx, by = points[(i + 1) % count]
                if ay == by:
                    continue
                if min(ay, by) <= y < max(ay, by):
                    ratio = (y - ay) / (by - ay)
                    crossings.append(ax + ratio * (bx - ax))
            crossings.sort()
            for i in range(0, len(crossings) - 1, 2):
                self.span(int(crossings[i]), int(crossings[i + 1]),
                          y, color)

    def darken(self, percent: int) -> None:
        """Dim the whole buffer towards black.

        Implemented with a byte translation table so the blend runs at C
        speed instead of looping over half a million bytes in Python.

        Args:
            percent: How much brightness to keep, from 0 to 100.
        """
        keep = max(0, min(100, percent))
        table = self._dim_tables.get(keep)
        if table is None:
            table = bytes(value * keep // 100 for value in range(256))
            self._dim_tables[keep] = table
        self._buf = self._buf.translate(table)

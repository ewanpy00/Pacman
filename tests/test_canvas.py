"""Tests for the pixel framebuffer, its primitives and the bitmap font."""

from src.ui.canvas import Canvas
from src.ui.font import GLYPH_HEIGHT, draw_text, text_height, text_width

_WHITE = (255, 255, 255)
_RED = (255, 0, 0)
_BLACK = (0, 0, 0)


def _pixel(canvas: Canvas, x: int, y: int) -> tuple[int, int, int]:
    """Read back one pixel as an RGB tuple."""
    data = canvas.to_bytes()
    offset = (y * canvas.width + x) * 3
    return (data[offset], data[offset + 1], data[offset + 2])


def _lit(canvas: Canvas) -> int:
    """Count how many pixels are not black."""
    data = canvas.to_bytes()
    return sum(1 for i in range(0, len(data), 3)
               if data[i] or data[i + 1] or data[i + 2])


def test_new_canvas_is_black() -> None:
    """A fresh buffer starts fully cleared."""
    assert _lit(Canvas(4, 4)) == 0


def test_clear_fills_every_pixel() -> None:
    """Clearing writes the colour everywhere."""
    canvas = Canvas(3, 2)
    canvas.clear(_RED)
    assert _lit(canvas) == 6
    assert _pixel(canvas, 2, 1) == _RED


def test_set_pixel_writes_one_point() -> None:
    """A single write touches exactly one pixel."""
    canvas = Canvas(4, 4)
    canvas.set_pixel(1, 2, _WHITE)
    assert _pixel(canvas, 1, 2) == _WHITE
    assert _lit(canvas) == 1


def test_out_of_bounds_writes_are_ignored() -> None:
    """Drawing outside the buffer is silently clipped, never an error."""
    canvas = Canvas(4, 4)
    for x, y in ((-1, 0), (0, -1), (4, 0), (0, 4), (99, 99)):
        canvas.set_pixel(x, y, _WHITE)
    assert _lit(canvas) == 0


def test_span_is_inclusive_and_clipped() -> None:
    """A span covers both ends and is trimmed to the buffer."""
    canvas = Canvas(5, 1)
    canvas.span(1, 3, 0, _WHITE)
    assert _lit(canvas) == 3
    canvas.clear(_BLACK)
    canvas.span(-10, 10, 0, _WHITE)
    assert _lit(canvas) == 5


def test_span_accepts_reversed_ends() -> None:
    """Passing the ends the other way round draws the same run."""
    canvas = Canvas(5, 1)
    canvas.span(3, 1, 0, _WHITE)
    assert _lit(canvas) == 3


def test_filled_rect_covers_its_area() -> None:
    """A rectangle fills exactly width times height pixels."""
    canvas = Canvas(6, 6)
    canvas.filled_rect(1, 1, 3, 2, _WHITE)
    assert _lit(canvas) == 6
    assert _pixel(canvas, 1, 1) == _WHITE
    assert _pixel(canvas, 3, 2) == _WHITE
    assert _pixel(canvas, 4, 1) == _BLACK


def test_empty_rect_draws_nothing() -> None:
    """Zero or negative extents are a no-op."""
    canvas = Canvas(4, 4)
    canvas.filled_rect(0, 0, 0, 3, _WHITE)
    canvas.filled_rect(0, 0, 3, -1, _WHITE)
    assert _lit(canvas) == 0


def test_horizontal_line_is_straight() -> None:
    """A line along one axis stays on its row."""
    canvas = Canvas(6, 3)
    canvas.line(0, 1, 5, 1, _WHITE)
    assert _lit(canvas) == 6
    assert all(_pixel(canvas, x, 1) == _WHITE for x in range(6))


def test_diagonal_line_touches_both_ends() -> None:
    """Bresenham reaches the exact endpoints."""
    canvas = Canvas(5, 5)
    canvas.line(0, 0, 4, 4, _WHITE)
    assert _pixel(canvas, 0, 0) == _WHITE
    assert _pixel(canvas, 4, 4) == _WHITE
    assert _lit(canvas) == 5


def test_filled_circle_is_symmetric() -> None:
    """A disc is centred and mirrored on both axes."""
    canvas = Canvas(11, 11)
    canvas.filled_circle(5, 5, 3, _WHITE)
    assert _pixel(canvas, 5, 5) == _WHITE
    for dx, dy in ((3, 0), (-3, 0), (0, 3), (0, -3)):
        assert _pixel(canvas, 5 + dx, 5 + dy) == _WHITE
    assert _pixel(canvas, 5 + 3, 5 + 3) == _BLACK


def test_zero_radius_circle_draws_nothing() -> None:
    """A disc with no radius is a no-op."""
    canvas = Canvas(5, 5)
    canvas.filled_circle(2, 2, 0, _WHITE)
    assert _lit(canvas) == 0


def test_filled_polygon_fills_a_triangle() -> None:
    """Scanline filling covers the interior of a simple shape."""
    canvas = Canvas(8, 8)
    canvas.filled_polygon([(0, 0), (7, 0), (0, 7)], _WHITE)
    assert _pixel(canvas, 0, 0) == _WHITE
    assert _pixel(canvas, 1, 1) == _WHITE
    assert _pixel(canvas, 7, 7) == _BLACK


def test_degenerate_polygon_draws_nothing() -> None:
    """Fewer than three vertices cannot enclose an area."""
    canvas = Canvas(5, 5)
    canvas.filled_polygon([(0, 0), (4, 4)], _WHITE)
    assert _lit(canvas) == 0


def test_darken_scales_every_channel() -> None:
    """Dimming multiplies the buffer without touching its size."""
    canvas = Canvas(2, 2)
    canvas.clear((200, 100, 50))
    canvas.darken(50)
    assert _pixel(canvas, 0, 0) == (100, 50, 25)
    assert len(canvas.to_bytes()) == 2 * 2 * 3


def test_darken_to_zero_is_black() -> None:
    """Keeping no brightness blanks the buffer."""
    canvas = Canvas(2, 2)
    canvas.clear(_WHITE)
    canvas.darken(0)
    assert _lit(canvas) == 0


def test_copy_from_duplicates_the_buffer() -> None:
    """Copying takes a snapshot rather than sharing memory."""
    source = Canvas(3, 3)
    source.clear(_RED)
    target = Canvas(3, 3)
    target.copy_from(source)
    assert _pixel(target, 1, 1) == _RED
    source.clear(_BLACK)
    assert _pixel(target, 1, 1) == _RED


def test_text_width_grows_with_scale() -> None:
    """Measurement matches the 5-plus-1 column advance."""
    assert text_width("", 2) == 0
    assert text_width("A", 1) == 5
    assert text_width("AB", 1) == 11
    assert text_width("AB", 3) == 33
    assert text_height(2) == GLYPH_HEIGHT * 2


def test_draw_text_marks_pixels_inside_its_box() -> None:
    """Text lands where it is asked to, and nowhere else."""
    canvas = Canvas(40, 12)
    draw_text(canvas, "Hi", 2, 2, _WHITE, 1)
    assert _lit(canvas) > 0
    data = canvas.to_bytes()
    for y in range(12):
        for x in range(40):
            offset = (y * 40 + x) * 3
            if data[offset]:
                assert 2 <= x < 2 + text_width("Hi", 1)
                assert 2 <= y < 2 + text_height(1)


def test_unknown_character_falls_back_to_a_box() -> None:
    """A glyph outside the table still renders something visible."""
    canvas = Canvas(10, 10)
    draw_text(canvas, "☃", 1, 1, _WHITE, 1)
    assert _lit(canvas) > 0

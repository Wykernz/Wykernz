"""Pixel-art scene primitives and animation for the rainy-day quest."""

import math

from theme import COLOR, FONT, FRAME_COUNT, HEIGHT, PIXELS_PER_DROP_STEP, WIDTH


class Canvas:
    """A compact indexed-color surface used by both image encoders."""

    def __init__(self, width: int, height: int, background: int) -> None:
        self.width = width
        self.height = height
        self.pixels = bytearray([background]) * (width * height)

    def rect(self, x: int, y: int, width: int, height: int, color: int) -> None:
        left = max(0, x)
        top = max(0, y)
        right = min(self.width, x + width)
        bottom = min(self.height, y + height)
        if left >= right or top >= bottom:
            return
        row = bytes([color]) * (right - left)
        for row_y in range(top, bottom):
            start = row_y * self.width + left
            self.pixels[start : start + len(row)] = row

    def pixel(self, x: int, y: int, color: int) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.pixels[y * self.width + x] = color

    def text(self, x: int, y: int, value: str, color: int, scale: int = 1) -> None:
        cursor_x = x
        for character in value.upper():
            glyph = FONT.get(character)
            if glyph is not None:
                for row_index, row in enumerate(glyph):
                    for column_index, active in enumerate(row):
                        if active == "1":
                            self.rect(
                                cursor_x + column_index * scale,
                                y + row_index * scale,
                                scale,
                                scale,
                                color,
                            )
            cursor_x += 6 * scale


def draw_mountain(canvas: Canvas, left: int, top: int, width: int, height: int, color: int) -> None:
    """Build a stepped silhouette that matches the scene's pixel scale."""
    for row in range(height):
        half_width = (row * width) // (height * 2)
        canvas.rect(left + width // 2 - half_width, top + row, half_width * 2 + 1, 1, color)


def draw_star(canvas: Canvas, x: int, y: int, color: int, bright: bool) -> None:
    canvas.rect(x, y + 2, 5, 1, color)
    canvas.rect(x + 2, y, 1, 5, color)
    if bright:
        canvas.pixel(x + 2, y + 2, COLOR["white"])


def draw_background(canvas: Canvas, frame: int) -> None:
    # Broad color bands create depth while keeping the GIF palette small.
    bands = (
        (0, 82, COLOR["night"]),
        (82, 188, COLOR["sky"]),
        (188, 270, COLOR["deep_blue"]),
        (270, 350, COLOR["panel"]),
        (350, HEIGHT, COLOR["deep_blue"]),
    )
    for top, bottom, shade in bands:
        canvas.rect(0, top, WIDTH, bottom - top, shade)

    # A quiet horizon glow separates the cloud from the mountains.
    canvas.rect(0, 258, WIDTH, 1, COLOR["ridge"])
    canvas.rect(0, 259, WIDTH, 2, COLOR["mountain"])
    draw_mountain(canvas, 75, 230, 206, 120, COLOR["mountain"])
    draw_mountain(canvas, 186, 247, 250, 104, COLOR["ridge"])
    draw_mountain(canvas, 472, 220, 240, 132, COLOR["mountain"])
    draw_mountain(canvas, 370, 255, 220, 96, COLOR["ridge"])

    star_positions = (
        (52, 103), (128, 79), (234, 116), (304, 63), (516, 82), (606, 120),
        (722, 82), (752, 151), (90, 182), (682, 194), (552, 57), (188, 167),
    )
    for index, (star_x, star_y) in enumerate(star_positions):
        visible = (frame // 4 + index * 3) % 10 != 0
        if visible:
            color = COLOR["star"] if index % 3 == 0 else COLOR["moonlight"]
            draw_star(canvas, star_x, star_y, color, (frame // 4 + index) % 2 == 0)

    # The little grass tufts make the horizon feel like a playable level.
    for tuft_x in (68, 113, 212, 273, 542, 630, 711, 748):
        canvas.rect(tuft_x, 347, 2, 6, COLOR["grass"])
        canvas.rect(tuft_x - 3, 347, 3, 2, COLOR["grass_light"])
        canvas.rect(tuft_x + 2, 345, 3, 2, COLOR["grass_light"])


def draw_puddle(canvas: Canvas, center_x: int, y: int, shimmer: bool) -> None:
    canvas.rect(center_x - 23, y + 4, 46, 4, COLOR["puddle"])
    canvas.rect(center_x - 16, y + 1, 32, 7, COLOR["puddle"])
    canvas.rect(center_x - 10, y + 1, 19, 2, COLOR["puddle_glint"])
    if shimmer:
        canvas.rect(center_x + 7, y + 4, 7, 1, COLOR["rain_glint"])


def draw_terrain(canvas: Canvas, frame: int) -> None:
    canvas.rect(0, 352, WIDTH, 3, COLOR["grass"])
    canvas.rect(0, 355, WIDTH, 24, COLOR["deep_blue"])
    canvas.rect(0, 355, WIDTH, 2, COLOR["grass_light"])
    for puddle_x, puddle_y in ((116, 359), (262, 366), (538, 360), (692, 365)):
        shimmer_phase = (frame + puddle_x // 17) % FRAME_COUNT
        draw_puddle(canvas, puddle_x, puddle_y, shimmer_phase < 6)


def draw_cloud_shape(canvas: Canvas, center_x: int, center_y: int, shade: int, outline: bool = False) -> None:
    blocks = (
        (-80, 14, 52, 40),
        (-63, -1, 75, 61),
        (-29, -23, 65, 82),
        (8, -13, 68, 72),
        (48, 6, 48, 49),
        (-59, 25, 123, 37),
    )
    for offset_x, offset_y, width, height in blocks:
        if outline:
            canvas.rect(center_x + offset_x - 4, center_y + offset_y - 4, width + 8, height + 8, shade)
        else:
            canvas.rect(center_x + offset_x, center_y + offset_y, width, height, shade)


def draw_cloud(canvas: Canvas, frame: int) -> tuple[int, int]:
    float_x = round(math.sin(frame * (2 * math.pi / FRAME_COUNT)) * 9)
    float_y = round(math.sin(frame * (2 * math.pi / FRAME_COUNT) + 0.8) * 4)
    center_x = 405 + float_x
    center_y = 151 + float_y

    draw_cloud_shape(canvas, center_x, center_y, COLOR["cloud_shade"], outline=True)
    draw_cloud_shape(canvas, center_x, center_y, COLOR["cloud"])
    canvas.rect(center_x - 35, center_y + 25, 102, 20, COLOR["lavender"])
    canvas.rect(center_x - 50, center_y + 33, 98, 11, COLOR["cloud_shade"])
    canvas.rect(center_x - 44, center_y - 4, 49, 3, COLOR["cloud_highlight"])
    canvas.rect(center_x - 23, center_y - 17, 35, 3, COLOR["white"])
    canvas.rect(center_x - 72, center_y + 11, 19, 3, COLOR["cloud_highlight"])

    # Tiny face details give the cloud a friendly game-character silhouette.
    canvas.rect(center_x - 21, center_y + 13, 4, 9, COLOR["deep_blue"])
    canvas.rect(center_x + 22, center_y + 13, 4, 9, COLOR["deep_blue"])
    canvas.rect(center_x - 27, center_y + 26, 9, 3, COLOR["blush"])
    canvas.rect(center_x + 18, center_y + 26, 9, 3, COLOR["blush"])
    canvas.rect(center_x - 6, center_y + 30, 4, 3, COLOR["cloud_shade"])
    canvas.rect(center_x - 2, center_y + 33, 8, 3, COLOR["cloud_shade"])
    canvas.rect(center_x + 6, center_y + 30, 4, 3, COLOR["cloud_shade"])
    return center_x, center_y


def draw_raindrop(canvas: Canvas, x: int, y: int, color: int) -> None:
    canvas.rect(x + 2, y, 2, 4, color)
    canvas.rect(x, y + 4, 6, 6, color)
    canvas.rect(x + 1, y + 10, 4, 2, color)
    canvas.rect(x + 1, y + 5, 1, 3, COLOR["rain_glint"])


def draw_rain(canvas: Canvas, frame: int, cloud_x: int, cloud_y: int) -> None:
    offsets = (-92, -63, -32, -3, 26, 56, 84)
    for index, offset_x in enumerate(offsets):
        fall_speed = PIXELS_PER_DROP_STEP + index % 3
        loop_distance = FRAME_COUNT * fall_speed
        stagger = index * loop_distance // len(offsets)
        travel = (frame * fall_speed + stagger) % loop_distance
        x = cloud_x + offset_x + ((index % 2) * 4)
        y = cloud_y + 54 + travel
        if y < 350:
            shade = COLOR["rain"] if index % 3 else COLOR["blue_sparkle"]
            draw_raindrop(canvas, x, y, shade)


def draw_umbrella(canvas: Canvas, center_x: int, top_y: int) -> None:
    # Stepped rows keep the umbrella readable at a reduced profile width.
    canvas.rect(center_x - 5, top_y - 2, 10, 5, COLOR["panel_edge"])
    canvas.rect(center_x - 29, top_y + 2, 58, 6, COLOR["panel_edge"])
    canvas.rect(center_x - 36, top_y + 8, 72, 7, COLOR["panel_edge"])
    canvas.rect(center_x - 31, top_y + 15, 62, 4, COLOR["panel_edge"])
    canvas.rect(center_x - 3, top_y, 6, 5, COLOR["umbrella_light"])
    canvas.rect(center_x - 26, top_y + 3, 52, 5, COLOR["umbrella_light"])
    canvas.rect(center_x - 33, top_y + 9, 66, 5, COLOR["umbrella_shade"])
    canvas.rect(center_x - 26, top_y + 14, 52, 3, COLOR["umbrella_light"])
    canvas.rect(center_x - 19, top_y + 3, 7, 10, COLOR["umbrella_shade"])
    canvas.rect(center_x + 13, top_y + 3, 7, 10, COLOR["umbrella_shade"])
    canvas.rect(center_x, top_y + 16, 3, 12, COLOR["slate"])
    canvas.rect(center_x + 1, top_y + 25, 7, 3, COLOR["slate"])


def draw_player(canvas: Canvas, frame: int) -> None:
    sway = round(math.sin(frame * (2 * math.pi / FRAME_COUNT)) * 18)
    center_x = 402 + sway
    step = (frame // 4) % 2

    draw_umbrella(canvas, center_x, 294)
    head_x = center_x - 7
    canvas.rect(head_x - 2, 322, 18, 13, COLOR["hair"])
    canvas.rect(head_x, 323, 14, 11, COLOR["skin"])
    canvas.rect(head_x - 1, 321, 16, 4, COLOR["hair"])
    canvas.rect(head_x + 2, 327, 2, 2, COLOR["deep_blue"])
    canvas.rect(head_x + 9, 327, 2, 2, COLOR["deep_blue"])
    canvas.rect(head_x + 5, 331, 3, 1, COLOR["jacket"])

    canvas.rect(center_x - 10, 335, 20, 13, COLOR["jacket"])
    canvas.rect(center_x - 14, 337, 5, 9, COLOR["skin"])
    canvas.rect(center_x + 9, 337, 5, 9, COLOR["skin"])
    left_leg_x = center_x - 7 - step * 3
    right_leg_x = center_x + 2 + step * 3
    canvas.rect(left_leg_x, 348, 6, 10, COLOR["slate"])
    canvas.rect(right_leg_x, 348, 6, 10, COLOR["slate"])
    canvas.rect(left_leg_x - 2, 357, 9, 3, COLOR["panel_edge"])
    canvas.rect(right_leg_x, 357, 9, 3, COLOR["panel_edge"])

    if frame % 8 in (0, 1, 2):
        canvas.pixel(center_x - 28, 291, COLOR["white"])
        canvas.pixel(center_x - 30, 293, COLOR["star"])


def draw_panel(canvas: Canvas) -> None:
    canvas.rect(23, 382, 754, 27, COLOR["panel_edge"])
    canvas.rect(25, 384, 750, 23, COLOR["panel"])
    canvas.rect(25, 384, 3, 23, COLOR["umbrella_light"])
    canvas.text(40, 392, "QUEST", COLOR["umbrella_light"])
    canvas.text(83, 392, "CATCH THE SPARKS", COLOR["moonlight"])
    canvas.text(627, 392, "PROGRESS", COLOR["mist"])
    for index in range(5):
        shade = COLOR["rain_glint"] if index < 3 else COLOR["border"]
        canvas.rect(694 + index * 13, 392, 8, 8, shade)


def draw_hud(canvas: Canvas) -> None:
    # Small drop mark and compact status panel frame the animated scene.
    draw_raindrop(canvas, 27, 27, COLOR["rain"])
    canvas.text(49, 25, "RAIN RUNNER", COLOR["cloud_highlight"], scale=2)
    canvas.text(50, 43, "A TINY WEATHER QUEST", COLOR["mist"])
    canvas.rect(627, 20, 149, 43, COLOR["panel_edge"])
    canvas.rect(629, 22, 145, 39, COLOR["panel"])
    canvas.text(641, 29, "STAGE 01", COLOR["umbrella_light"])
    canvas.text(641, 45, "SPARKS 03/05", COLOR["moonlight"])


def render_frame(frame: int) -> Canvas:
    canvas = Canvas(WIDTH, HEIGHT, COLOR["night"])
    draw_background(canvas, frame)
    draw_terrain(canvas, frame)
    cloud_x, cloud_y = draw_cloud(canvas, frame)
    draw_rain(canvas, frame, cloud_x, cloud_y)
    draw_player(canvas, frame)
    draw_hud(canvas)
    draw_panel(canvas)
    return canvas

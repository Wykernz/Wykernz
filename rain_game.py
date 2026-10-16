"""Render the looping rainy-day game GIF and a reduced-motion PNG poster."""

import argparse
from pathlib import Path

from image_export import write_gif, write_png
from scene import render_frame
from theme import FRAME_COUNT


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a looping rainy-day pixel-art game GIF.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("assets/rainy-day-quest.gif"),
        help="GIF output path (default: assets/rainy-day-quest.gif)",
    )
    parser.add_argument(
        "--poster",
        type=Path,
        default=Path("assets/rainy-day-quest.png"),
        help="static poster output path (default: assets/rainy-day-quest.png)",
    )
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    frames = [render_frame(frame_number) for frame_number in range(FRAME_COUNT)]
    write_gif(arguments.output, frames)
    write_png(arguments.poster, frames[0])
    print(f"Created {arguments.output} ({FRAME_COUNT} frames, 800x420).")
    print(f"Created static poster {arguments.poster}.")


if __name__ == "__main__":
    main()

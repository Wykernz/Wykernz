"""Dependency-free GIF and PNG writers for the indexed pixel-art canvas."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

from theme import FRAME_DELAY_CENTISECONDS, GIF_PALETTE_SIZE, HEIGHT, PALETTE, WIDTH

if TYPE_CHECKING:
    from scene import Canvas


def gif_lzw_encode(pixels: bytearray) -> bytes:
    """Encode indexed pixels with GIF's 9-bit LZW codes.

    The dictionary resets before it can outgrow 9-bit codes. That keeps this
    compact encoder easy to audit while still compressing repeated sky pixels.
    """
    clear_code = 1 << 8
    end_code = clear_code + 1
    next_code_limit = 500  # Stay below 512 so every emitted code remains 9 bits.
    output = bytearray()
    bit_buffer = 0
    bit_count = 0

    def emit(code: int) -> None:
        nonlocal bit_buffer, bit_count
        bit_buffer |= code << bit_count
        bit_count += 9
        while bit_count >= 8:
            output.append(bit_buffer & 0xFF)
            bit_buffer >>= 8
            bit_count -= 8

    dictionary: dict[bytes, int] = {bytes([index]): index for index in range(256)}
    next_code = 258
    emit(clear_code)
    if not pixels:
        emit(end_code)
    else:
        prefix = bytes([pixels[0]])
        for pixel_value in pixels[1:]:
            candidate = prefix + bytes([pixel_value])
            if candidate in dictionary:
                prefix = candidate
                continue

            emit(dictionary[prefix])
            if next_code < next_code_limit:
                dictionary[candidate] = next_code
                next_code += 1
            else:
                emit(clear_code)
                dictionary = {bytes([index]): index for index in range(256)}
                next_code = 258
            prefix = bytes([pixel_value])
        emit(dictionary[prefix])
        emit(end_code)

    if bit_count:
        output.append(bit_buffer & 0xFF)
    return bytes(output)


def gif_sub_blocks(data: bytes) -> bytes:
    blocks = bytearray()
    for start in range(0, len(data), 255):
        block = data[start : start + 255]
        blocks.append(len(block))
        blocks.extend(block)
    blocks.append(0)
    return bytes(blocks)


def write_gif(path: Path, frames: Iterable[Canvas]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    palette_bytes = bytearray()
    for red, green, blue in PALETTE:
        palette_bytes.extend((red, green, blue))
    palette_bytes.extend(bytes((GIF_PALETTE_SIZE - len(PALETTE)) * 3))

    with path.open("wb") as image_file:
        image_file.write(b"GIF89a")
        image_file.write(struct.pack("<HHBBB", WIDTH, HEIGHT, 0xF7, 0, 0))
        image_file.write(palette_bytes)
        # NETSCAPE2.0 makes the animation loop forever in GitHub's image view.
        image_file.write(b"!\xFF\x0bNETSCAPE2.0\x03\x01\x00\x00\x00")

        for frame in frames:
            image_file.write(b"!\xF9\x04\x04")
            image_file.write(struct.pack("<H", FRAME_DELAY_CENTISECONDS))
            image_file.write(b"\x00\x00")
            image_file.write(b",")
            image_file.write(struct.pack("<HHHHB", 0, 0, WIDTH, HEIGHT, 0))
            image_file.write(b"\x08")  # LZW minimum code size for a 256-color table.
            image_file.write(gif_sub_blocks(gif_lzw_encode(frame.pixels)))

        image_file.write(b";")


def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    chunk = chunk_type + data
    checksum = zlib.crc32(chunk) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk + struct.pack(">I", checksum)


def write_png(path: Path, canvas: Canvas) -> None:
    """Write an RGB PNG poster without relying on third-party imaging packages."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rgb_palette = [channel for color in PALETTE for channel in color]
    scanlines = bytearray()
    for y in range(canvas.height):
        scanlines.append(0)  # PNG filter type 0: one unfiltered row.
        row_start = y * canvas.width
        for palette_index in canvas.pixels[row_start : row_start + canvas.width]:
            palette_start = palette_index * 3
            scanlines.extend(rgb_palette[palette_start : palette_start + 3])

    header = struct.pack(">IIBBBBB", canvas.width, canvas.height, 8, 2, 0, 0, 0)
    png_data = bytearray(b"\x89PNG\r\n\x1a\n")
    png_data.extend(png_chunk(b"IHDR", header))
    png_data.extend(png_chunk(b"IDAT", zlib.compress(scanlines, level=9)))
    png_data.extend(png_chunk(b"IEND", b""))
    path.write_bytes(png_data)

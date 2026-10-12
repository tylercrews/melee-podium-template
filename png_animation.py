"""Stream lossless RGBA animation without retaining full canvases for every frame."""

from io import BytesIO
import struct
import zlib
from collections.abc import Iterable

from PIL import Image


def _chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def _png_parts(image: Image.Image) -> list[tuple[bytes, bytes]]:
    output = BytesIO()
    image.convert("RGBA").save(output, format="PNG")
    data = output.getvalue()
    parts, position = [], 8
    while position < len(data):
        length = struct.unpack_from(">I", data, position)[0]
        parts.append((data[position + 4:position + 8], data[position + 8:position + 8 + length]))
        position += length + 12
    return parts


def encode_animated_png(first: Image.Image, patches: Iterable[tuple[Image.Image, int]],
                        *, frame_count: int, first_duration: int,
                        offset: tuple[int, int]) -> bytes:
    """Encode a full first frame followed by replacement patches; loop forever.

    SOURCE blending replaces transparent pixels as well as opaque ones, avoiding
    ghosting when a character moves against a translucent portrait background.
    """
    if frame_count < 2 or not 0 < first_duration <= 65535:
        raise ValueError("An animation needs at least two frames with positive durations")
    output = BytesIO()
    output.write(b"\x89PNG\r\n\x1a\n")
    parts = _png_parts(first)
    output.write(_chunk(b"IHDR", next(data for kind, data in parts if kind == b"IHDR")))
    output.write(_chunk(b"acTL", struct.pack(">II", frame_count, 0)))
    output.write(_chunk(b"fcTL", struct.pack(">IIIIIHHBB", 0, *first.size, 0, 0, first_duration, 1000, 0, 0)))
    for kind, data in parts:
        if kind == b"IDAT":
            output.write(_chunk(kind, data))
    sequence, count = 1, 1
    for image, duration in patches:
        if not 0 < duration <= 65535 or offset[0] < 0 or offset[1] < 0 or offset[0] + image.width > first.width or offset[1] + image.height > first.height:
            raise ValueError("Animation patch must fit its canvas and have a valid duration")
        output.write(_chunk(b"fcTL", struct.pack(">IIIIIHHBB", sequence, *image.size, *offset, duration, 1000, 0, 0)))
        sequence += 1
        for kind, data in _png_parts(image):
            if kind == b"IDAT":
                output.write(_chunk(b"fdAT", struct.pack(">I", sequence) + data))
                sequence += 1
        count += 1
    if count != frame_count:
        raise ValueError("Animation frame count does not match its patches")
    output.write(_chunk(b"IEND", b""))
    return output.getvalue()

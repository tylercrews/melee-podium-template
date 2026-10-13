"""Encode looping result GIFs with one stable palette for every frame."""

from collections.abc import Callable, Iterable, Sequence
from io import BytesIO

from PIL import Image, ImageChops


def _rgb_on_matte(image: Image.Image) -> Image.Image:
    # GIF has binary transparency. Keep fully transparent pixels clear and
    # resolve partial alpha against the dark presentation matte before indexing.
    matte = Image.new("RGBA", image.size, "#000000FF")
    matte.alpha_composite(image.convert("RGBA"))
    return matte.convert("RGB")


def encode_animated_gif(frame_at: Callable[[int], Image.Image], durations: Sequence[int],
                        *, palette_samples: Iterable[Image.Image] = ()) -> bytes:
    """Write a GIF while retaining indexed rather than RGBA full-resolution frames.

    A shared palette and deterministic quantization keep the background, names,
    and podiums steady. Transparent GIFs restore the canvas between frames so a
    moving character cannot leave an opaque trail behind it.
    """
    if len(durations) < 2 or any(isinstance(duration, bool) or not isinstance(duration, int)
                                or duration <= 0 or duration % 10 for duration in durations):
        raise ValueError("GIF durations must be positive multiples of 10 ms for at least two frames")
    first = frame_at(0).convert("RGBA")
    sample = _rgb_on_matte(first)
    samples = []
    for image in palette_samples:
        image = _rgb_on_matte(image)
        image.thumbnail((48, 48), Image.Resampling.LANCZOS)
        samples.append(image)
    row_height, columns = 48, max(1, sample.width // 48)
    atlas = Image.new("RGB", (sample.width, sample.height + ((len(samples) + columns - 1) // columns) * row_height), "#000000FF")
    atlas.paste(sample)
    for index, image in enumerate(samples):
        atlas.paste(image, (index % columns * 48, sample.height + index // columns * row_height))
    palette = atlas.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    colors = palette.getpalette()[:765]
    colors.extend([0] * (765 - len(colors)))
    palette.putpalette(colors + [0, 0, 0])
    black = min(range(255), key=lambda index: sum(channel * channel for channel in colors[index * 3:index * 3 + 3]))
    remap = list(range(255)) + [black]
    # Ordered noise is anchored to the canvas. Unlike error diffusion, changes
    # to a clapping hand cannot alter the color of a neighboring static pixel.
    bayer = (0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5)
    noise = Image.new("L", (4, 4))
    noise.putdata([113 + value * 2 for value in bayer])
    pattern = Image.new("L", first.size)
    # Double the tile repeatedly in C-backed image operations instead of making
    # one Python paste call for every four pixels across the full canvas.
    while noise.width < first.width or noise.height < first.height:
        tiled = Image.new("L", (noise.width * 2, noise.height * 2))
        for x, y in ((0, 0), (noise.width, 0), (0, noise.height), noise.size):
            tiled.paste(noise, (x, y))
        noise = tiled
    pattern.paste(noise, (0, 0))
    pattern = pattern.convert("RGB")

    def indexed(image: Image.Image) -> Image.Image:
        if image.size != first.size:
            raise ValueError("GIF frames must match the output canvas")
        rgb = _rgb_on_matte(image)
        result = rgb.quantize(palette=palette, dither=Image.Dither.NONE).point(remap)
        result.putpalette(colors + [0, 0, 0])
        # Keep exact/near-exact vector and text colors crisp. Dither only pixels
        # whose nearest available color would otherwise cause visible banding.
        error = ImageChops.difference(rgb, result.convert("RGB")).convert("L").point(
            [0 if value < 3 else 255 for value in range(256)])
        shifted = ImageChops.add(rgb, pattern, offset=-128)
        softened = shifted.quantize(palette=palette, dither=Image.Dither.NONE).point(remap)
        softened.putpalette(colors + [0, 0, 0])
        result.paste(softened, mask=error)
        transparent = image.getchannel("A").point([255] + [0] * 255)
        result.paste(255, mask=transparent)
        return result

    frames = [indexed(first)]
    frames.extend(indexed(frame_at(index)) for index in range(1, len(durations)))
    output = BytesIO()
    disposal = 2 if first.getchannel("A").getextrema()[0] == 0 else 1
    frames[0].save(output, format="GIF", save_all=True, append_images=frames[1:],
                   duration=list(durations), loop=0, transparency=255, background=255,
                   disposal=disposal, optimize=False)
    return output.getvalue()

// Matches radial_watermark.py: contrast with the divider pixels under the text.
const ray = { x0: 960, y0: 540, x1: 1920, y1: 1080 };
const textLength = 270;
// Singles and Doubles share one position near the corner.
const end = 1050;

function dividerSamples(): [number, number][] {
  const length = Math.hypot(ray.x1 - ray.x0, ray.y1 - ray.y0);
  const rayX = (distance: number) => ray.x0 + (ray.x1 - ray.x0) * distance / length;
  const samples: [number, number][] = [];
  for (let x = Math.floor(rayX(end - textLength)); x <= Math.floor(rayX(end)); x += 1) {
    const y = Math.floor(ray.y0 + (x - ray.x0) * (ray.y1 - ray.y0) / (ray.x1 - ray.x0) + .5);
    for (const offset of [-1, 0, 1]) samples.push([x, y + offset]);
  }
  return samples;
}

export function drawRadialWatermark(context: CanvasRenderingContext2D, mask: HTMLImageElement) {
  const samples = dividerSamples();
  const left = samples[0][0];
  const top = samples[0][1];
  const right = samples[samples.length - 1][0];
  const bottom = samples[samples.length - 1][1];
  const pixels = context.getImageData(left, top, right - left + 1, bottom - top + 1).data;
  const width = right - left + 1;
  let luminance = 0;
  for (const [x, y] of samples) {
    const index = ((y - top) * width + (x - left)) * 4;
    luminance += (.2126 * pixels[index] + .7152 * pixels[index + 1] + .0722 * pixels[index + 2]) / 255 * pixels[index + 3] / 255;
  }
  const layer = document.createElement("canvas");
  layer.width = mask.naturalWidth;
  layer.height = mask.naturalHeight;
  const tint = layer.getContext("2d");
  if (!tint) throw new Error("Canvas preview is unavailable.");
  tint.drawImage(mask, 0, 0);
  tint.globalCompositeOperation = "source-in";
  // The mask already owns the 25% alpha; tint with an opaque color once.
  tint.fillStyle = luminance / samples.length >= .55 ? "#000000FF" : "#FFFFFFFF";
  tint.fillRect(0, 0, layer.width, layer.height);
  context.drawImage(layer, 0, 0);
}

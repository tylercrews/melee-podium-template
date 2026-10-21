// Matches radial_watermark.py: choose contrast from the fully composed image.
const singlesBox = { left: 1450, top: 787, right: 1686, bottom: 933 };
const doublesBox = { left: 1562, top: 1034, right: 1902, bottom: 1062 };

export function drawRadialWatermark(context: CanvasRenderingContext2D, mask: HTMLImageElement, doubles: boolean) {
  const box = doubles ? doublesBox : singlesBox;
  const pixels = context.getImageData(box.left, box.top, box.right - box.left, box.bottom - box.top).data;
  let luminance = 0;
  for (let index = 0; index < pixels.length; index += 4) {
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
  tint.fillStyle = luminance / (pixels.length / 4) >= .55 ? "#000000FF" : "#FFFFFFFF";
  tint.fillRect(0, 0, layer.width, layer.height);
  context.drawImage(layer, 0, 0);
}

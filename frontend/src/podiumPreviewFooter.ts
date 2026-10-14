/** Keep the shared header's footer at the bottom of taller clapping canvases. */
const FOOTER_STRIP_HEIGHT = 45;

export function podiumHeaderWithoutFooter(source: CanvasImageSource, width: number, height: number): HTMLCanvasElement {
  const layer = document.createElement("canvas");
  layer.width = width;
  layer.height = height;
  const context = layer.getContext("2d");
  if (context) {
    context.drawImage(source, 0, 0);
    context.clearRect(0, height - FOOTER_STRIP_HEIGHT, width, FOOTER_STRIP_HEIGHT);
  }
  return layer;
}

export function drawPodiumPreviewFooter(context: CanvasRenderingContext2D, header: HTMLImageElement, output: { width: number; height: number }): void {
  const layer = document.createElement("canvas");
  layer.width = header.naturalWidth;
  layer.height = FOOTER_STRIP_HEIGHT;
  const footer = layer.getContext("2d");
  if (!footer) return;
  footer.drawImage(header, 0, header.naturalHeight - FOOTER_STRIP_HEIGHT, header.naturalWidth, FOOTER_STRIP_HEIGHT,
                   0, 0, header.naturalWidth, FOOTER_STRIP_HEIGHT);
  footer.globalCompositeOperation = "source-in";
  footer.fillStyle = "#FFFFFF40";
  footer.fillRect(0, 0, layer.width, layer.height);
  context.drawImage(layer, 0, output.height - FOOTER_STRIP_HEIGHT, output.width, FOOTER_STRIP_HEIGHT);
}

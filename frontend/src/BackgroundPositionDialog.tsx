import { PointerEvent, useMemo, useRef, useState } from "react";
import { BackgroundPlacement, BackgroundSizeOption, PixelSize, backgroundSizeValue, buildBackgroundPlacement } from "./format";

export interface FormatImageInfo extends PixelSize {
  id: string;
  name: string;
  url: string;
}

interface BackgroundPositionDialogProps {
  image: FormatImageInfo;
  outputSize: PixelSize;
  multiplier: BackgroundSizeOption;
  value: BackgroundPlacement | null;
  onChange: (value: BackgroundPlacement) => void;
}

const clamp = (value: number) => Math.min(1, Math.max(0, value));

export default function BackgroundPositionDialog({ image, outputSize, multiplier, value, onChange }: BackgroundPositionDialogProps) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [alignment, setAlignment] = useState(value?.alignment ?? { x: .5, y: .5 });
  const scale = backgroundSizeValue(multiplier, image, outputSize);
  const scaled = { width: image.width * scale, height: image.height * scale };
  const fitsInside = scaled.width <= outputSize.width && scaled.height <= outputSize.height;
  const workspace = { width: Math.max(scaled.width, outputSize.width), height: Math.max(scaled.height, outputSize.height) };
  const geometry = useMemo(() => {
    const imageLeft = scaled.width <= outputSize.width ? (outputSize.width - scaled.width) * alignment.x : 0;
    const imageTop = scaled.height <= outputSize.height ? (outputSize.height - scaled.height) * alignment.y : 0;
    const viewportLeft = scaled.width > outputSize.width ? (scaled.width - outputSize.width) * alignment.x : 0;
    const viewportTop = scaled.height > outputSize.height ? (scaled.height - outputSize.height) * alignment.y : 0;
    return { imageLeft, imageTop, viewportLeft, viewportTop };
  }, [alignment.x, alignment.y, outputSize.height, outputSize.width, scaled.height, scaled.width]);

  function open() {
    setAlignment(value?.alignment ?? { x: .5, y: .5 });
    dialog.current?.showModal();
  }

  function updateFromPointer(event: PointerEvent<HTMLDivElement>) {
    const bounds = event.currentTarget.getBoundingClientRect();
    const pointX = (event.clientX - bounds.left) / bounds.width * workspace.width;
    const pointY = (event.clientY - bounds.top) / bounds.height * workspace.height;
    const xRange = Math.abs(scaled.width - outputSize.width);
    const yRange = Math.abs(scaled.height - outputSize.height);
    const targetWidth = scaled.width <= outputSize.width ? scaled.width : outputSize.width;
    const targetHeight = scaled.height <= outputSize.height ? scaled.height : outputSize.height;
    setAlignment({
      x: xRange ? clamp((pointX - targetWidth / 2) / xRange) : .5,
      y: yRange ? clamp((pointY - targetHeight / 2) / yRange) : .5,
    });
  }

  const percent = (value: number, total: number) => `${value / total * 100}%`;
  return <>
    <button className="button button--outline" type="button" onClick={open}>Choose position</button>
    <dialog className="modal background-position-modal" ref={dialog} onClick={(event) => { if (event.target === event.currentTarget) event.currentTarget.close(); }}><div className="modal__content"><button className="modal__close" type="button" onClick={() => dialog.current?.close()} aria-label="Close">×</button><span className="eyebrow">Background placement</span><h2>{fitsInside ? "Position the background" : "Choose the visible area"}</h2><p>{fitsInside ? "The scaled background is smaller than the finished image. Drag it to choose where it sits." : "The scaled background extends beyond the finished image. Drag the highlighted output rectangle over the area you want visible."}</p>
      <div className={`background-position-stage${fitsInside ? " is-positioning" : " is-cropping"}`} style={{ aspectRatio: `${workspace.width} / ${workspace.height}` }} onPointerDown={(event) => { event.currentTarget.setPointerCapture(event.pointerId); updateFromPointer(event); }} onPointerMove={(event) => { if (event.currentTarget.hasPointerCapture(event.pointerId)) updateFromPointer(event); }}>
        <img src={image.url} alt="" draggable={false} style={{ left: percent(geometry.imageLeft, workspace.width), top: percent(geometry.imageTop, workspace.height), width: percent(scaled.width, workspace.width), height: percent(scaled.height, workspace.height) }} />
        <div className="background-position-stage__viewport" style={{ left: percent(geometry.viewportLeft, workspace.width), top: percent(geometry.viewportTop, workspace.height), width: percent(outputSize.width, workspace.width), height: percent(outputSize.height, workspace.height) }}><span>{outputSize.width} × {outputSize.height}</span></div>
      </div>
      <div className="background-position-sliders"><label>Horizontal position <span>{Math.round(alignment.x * 100)}%</span><input type="range" min="0" max="100" value={Math.round(alignment.x * 100)} onChange={(event) => setAlignment((current) => ({ ...current, x: Number(event.target.value) / 100 }))} /></label><label>Vertical position <span>{Math.round(alignment.y * 100)}%</span><input type="range" min="0" max="100" value={Math.round(alignment.y * 100)} onChange={(event) => setAlignment((current) => ({ ...current, y: Number(event.target.value) / 100 }))} /></label></div>
      <p className="background-position-summary">{image.name} · {image.width} × {image.height} · {multiplier === "scale_to_width" ? "scaled to width" : multiplier === "scale_to_height" ? "scaled to height" : `set to ${multiplier}×`} ({scale.toFixed(3)}× actual size)</p>
      <div className="modal__actions"><button className="button button--ghost" type="button" onClick={() => dialog.current?.close()}>Cancel</button><button className="button button--dark" type="button" onClick={() => { onChange(buildBackgroundPlacement(image.id, image, outputSize, multiplier, alignment)); dialog.current?.close(); }}>Apply position</button></div>
    </div></dialog>
  </>;
}


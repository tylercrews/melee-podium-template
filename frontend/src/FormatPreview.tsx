import { useEffect, useMemo, useRef, useState } from "react";
import { apiUrl } from "./api";
import { FormatImageInfo } from "./BackgroundPositionDialog";
import { FormatConfiguration, buildBackgroundPlacement, formatCanvasSize, hasValidEntrantCount, sizeMultiplierValue } from "./format";

interface FormatPreviewProps {
  format: FormatConfiguration;
  backgroundImage: FormatImageInfo | null;
  logoImage: FormatImageInfo | null;
}

interface PreviewRequest { url: string; transparentUrl: string; label: string }

function previewRequest(format: FormatConfiguration): PreviewRequest {
  const { selection } = format;
  const style = selection.options.podium_style ?? "legacy";
  const eventFormat = selection.options.event_format ?? "singles";
  const hasEntrantChoice = hasValidEntrantCount(selection);
  const entrantCount = hasEntrantChoice
    ? selection.options.entrant_count as number
    : eventFormat === "doubles" ? 4 : 8;
  const variant = hasEntrantChoice ? selection.options.variant : null;
  const params = new URLSearchParams({
    style,
    event_format: eventFormat,
    entrant_count: String(entrantCount),
  });
  if (variant) params.set("variant", variant);
  const styleLabel = style === "customizable" ? "Customizable" : "Legacy";
  const eventLabel = eventFormat === "doubles" ? "Doubles" : "Singles";
  const layoutLabel = variant === "four_podium" ? "Top 8 – 4 Podiums" : `Top ${entrantCount}`;
  const transparentParams = new URLSearchParams(params);
  transparentParams.set("transparent", "1");
  return {
    url: apiUrl(`format-preview?${params.toString()}`),
    transparentUrl: apiUrl(`format-preview?${transparentParams.toString()}`),
    label: `${styleLabel} · ${eventLabel} · ${layoutLabel}`,
  };
}

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("Could not load a preview asset."));
    image.src = url;
  });
}

async function loadConfiguredForeground(format: FormatConfiguration): Promise<HTMLImageElement> {
  const response = await fetch(apiUrl("format-preview"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      style: format.selection.options.podium_style ?? "legacy",
      event_format: format.selection.options.event_format ?? "singles",
      entrant_count: format.selection.options.entrant_count ?? 8,
      variant: format.selection.options.variant,
      transparent: true,
      formatting_asset_colors: format.formatting_asset_colors,
      header_layout: format.header_layout,
    }),
  });
  if (!response.ok) throw new Error("Could not render the configured format preview.");
  const objectUrl = URL.createObjectURL(await response.blob());
  try {
    return await loadImage(objectUrl);
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

export default function FormatPreview({ format, backgroundImage, logoImage }: FormatPreviewProps) {
  const request = useMemo(() => previewRequest(format), [format]);
  const [displayed, setDisplayed] = useState(request);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [failed, setFailed] = useState(false);
  const [refreshedSignature, setRefreshedSignature] = useState<string | null>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const expandedDialog = useRef<HTMLDialogElement>(null);
  const expandedImage = useRef<HTMLImageElement>(null);
  const expandedCanvas = useRef<HTMLCanvasElement>(null);
  const previewSignature = JSON.stringify({
    structuralPreview: request.transparentUrl,
    format,
    backgroundId: backgroundImage?.id ?? null,
    backgroundUrl: backgroundImage?.url ?? null,
    logoId: logoImage?.id ?? null,
    logoUrl: logoImage?.url ?? null,
  });
  const customPreviewVisible = refreshedSignature !== null;
  const needsRefresh = refreshedSignature !== previewSignature;
  const customPreviewStale = customPreviewVisible && needsRefresh;

  useEffect(() => {
    if (request.url === displayed.url) return;
    let cancelled = false;
    setRefreshedSignature(null);
    setLoading(true);
    setFailed(false);
    const timeout = window.setTimeout(() => {
      const nextImage = new Image();
      nextImage.onload = () => { if (!cancelled) { setDisplayed(request); setLoading(false); } };
      nextImage.onerror = () => { if (!cancelled) { setFailed(true); setLoading(false); } };
      nextImage.src = request.url;
    }, 180);
    return () => { cancelled = true; window.clearTimeout(timeout); };
  }, [displayed.url, request]);

  async function refreshWithSelectedImages() {
    const outputSize = formatCanvasSize(format);
    const target = canvas.current;
    if (!outputSize || !target) return;
    setRefreshing(true);
    setFailed(false);
    try {
      const [foreground, background, logo] = await Promise.all([
        loadConfiguredForeground(format),
        backgroundImage ? loadImage(backgroundImage.url) : Promise.resolve(null),
        logoImage ? loadImage(logoImage.url) : Promise.resolve(null),
      ]);
      target.width = outputSize.width;
      target.height = outputSize.height;
      const context = target.getContext("2d");
      if (!context) throw new Error("Canvas preview is unavailable.");
      context.clearRect(0, 0, target.width, target.height);
      context.fillStyle = format.image_settings.background_color;
      context.fillRect(0, 0, target.width, target.height);

      if (background && backgroundImage) {
        const savedPlacement = format.image_settings.background_placement;
        const placement = savedPlacement?.asset_id === backgroundImage.id
          ? savedPlacement
          : buildBackgroundPlacement(
              backgroundImage.id,
              backgroundImage,
              outputSize,
              format.image_settings.background_size,
            );
        const source = placement.source_crop;
        const destination = placement.destination;
        context.drawImage(
          background,
          source.left,
          source.top,
          source.right - source.left,
          source.bottom - source.top,
          destination.left,
          destination.top,
          destination.right - destination.left,
          destination.bottom - destination.top,
        );
      }

      context.drawImage(foreground, 0, 0, target.width, target.height);
      if (logo && logoImage) {
        const scale = sizeMultiplierValue(format.image_settings.logo_size);
        const width = logoImage.width * scale;
        const height = logoImage.height * scale;
        const position = Object.entries(format.header_layout).find(([, content]) => content === "tournament_logo")?.[0] ?? "top_left";
        const left = position === "top_middle"
          ? (target.width - width) / 2
          : position === "top_right" ? target.width - width - 20 : 20;
        context.drawImage(logo, left, 20, width, height);
      }
      setRefreshedSignature(previewSignature);
    } catch {
      setFailed(true);
    } finally {
      setRefreshing(false);
    }
  }

  function openExpandedPreview() {
    if (!expandedImage.current || !expandedCanvas.current) return;
    if (customPreviewVisible && canvas.current) {
      expandedCanvas.current.width = canvas.current.width;
      expandedCanvas.current.height = canvas.current.height;
      expandedCanvas.current.getContext("2d")?.drawImage(canvas.current, 0, 0);
      expandedCanvas.current.hidden = false;
      expandedImage.current.hidden = true;
    } else {
      expandedImage.current.src = displayed.url;
      expandedImage.current.hidden = false;
      expandedCanvas.current.hidden = true;
    }
    expandedDialog.current?.showModal();
  }

  return <div className="format-preview">
    <button className="format-preview__frame" type="button" onClick={openExpandedPreview} aria-label="Open a larger format preview"><img className="format-preview__demo" src={displayed.url} alt={`Cached demo podium: ${displayed.label}`} hidden={customPreviewVisible} /><canvas className="format-preview__canvas" ref={canvas} hidden={!customPreviewVisible} aria-label={`Format preview using your selected images: ${request.label}`} />{loading && <span className="format-preview__loading">Updating layout…</span>}{customPreviewStale && <span className="format-preview__loading">Image changes need refresh</span>}</button>
    <button className={`button button--outline format-preview__refresh${needsRefresh ? " format-preview__refresh--needed" : ""}`} type="button" onClick={() => void refreshWithSelectedImages()} disabled={refreshing} aria-label={needsRefresh ? "Refresh Format Preview; changes are waiting" : "Refresh Format Preview; preview is up to date"}><span>{refreshing ? "Refreshing preview…" : "Refresh Format Preview"}</span>{needsRefresh && !refreshing && <span className="format-preview__refresh-status">Changes waiting</span>}</button>
    <p><strong>{customPreviewVisible ? "Your image preview" : "Cached layout demo"}</strong> · {request.label}</p>
    {failed && <span className="format-preview__waiting" role="alert">The new preview could not be rendered. The previous preview is still shown.</span>}
    <dialog className="modal format-preview-modal" ref={expandedDialog} onClick={(event) => { if (event.target === event.currentTarget) event.currentTarget.close(); }}><div className="modal__content"><button className="modal__close" type="button" onClick={() => expandedDialog.current?.close()} aria-label="Close enlarged preview">×</button><img className="format-preview-modal__image" ref={expandedImage} alt={`Enlarged format preview: ${request.label}`} /><canvas className="format-preview-modal__image" ref={expandedCanvas} hidden aria-label={`Enlarged customized format preview: ${request.label}`} /></div></dialog>
  </div>;
}

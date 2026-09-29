import { useEffect, useMemo, useRef, useState } from "react";
import { apiUrl, recordDownload } from "./api";
import { FormatImageInfo } from "./BackgroundPositionDialog";
import { EntrantDraft, TournamentDetails } from "./creationData";
import { FavoriteCharacter } from "./favorites";
import { FormatConfiguration, PixelSize, buildBackgroundPlacement, formatCanvasSize, sizeMultiplierValue } from "./format";

interface FormatPreviewProps {
  format: FormatConfiguration;
  backgroundImage: FormatImageInfo | null;
  logoImage: FormatImageInfo | null;
  fontAsset: FormatFontInfo | null;
  tournament: TournamentDetails;
  entrants: EntrantDraft[];
  tournamentComplete: boolean;
  entrantsComplete: boolean;
}

export interface FormatFontInfo { id: string; name: string; url: string; custom: boolean }

interface LayerRequest {
  foregroundLayers: Array<{ url: string }>;
  headerUrl: string;
  label: string;
  logoPosition: "top_left" | "top_middle" | "top_right";
  logoBox: { left: number; top: number; right: number; bottom: number };
  outputSize: PixelSize;
}

const imageCache = new Map<string, Promise<HTMLImageElement>>();
const layerRoot = `${import.meta.env.BASE_URL}format_preview_layers`;

function loadImage(url: string): Promise<HTMLImageElement> {
  const cached = imageCache.get(url);
  if (cached) return cached;
  const loading = new Promise<HTMLImageElement>((resolve, reject) => {
    const image = new Image();
    image.crossOrigin = "anonymous";
    image.onload = () => resolve(image);
    image.onerror = () => { imageCache.delete(url); reject(new Error("Could not load a preview asset.")); };
    image.src = url;
  });
  imageCache.set(url, loading);
  return loading;
}

function layoutId(format: FormatConfiguration): string {
  if (format.selection.options.variant === "four_podium") return "top_8_four_podiums";
  const entrantCount = format.selection.options.entrant_count
    ?? (format.selection.options.event_format === "doubles" ? 3 : 8);
  return entrantCount === 3 ? "top_3" : entrantCount === 4 ? "top_4" : "top_8";
}

function headerPermutationId(format: FormatConfiguration): string {
  const aliases = { tournament_logo: "logo", tournament_title: "title", metadata: "metadata" } as const;
  return (["top_left", "top_middle", "top_right"] as const).map((position) => aliases[format.header_layout[position]]).join("-");
}

function headerBox(format: FormatConfiguration, outputSize: PixelSize, position: LayerRequest["logoPosition"]): LayerRequest["logoBox"] {
  if (format.selection.mode === "eyes") {
    const index = position === "top_left" ? 0 : position === "top_middle" ? 1 : 2;
    if (outputSize.width === 1080) {
      const top = 20;
      const sectionHeight = Math.floor((1900 - top) / 3);
      return {
        left: 858,
        top: top + index * sectionHeight + 8,
        right: 1052,
        bottom: top + (index + 1) * sectionHeight - 8,
      };
    }
    const left = 40;
    const right = outputSize.width - 40;
    const gap = 24;
    const sectionWidth = Math.floor((right - left - gap * 2) / 3);
    const sectionLeft = left + index * (sectionWidth + gap);
    return {
      left: sectionLeft,
      top: 30,
      right: index === 2 ? right : sectionLeft + sectionWidth,
      bottom: 225,
    };
  }
  if (format.selection.mode !== "squares") {
    const third = outputSize.width / 3;
    const index = position === "top_left" ? 0 : position === "top_middle" ? 1 : 2;
    return { left: third * index, top: 0, right: third * (index + 1), bottom: 180 };
  }
  const left = 40;
  const right = 1880;
  const gap = 24;
  const availableWidth = right - left - gap * 2;
  const doubles = format.selection.options.event_format === "doubles";
  const sideWidth = doubles ? Math.round(availableWidth * .4) : Math.floor(availableWidth / 3);
  const middleWidth = availableWidth - sideWidth * 2;
  const middleLeft = left + sideWidth + gap;
  const rightLeft = middleLeft + middleWidth + gap;
  if (position === "top_left") return { left, top: 888, right: left + sideWidth, bottom: 1070 };
  if (position === "top_middle") return { left: middleLeft, top: 888, right: middleLeft + middleWidth, bottom: 1070 };
  return { left: rightLeft, top: 888, right, bottom: 1070 };
}

function layerRequest(format: FormatConfiguration, fontAsset: FormatFontInfo | null): LayerRequest {
  const mode = format.selection.mode;
  const style = format.selection.options.podium_style ?? "legacy";
  const eventFormat = format.selection.options.event_format ?? "singles";
  const layout = layoutId(format);
  const outputSize = formatCanvasSize(format) ?? (
    style === "customizable" ? { width: 1920, height: 941 } : { width: 1672, height: 941 }
  );
  const selectedFontId = fontAsset?.id.replace("provided:", "") ?? "tyrowo";
  const fontId = fontAsset?.custom
    ? "ubuntu"
    : ["tyrowo", "impact", "ubuntu"].includes(selectedFontId) ? selectedFontId : "tyrowo";
  const logoPosition = (Object.entries(format.header_layout).find(([, content]) => content === "tournament_logo")?.[0] ?? "top_left") as LayerRequest["logoPosition"];
  const colors = format.formatting_asset_colors;
  let foregroundLayers: LayerRequest["foregroundLayers"];
  let headerUrl: string;
  if (mode === "eyes") {
    const eyeEntrantCount = format.selection.options.entrant_count
      ?? (eventFormat === "doubles" ? 3 : 8);
    const eyeLayout = `${eventFormat}_top_${eyeEntrantCount}`;
    const colorId = colors.mode === "premade" ? colors.preset ?? "smash_player_colors" : "pick_all";
    foregroundLayers = [{ url: `${layerRoot}/eyes/${eyeLayout}/${colorId}.png` }];
    headerUrl = `${layerRoot}/eye_headers/${fontId}/${eyeLayout}/${headerPermutationId(format)}.png`;
  } else if (mode === "squares") {
    const squareLayout = `${eventFormat}_${layout}`;
    const colorId = colors.mode === "premade" ? colors.preset ?? "smash_player_colors" : "pick_all";
    foregroundLayers = [{ url: `${layerRoot}/squares/${squareLayout}/${colorId}.png` }];
    headerUrl = `${layerRoot}/square_headers/${fontId}/${eventFormat}/${headerPermutationId(format)}.png`;
  } else if (style === "customizable") {
    const colorId = colors.mode === "premade" ? colors.preset ?? "smash_player_colors" : "custom_red";
    foregroundLayers = [{ url: `${layerRoot}/podiums/customizable/${layout}/${colorId}.png` }];
    headerUrl = `${layerRoot}/headers/${fontId}/${headerPermutationId(format)}.png`;
  } else {
    foregroundLayers = [{ url: `${layerRoot}/podiums/legacy/${layout}.png` }];
    headerUrl = `${layerRoot}/headers/${fontId}/${headerPermutationId(format)}.png`;
  }
  const styleLabel = mode === "eyes" ? "Eyes" : mode === "squares" ? "Squares" : style === "customizable" ? "Customizable" : "Legacy";
  const eventLabel = eventFormat === "doubles" ? "Doubles" : "Singles";
  const layoutLabel = format.selection.options.variant === "four_podium"
    ? "Top 8 – 4 Podiums"
    : `Top ${format.selection.options.entrant_count ?? 8}`;
  return {
    foregroundLayers,
    headerUrl,
    label: `${styleLabel} · ${eventLabel} · ${layoutLabel}`,
    logoPosition,
    logoBox: headerBox(format, outputSize, logoPosition),
    outputSize,
  };
}

function previewCharacter(character: FavoriteCharacter) {
  return {
    melee_fighter_name: character.fighter,
    color: character.color || null,
    pose: character.pose || null,
    mirror_horizontally: character.mirrorHorizontally,
  };
}

function previewEntrants(entrants: EntrantDraft[], entrantCount: number, includeSeeding: boolean) {
  return entrants.slice(0, entrantCount).map((entrant) => entrant.kind === "singles" ? {
    tag: entrant.tag.trim(),
    seed: includeSeeding && entrant.seed ? Number(entrant.seed) : null,
    placement: entrant.placement,
    characters: entrant.characters.map(previewCharacter),
  } : {
    team_name: entrant.teamName.trim(),
    seed: includeSeeding && entrant.seed ? Number(entrant.seed) : null,
    placement: entrant.placement,
    team_color: entrant.teamColor || null,
    entrant_1: { tag: entrant.entrant1.tag.trim(), characters: entrant.entrant1.characters.map(previewCharacter) },
    entrant_2: { tag: entrant.entrant2.tag.trim(), characters: entrant.entrant2.characters.map(previewCharacter) },
  });
}

async function loadConfiguredForeground(format: FormatConfiguration, fontAsset: FormatFontInfo | null, tournament: TournamentDetails, entrants: EntrantDraft[], tournamentComplete: boolean, entrantsComplete: boolean): Promise<HTMLImageElement> {
  const entrantCount = format.selection.options.entrant_count ?? 8;
  const config = {
    mode: format.selection.mode,
    style: format.selection.options.podium_style ?? "legacy",
    event_format: format.selection.options.event_format ?? "singles",
    entrant_count: entrantCount,
    variant: format.selection.options.variant,
    transparent: true,
    formatting_asset_colors: format.formatting_asset_colors,
    entrant_text_colors: format.entrant_text_colors,
    header_layout: format.header_layout,
    text_settings: format.text_settings,
    tournament: tournamentComplete ? {
      title: tournament.title.trim(),
      subtitle: tournament.subtitle.trim() || null,
      event: tournament.event.trim() || null,
      date: tournament.date || null,
      entrants_count: Number(tournament.entrantsCount) || null,
      link: tournament.tournamentLink.trim() || null,
      location: tournament.location.trim() || null,
      stream_link: tournament.streamLink.trim() || null,
      vod_link: tournament.vodLink.trim() || null,
      organizer_x_account: tournament.toXAccount.trim() || null,
      organizer_twitch_account: tournament.toTwitchAccount.trim() || null,
      organizer_bluesky_account: tournament.toBlueskyAccount.trim() || null,
    } : undefined,
    entrants: entrantsComplete ? previewEntrants(entrants, entrantCount, format.text_settings.include_seeding) : undefined,
  };
  let init: RequestInit;
  if (fontAsset?.custom) {
    const fontResponse = await fetch(fontAsset.url);
    if (!fontResponse.ok) throw new Error("Could not load the selected custom font.");
    const form = new FormData();
    form.append("config", JSON.stringify(config));
    form.append("font_file", await fontResponse.blob(), fontAsset.name);
    init = { method: "POST", body: form };
  } else {
    init = { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(config) };
  }
  const response = await fetch(apiUrl("format-preview"), init);
  if (!response.ok) throw new Error("Could not render the configured format preview.");
  const objectUrl = URL.createObjectURL(await response.blob());
  try {
    return await new Promise<HTMLImageElement>((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error("Could not decode the configured preview."));
      image.src = objectUrl;
    });
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

function drawBackground(context: CanvasRenderingContext2D, format: FormatConfiguration, outputSize: PixelSize, background: HTMLImageElement | null, backgroundImage: FormatImageInfo | null) {
  context.clearRect(0, 0, outputSize.width, outputSize.height);
  context.fillStyle = format.image_settings.background_color;
  context.fillRect(0, 0, outputSize.width, outputSize.height);
  if (!background || !backgroundImage) return;
  const savedPlacement = format.image_settings.background_placement;
  const placement = savedPlacement?.asset_id === backgroundImage.id
    ? savedPlacement
    : buildBackgroundPlacement(backgroundImage.id, backgroundImage, outputSize, format.image_settings.background_size);
  const source = placement.source_crop;
  const destination = placement.destination;
  context.drawImage(background, source.left, source.top, source.right - source.left, source.bottom - source.top, destination.left, destination.top, destination.right - destination.left, destination.bottom - destination.top);
}

function drawLogo(context: CanvasRenderingContext2D, format: FormatConfiguration, logo: HTMLImageElement | null, logoImage: FormatImageInfo | null, outputSize: PixelSize, position: LayerRequest["logoPosition"], box: LayerRequest["logoBox"]) {
  if (!logo || !logoImage) return;
  const scale = sizeMultiplierValue(format.image_settings.logo_size);
  const width = logoImage.width * scale;
  const height = logoImage.height * scale;
  if (format.selection.mode === "eyes" && outputSize.width === 1080) {
    context.save();
    context.translate((box.left + box.right) / 2, (box.top + box.bottom) / 2);
    context.rotate(Math.PI / 2);
    context.drawImage(logo, -width / 2, -height / 2, width, height);
    context.restore();
  } else if (format.selection.mode === "squares" || format.selection.mode === "eyes") {
    context.drawImage(logo, box.left + (box.right - box.left - width) / 2, box.top + (box.bottom - box.top - height) / 2, width, height);
  } else {
    const left = position === "top_middle" ? (outputSize.width - width) / 2 : position === "top_right" ? outputSize.width - width - 20 : 20;
    context.drawImage(logo, left, 20, width, height);
  }
}

function headerWithoutPlaceholder(header: HTMLImageElement, logoBox: LayerRequest["logoBox"]): HTMLCanvasElement {
  const layer = document.createElement("canvas");
  layer.width = header.naturalWidth;
  layer.height = header.naturalHeight;
  const context = layer.getContext("2d");
  if (!context) return layer;
  context.drawImage(header, 0, 0);
  context.clearRect(logoBox.left, logoBox.top, logoBox.right - logoBox.left, logoBox.bottom - logoBox.top);
  return layer;
}

function tintedHeader(header: CanvasImageSource, width: number, height: number, color: string, metallic: boolean): HTMLCanvasElement {
  const layer = document.createElement("canvas");
  layer.width = width;
  layer.height = height;
  const context = layer.getContext("2d");
  if (!context) return layer;
  context.drawImage(header, 0, 0, width, height);
  context.globalCompositeOperation = "source-in";
  if (metallic) {
    const red = Number.parseInt(color.slice(1, 3), 16);
    const green = Number.parseInt(color.slice(3, 5), 16);
    const blue = Number.parseInt(color.slice(5, 7), 16);
    const alpha = Number.parseInt(color.slice(7, 9), 16) / 255;
    const highlight = `rgba(${Math.round(red + (255 - red) * .32)}, ${Math.round(green + (255 - green) * .32)}, ${Math.round(blue + (255 - blue) * .32)}, ${alpha})`;
    const gradient = context.createLinearGradient(0, height, width, 0);
    gradient.addColorStop(0, color);
    gradient.addColorStop(.43, color);
    gradient.addColorStop(.52, highlight);
    gradient.addColorStop(.61, color);
    gradient.addColorStop(1, color);
    context.fillStyle = gradient;
  } else {
    context.fillStyle = color;
  }
  context.fillRect(0, 0, width, height);
  return layer;
}

function canvasPng(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error("Could not create the full-resolution PNG.")), "image/png"));
}

function downloadName(title: string): string {
  const safeTitle = title.trim().replace(/[^a-z0-9]+/gi, "-").replace(/^-+|-+$/g, "").toLowerCase();
  return `${safeTitle || "melee-podium"}.png`;
}

export default function LayeredFormatPreview({ format, backgroundImage, logoImage, fontAsset, tournament, entrants, tournamentComplete, entrantsComplete }: FormatPreviewProps) {
  const request = useMemo(() => layerRequest(format, fontAsset), [format, fontAsset]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [failed, setFailed] = useState(false);
  const [exactPreview, setExactPreview] = useState(false);
  const [refreshedSignature, setRefreshedSignature] = useState<string | null>(null);
  const renderInFlight = useRef(false);
  const canvas = useRef<HTMLCanvasElement>(null);
  const expandedDialog = useRef<HTMLDialogElement>(null);
  const expandedCanvas = useRef<HTMLCanvasElement>(null);
  const previewSignature = JSON.stringify({ format, backgroundId: backgroundImage?.id ?? null, backgroundUrl: backgroundImage?.url ?? null, logoId: logoImage?.id ?? null, logoUrl: logoImage?.url ?? null, fontId: fontAsset?.id ?? null, tournament: tournamentComplete ? tournament : null, entrants: entrantsComplete ? entrants.slice(0, format.selection.options.entrant_count ?? 0) : null });
  const needsRefresh = refreshedSignature !== previewSignature;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setFailed(false);
    setExactPreview(false);
    setRefreshedSignature(null);
    const timeout = window.setTimeout(async () => {
      try {
        const [foregrounds, header, background, logo] = await Promise.all([
          Promise.all(request.foregroundLayers.map(async (layer) => ({ ...layer, image: await loadImage(layer.url) }))),
          loadImage(request.headerUrl),
          backgroundImage ? loadImage(backgroundImage.url) : Promise.resolve(null),
          logoImage ? loadImage(logoImage.url) : Promise.resolve(null),
        ]);
        if (cancelled || !canvas.current) return;
        const target = canvas.current;
        target.width = request.outputSize.width;
        target.height = request.outputSize.height;
        const context = target.getContext("2d");
        if (!context) throw new Error("Canvas preview is unavailable.");
        drawBackground(context, format, request.outputSize, background, backgroundImage);
        for (const foreground of foregrounds) {
          context.drawImage(foreground.image, 0, 0, request.outputSize.width, request.outputSize.height);
        }
        const headerLayer = logo ? headerWithoutPlaceholder(header, request.logoBox) : header;
        context.drawImage(tintedHeader(headerLayer, request.outputSize.width, request.outputSize.height, format.text_settings.heading_color, format.text_settings.heading_metallic), 0, 0);
        drawLogo(context, format, logo, logoImage, request.outputSize, request.logoPosition, request.logoBox);
        setLoading(false);
      } catch {
        if (!cancelled) { setFailed(true); setLoading(false); }
      }
    }, 80);
    return () => { cancelled = true; window.clearTimeout(timeout); };
  }, [backgroundImage, format, logoImage, request]);

  async function refreshWithSelectedImages(download = false) {
    if (renderInFlight.current) return;
    const target = canvas.current;
    if (!target) return;
    renderInFlight.current = true;
    setRefreshing(true);
    setFailed(false);
    try {
      const [foreground, background, logo] = await Promise.all([
        loadConfiguredForeground(format, fontAsset, tournament, entrants, tournamentComplete, entrantsComplete),
        backgroundImage ? loadImage(backgroundImage.url) : Promise.resolve(null),
        logoImage ? loadImage(logoImage.url) : Promise.resolve(null),
      ]);
      target.width = request.outputSize.width;
      target.height = request.outputSize.height;
      const context = target.getContext("2d");
      if (!context) throw new Error("Canvas preview is unavailable.");
      drawBackground(context, format, request.outputSize, background, backgroundImage);
      context.drawImage(foreground, 0, 0, request.outputSize.width, request.outputSize.height);
      drawLogo(context, format, logo, logoImage, request.outputSize, request.logoPosition, request.logoBox);
      setExactPreview(true);
      setRefreshedSignature(previewSignature);
      if (download) {
        const blob = await canvasPng(target);
        const downloadUrl = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = downloadUrl;
        link.download = downloadName(tournament.title);
        link.click();
        window.setTimeout(() => URL.revokeObjectURL(downloadUrl), 1_000);
        const stats = await recordDownload();
        window.dispatchEvent(new CustomEvent<number>("render-count:updated", { detail: stats.render_count }));
      }
    } catch {
      setFailed(true);
    } finally {
      renderInFlight.current = false;
      setRefreshing(false);
    }
  }

  useEffect(() => {
    const handleRefreshRequest = () => void refreshWithSelectedImages();
    window.addEventListener("format-preview:refresh", handleRefreshRequest);
    return () => window.removeEventListener("format-preview:refresh", handleRefreshRequest);
  });

  useEffect(() => {
    const handleDownloadRequest = () => void refreshWithSelectedImages(true);
    window.addEventListener("format-preview:download", handleDownloadRequest);
    return () => window.removeEventListener("format-preview:download", handleDownloadRequest);
  });

  function openExpandedPreview() {
    if (!expandedCanvas.current || !canvas.current) return;
    expandedCanvas.current.width = canvas.current.width;
    expandedCanvas.current.height = canvas.current.height;
    expandedCanvas.current.getContext("2d")?.drawImage(canvas.current, 0, 0);
    expandedDialog.current?.showModal();
  }

  return <div className="format-preview">
    <button className="format-preview__frame" type="button" onClick={openExpandedPreview} aria-label="Open a larger format preview" style={{ aspectRatio: `${request.outputSize.width} / ${request.outputSize.height}` }}><canvas className="format-preview__canvas" ref={canvas} width={request.outputSize.width} height={request.outputSize.height} aria-label={`Layered format preview: ${request.label}`} />{loading && <span className="format-preview__loading">Updating layers…</span>}</button>
    <button className={`button button--outline format-preview__refresh${needsRefresh ? " format-preview__refresh--needed" : ""}`} type="button" onClick={() => void refreshWithSelectedImages()} disabled={refreshing} aria-label={needsRefresh ? "Refresh Format Preview; exact render is available" : "Refresh Format Preview; preview is up to date"}><span>{refreshing ? "Refreshing preview…" : "Refresh Format Preview"}</span>{needsRefresh && !refreshing && <span className="format-preview__refresh-status">Exact render available</span>}</button>
    <p><strong>{exactPreview ? "Exact entrant preview" : "Fast layered preview"}</strong> · {request.label}</p>
    {failed && <span className="format-preview__waiting" role="alert">The preview could not be updated. The previous preview is still shown.</span>}
    <dialog className="modal format-preview-modal" ref={expandedDialog} onClick={(event) => { if (event.target === event.currentTarget) event.currentTarget.close(); }}><div className="modal__content"><button className="modal__close" type="button" onClick={() => expandedDialog.current?.close()} aria-label="Close enlarged preview">×</button><canvas className="format-preview-modal__image" ref={expandedCanvas} width={request.outputSize.width} height={request.outputSize.height} aria-label={`Enlarged format preview: ${request.label}`} /></div></dialog>
  </div>;
}

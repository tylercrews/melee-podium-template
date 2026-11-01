import { useEffect, useMemo, useRef, useState } from "react";
import { apiUrl, recordDownload } from "./api";
import { previewDownloadName } from "./previewDownload";
import { drawRadialWatermark } from "./radialWatermark";
import { dataUrlBlob, exactPreviewKeys, layersWithLogo, replaceHeaderLayers } from "./exactPreviewLayers";
import { flyingVHeaderGeometryId, flyingVLayoutId, isFlyingVVerticallyReversed } from "./flyingVFormat";
import { drawPodiumPreviewFooter, podiumHeaderWithoutFooter } from "./podiumPreviewFooter";
import { placementNumberPreviewPath } from "./placementNumbering";
import { clappingGridLayout, clappingGridVariant } from "./clappingGrid";
import { isPrLayout } from "./layoutTextDefaults";
import { FormatImageInfo } from "./BackgroundPositionDialog";
import { EntrantDraft, TournamentDetails } from "./creationData";
import { FavoriteCharacter } from "./favorites";
import { FormatConfiguration, PixelSize, buildBackgroundPlacement, fixedEntrantCount, formatCanvasSize, sizeMultiplierValue, isPodiumsClapping } from "./format";

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
  logoPlaceholderUrl?: string;
  resultLabelsUrl?: string;
  watermarkUrl?: string;
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
  const grid = clappingGridLayout(format.selection);
  if (grid) return `singles_top_${grid.entrant_count}_${clappingGridVariant(grid.columns)}`;
  if (isPodiumsClapping(format.selection) && format.selection.options.entrant_count === 16) return "singles_top_16_clapping";
  if (isPodiumsClapping(format.selection) && format.selection.options.event_format === "doubles") return "doubles_top_8_four_podium";
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
  if (format.selection.mode === "radial") {
    return {
      top_left: { left: 690, top: 532, right: 1230, bottom: 668 },
      top_middle: { left: 735, top: 345, right: 1185, bottom: 750 },
      top_right: { left: 705, top: 675, right: 1215, bottom: 900 },
    }[position];
  }
  if (format.selection.mode === "flying_v") {
    // Matches the header boxes in generate_flying_v_preferences.py.
    if (isFlyingVVerticallyReversed(format.selection)) return {
      top_left: { left: 16, top: 16, right: 396, bottom: 308 },
      top_middle: { left: 420, top: 1716, right: 1020, bottom: 1872 },
      top_right: { left: 1044, top: 16, right: 1424, bottom: 308 },
    }[position];
    return (format.selection.options.event_format === "doubles" ? {
      top_left: { left: 16, top: 800, right: 456, bottom: 1064 },
      top_middle: { left: 880, top: 48, right: 1480, bottom: 230 },
      top_right: { left: 1904, top: 800, right: 2344, bottom: 1064 },
    } : {
      top_left: { left: 16, top: 1612, right: 396, bottom: 1904 },
      top_middle: { left: 420, top: 48, right: 1020, bottom: 246 },
      top_right: { left: 1044, top: 1612, right: 1424, bottom: 1904 },
    })[position];
  }
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
  if (mode === "radial") {
    const colorId = colors.mode === "premade" ? colors.preset ?? "smash_player_colors" : "pick_all";
    foregroundLayers = [{ url: `${layerRoot}/radial/${eventFormat === "doubles" ? "doubles_top_4" : "singles_top_8"}/${colorId}.png` }];
    headerUrl = `${layerRoot}/radial_headers/${fontId}/${eventFormat === "doubles" ? "doubles/" : ""}${headerPermutationId(format)}.png`;
  } else if (mode === "flying_v") {
    foregroundLayers = [{ url: `${layerRoot}/flying_v/${flyingVLayoutId(format.selection)}/placeholders.png` }];
    headerUrl = `${layerRoot}/flying_v_headers/${fontId}/${flyingVHeaderGeometryId(format.selection)}/${headerPermutationId(format)}.png`;
  } else if (mode === "eyes") {
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
    headerUrl = `${layerRoot}/headers/${isPrLayout(format.selection) ? "pr/" : ""}${fontId}/${headerPermutationId(format)}.png`;
  } else {
    foregroundLayers = [{ url: `${layerRoot}/podiums/legacy/${layout}.png` }];
    headerUrl = `${layerRoot}/headers/${fontId}/${headerPermutationId(format)}.png`;
  }
  const styleLabel = mode === "flying_v" ? (isFlyingVVerticallyReversed(format.selection) ? "Flying V (Reversed)" : "Flying V") : mode === "radial" ? "Radial" : mode === "eyes" ? "Eyes" : mode === "squares" ? "Squares" : style === "customizable" ? "Customizable" : "Legacy";
  const eventLabel = eventFormat === "doubles" ? "Doubles" : "Singles";
  const layoutLabel = isPodiumsClapping(format.selection)
    ? `Podiums+Clapping · Top ${format.selection.options.entrant_count}`
    : `Top ${format.selection.options.entrant_count ?? fixedEntrantCount(mode, eventFormat) ?? 8}`;
  return {
    foregroundLayers,
    headerUrl,
    logoPlaceholderUrl: mode === "radial" ? `${layerRoot}/radial_logos/${logoPosition}.png` : undefined,
    resultLabelsUrl: `${layerRoot}/${placementNumberPreviewPath(format)}`,
    watermarkUrl: mode === "radial" ? `${layerRoot}/radial_watermark${eventFormat === "doubles" ? "_doubles" : ""}.png` : undefined,
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
    omit_entrant: entrant.omitEntrant === true,
    omit_placement: entrant.omitPlacement === true,
    tag: entrant.tag.trim(),
    name_font_size_adjustment: entrant.nameFontSizeAdjustment ?? 0,
    seed: includeSeeding && entrant.seed ? Number(entrant.seed) : null,
    placement: entrant.placement,
    characters: entrant.characters.map(previewCharacter),
  } : {
    omit_entrant: entrant.omitEntrant === true,
    omit_placement: entrant.omitPlacement === true,
    team_name: entrant.teamName.trim(),
    team_name_font_size_adjustment: entrant.teamNameFontSizeAdjustment ?? 0,
    seed: includeSeeding && entrant.seed ? Number(entrant.seed) : null,
    placement: entrant.placement,
    team_color: entrant.teamColor || null,
    entrant_1: { tag: entrant.entrant1.tag.trim(), name_font_size_adjustment: entrant.entrant1.nameFontSizeAdjustment ?? 0, characters: entrant.entrant1.characters.map(previewCharacter) },
    entrant_2: { tag: entrant.entrant2.tag.trim(), name_font_size_adjustment: entrant.entrant2.nameFontSizeAdjustment ?? 0, characters: entrant.entrant2.characters.map(previewCharacter) },
  });
}

function previewEntrantCount(format: FormatConfiguration): number {
  return format.selection.options.entrant_count ?? fixedEntrantCount(format.selection.mode, format.selection.options.event_format ?? "singles") ?? 8;
}

const fileCache = new Map<string, Promise<Blob>>();

/** Header refreshes re-send the same font and logo files, so fetch each only once. */
function loadFile(url: string, failure: string): Promise<Blob> {
  const cached = fileCache.get(url);
  if (cached) return cached;
  const loading = fetch(url).then((response) => {
    if (!response.ok) throw new Error(failure);
    return response.blob();
  });
  loading.catch(() => fileCache.delete(url));
  fileCache.set(url, loading);
  return loading;
}

interface PreviewData {
  format: FormatConfiguration;
  fontAsset: FormatFontInfo | null;
  tournament: TournamentDetails;
  entrants: EntrantDraft[];
  tournamentComplete: boolean;
  entrantsComplete: boolean;
  logoImage: FormatImageInfo | null;
}

async function previewRequestInit({ format, fontAsset, tournament, entrants, tournamentComplete, entrantsComplete, logoImage }: PreviewData, composition?: { background: Blob; overlay: Blob }): Promise<RequestInit> {
  const entrantCount = previewEntrantCount(format);
  const config = {
    mode: format.selection.mode,
    style: format.selection.options.podium_style ?? "legacy",
    event_format: format.selection.options.event_format ?? "singles",
    entrant_count: entrantCount,
    variant: format.selection.options.variant,
    animated: isPodiumsClapping(format.selection) && format.selection.options.animated !== false,
    transparent: true,
    formatting_asset_colors: format.formatting_asset_colors,
    entrant_text_colors: format.entrant_text_colors,
    header_layout: format.header_layout,
    text_settings: format.text_settings,
    logo_size: format.image_settings.logo_size,
    tournament: tournamentComplete ? {
      title: tournament.title.trim(),
      subtitle: tournament.subtitle.trim() || null,
      event: tournament.event.trim() || null,
      date: tournament.date || null,
      date_range_start: format.text_settings.metadata_rows.flat().includes("date_range") ? tournament.dateRangeStart || null : null,
      date_range_end: format.text_settings.metadata_rows.flat().includes("date_range") ? tournament.dateRangeEnd || null : null,
      free_text_1: tournament.freeText1?.trim() || null,
      free_text_2: tournament.freeText2?.trim() || null,
      free_text_3: tournament.freeText3?.trim() || null,
      free_text_4: tournament.freeText4?.trim() || null,
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
    entrant_visibility: entrantsComplete ? undefined : entrants.slice(0, entrantCount).map((entrant) => ({
      omit_entrant: entrant.omitEntrant === true, omit_placement: entrant.omitPlacement === true })),
  };
  if (!fontAsset?.custom && !(format.selection.mode === "radial" && logoImage) && !composition) {
    return { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(config) };
  }
  const form = new FormData();
  form.append("config", JSON.stringify(config));
  if (composition) {
    form.append("composite_background", composition.background, "background.png");
    form.append("composite_overlay", composition.overlay, "overlay.png");
  }
  if (fontAsset?.custom) form.append("font_file", await loadFile(fontAsset.url, "Could not load the selected custom font."), fontAsset.name);
  if (format.selection.mode === "radial" && logoImage) form.append("logo_file", await loadFile(logoImage.url, "Could not load the selected tournament logo."), "logo.png");
  return { method: "POST", body: form };
}

interface LayerPayload { kind: "content" | "header"; left: number; top: number; image: string | null }
interface LayersResponse { width: number; height: number; logo_index: number; layers: LayerPayload[]; animation: string | null }
interface ExactLayer { kind: "content" | "header"; left: number; top: number; image: HTMLImageElement | null }

/** The last exact render, kept as layers so header-only changes can replace just their layers. */
interface ExactRender {
  contentKey: string;
  headerKey: string;
  headerSequence: number;
  canvasSize: PixelSize;
  layers: ExactLayer[];
  logoIndex: number;
  animation: { blob: Blob; url: string; signature: string } | null;
}

async function fetchPreviewJson<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), init);
  if (!response.ok) throw new Error("Could not render the configured format preview.");
  return response.json() as Promise<T>;
}

function decodeImage(url: string): Promise<HTMLImageElement> {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("Could not decode the configured preview."));
    image.src = url;
  });
}

function decodeLayers(layers: LayerPayload[]): Promise<ExactLayer[]> {
  return Promise.all(layers.map(async (layer) => ({
    kind: layer.kind, left: layer.left, top: layer.top, image: layer.image ? await decodeImage(layer.image) : null,
  })));
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
  } else if (format.selection.mode === "squares" || format.selection.mode === "eyes" || format.selection.mode === "radial" || format.selection.mode === "flying_v") {
    context.drawImage(logo, box.left + (box.right - box.left - width) / 2, box.top + (box.bottom - box.top - height) / 2, width, height);
  } else {
    const left = position === "top_middle" ? (outputSize.width - width) / 2 : position === "top_right" ? outputSize.width - width - 20 : 20;
    context.drawImage(logo, left, 20, width, height);
  }
}

/** Composite the selected background, the exact layers, and the browser-drawn logo. */
function drawExactPreview(target: HTMLCanvasElement, render: ExactRender, format: FormatConfiguration, request: LayerRequest, background: HTMLImageElement | null, backgroundImage: FormatImageInfo | null, logo: HTMLImageElement | null, logoImage: FormatImageInfo | null) {
  target.width = request.outputSize.width;
  target.height = request.outputSize.height;
  const context = target.getContext("2d");
  if (!context) throw new Error("Canvas preview is unavailable.");
  drawBackground(context, format, request.outputSize, background, backgroundImage);
  const scaleX = request.outputSize.width / render.canvasSize.width;
  const scaleY = request.outputSize.height / render.canvasSize.height;
  for (const layer of layersWithLogo(render.layers, render.logoIndex)) {
    if (layer === "logo") {
      // Radial composes its logo beneath the header text on the server.
      if (format.selection.mode !== "radial") drawLogo(context, format, logo, logoImage, request.outputSize, request.logoPosition, request.logoBox);
    } else if (layer.image) {
      context.drawImage(layer.image, layer.left * scaleX, layer.top * scaleY, layer.image.naturalWidth * scaleX, layer.image.naturalHeight * scaleY);
    }
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

export default function LayeredFormatPreview({ format, backgroundImage, logoImage, fontAsset, tournament, entrants, tournamentComplete, entrantsComplete }: FormatPreviewProps) {
  const request = useMemo(() => layerRequest(format, fontAsset), [format, fontAsset]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [failed, setFailed] = useState(false);
  const [exact, setExact] = useState<ExactRender | null>(null);
  const [headerFailedKey, setHeaderFailedKey] = useState<string | null>(null);
  const headerSequence = useRef(0);
  const renderInFlight = useRef(false);
  const canvas = useRef<HTMLCanvasElement>(null);
  const expandedDialog = useRef<HTMLDialogElement>(null);
  const expandedCanvas = useRef<HTMLCanvasElement>(null);
  const entrantCount = previewEntrantCount(format);
  const visibleEntrants = entrants.slice(0, entrantCount);
  const visibility = visibleEntrants.map((entrant) => [entrant.omitEntrant === true, entrant.omitPlacement === true]);
  const { contentKey, headerKey } = exactPreviewKeys({
    format, fontId: fontAsset?.id ?? null, tournament: tournamentComplete ? tournament : null,
    entrants: entrantsComplete ? visibleEntrants : null, visibility, logoId: logoImage?.id ?? null,
  });
  const previewSignature = JSON.stringify({ contentKey, headerKey, imageSettings: format.image_settings, backgroundId: backgroundImage?.id ?? null, backgroundUrl: backgroundImage?.url ?? null, logoId: logoImage?.id ?? null, logoUrl: logoImage?.url ?? null });
  const exactCurrent = exact?.contentKey === contentKey;
  const headerFailed = exactCurrent && headerFailedKey === headerKey;
  const headerPending = exactCurrent && exact.headerKey !== headerKey && !headerFailed;
  const animatedPreviewUrl = exactCurrent && exact.animation?.signature === previewSignature ? exact.animation.url : null;
  const animatedSelection = isPodiumsClapping(format.selection) && format.selection.options.animated !== false;
  // Header and image edits update an exact still in place; an animation needs a new render to catch up.
  const needsRefresh = !exactCurrent || headerFailed || (animatedSelection && !animatedPreviewUrl);
  const animationUrl = exact?.animation?.url;

  useEffect(() => () => { if (animationUrl) URL.revokeObjectURL(animationUrl); }, [animationUrl]);

  useEffect(() => {
    if (exactCurrent) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setFailed(false);
    const timeout = window.setTimeout(async () => {
      try {
        const [foregrounds, header, background, logo, logoPlaceholder, resultLabels, watermark] = await Promise.all([
          Promise.all(request.foregroundLayers.map(async (layer) => ({ ...layer, image: await loadImage(layer.url) }))),
          loadImage(request.headerUrl),
          backgroundImage ? loadImage(backgroundImage.url) : Promise.resolve(null),
          logoImage ? loadImage(logoImage.url) : Promise.resolve(null),
          !logoImage && request.logoPlaceholderUrl ? loadImage(request.logoPlaceholderUrl) : Promise.resolve(null),
          request.resultLabelsUrl ? loadImage(request.resultLabelsUrl) : Promise.resolve(null),
          request.watermarkUrl ? loadImage(request.watermarkUrl) : Promise.resolve(null),
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
        if (format.selection.mode === "radial") drawLogo(context, format, logo, logoImage, request.outputSize, request.logoPosition, request.logoBox);
        if (logoPlaceholder) context.drawImage(logoPlaceholder, 0, 0, request.outputSize.width, request.outputSize.height);
        let headerLayer: CanvasImageSource = logo && format.selection.mode !== "radial" ? headerWithoutPlaceholder(header, request.logoBox) : header;
        if (isPodiumsClapping(format.selection)) headerLayer = podiumHeaderWithoutFooter(headerLayer, header.naturalWidth, header.naturalHeight);
        const headerHeight = format.selection.mode === "podium" ? 941 : request.outputSize.height;
        context.drawImage(tintedHeader(headerLayer, request.outputSize.width, headerHeight, format.text_settings.heading_color, format.text_settings.heading_metallic), 0, 0);
        if (resultLabels) context.drawImage(resultLabels, 0, 0, request.outputSize.width, request.outputSize.height);
        if (format.selection.mode !== "radial") drawLogo(context, format, logo, logoImage, request.outputSize, request.logoPosition, request.logoBox);
        if (watermark) drawRadialWatermark(context, watermark);
        if (isPodiumsClapping(format.selection)) drawPodiumPreviewFooter(context, header, request.outputSize);
        setLoading(false);
      } catch {
        if (!cancelled) { setFailed(true); setLoading(false); }
      }
    }, 80);
    return () => { cancelled = true; window.clearTimeout(timeout); };
  }, [backgroundImage, exactCurrent, format, logoImage, request]);

  // While the content layers still match, background, logo, and header edits recomposite the exact layers.
  useEffect(() => {
    if (!exact || !exactCurrent) return;
    let cancelled = false;
    void (async () => {
      try {
        const [background, logo] = await Promise.all([
          backgroundImage ? loadImage(backgroundImage.url) : Promise.resolve(null),
          logoImage ? loadImage(logoImage.url) : Promise.resolve(null),
        ]);
        if (!cancelled && canvas.current) drawExactPreview(canvas.current, exact, format, request, background, backgroundImage, logo, logoImage);
      } catch {
        if (!cancelled) setFailed(true);
      }
    })();
    return () => { cancelled = true; };
  }, [backgroundImage, exact, exactCurrent, format, logoImage, request]);

  useEffect(() => {
    if (!exact || !exactCurrent || exact.headerKey === headerKey || headerFailedKey === headerKey) return;
    const sequence = ++headerSequence.current;
    const requestedContentKey = contentKey;
    const requestedHeaderKey = headerKey;
    const data = { format, fontAsset, tournament, entrants, tournamentComplete, entrantsComplete, logoImage };
    // Responses are applied in request order, so dragging a slider keeps updating instead of waiting for it to stop.
    const timeout = window.setTimeout(async () => {
      try {
        const body = await fetchPreviewJson<{ layers: LayerPayload[] }>("format-preview/header", await previewRequestInit(data));
        const headers = await decodeLayers(body.layers);
        setExact((current) => {
          if (!current || current.contentKey !== requestedContentKey || sequence < current.headerSequence) return current;
          const layers = replaceHeaderLayers(current.layers, headers);
          return layers ? { ...current, layers, headerKey: requestedHeaderKey, headerSequence: sequence } : current;
        });
      } catch {
        if (sequence === headerSequence.current) setHeaderFailedKey(requestedHeaderKey);
      }
    }, 120);
    return () => window.clearTimeout(timeout);
  }, [contentKey, entrants, entrantsComplete, exact, exactCurrent, fontAsset, format, headerFailedKey, headerKey, logoImage, tournament, tournamentComplete]);

  async function refreshWithSelectedImages(download = false) {
    if (renderInFlight.current) return;
    renderInFlight.current = true;
    setRefreshing(true);
    setFailed(false);
    const keys = { contentKey, headerKey, signature: previewSignature };
    try {
      const [background, logo] = await Promise.all([
        backgroundImage ? loadImage(backgroundImage.url) : Promise.resolve(null),
        logoImage ? loadImage(logoImage.url) : Promise.resolve(null),
      ]);
      let composition: { background: Blob; overlay: Blob } | undefined;
      if (animatedSelection) {
        // GIF frames need the background and logo composed on the server.
        const backgroundLayer = document.createElement("canvas");
        const overlay = document.createElement("canvas");
        backgroundLayer.width = overlay.width = request.outputSize.width;
        backgroundLayer.height = overlay.height = request.outputSize.height;
        const backgroundContext = backgroundLayer.getContext("2d");
        const overlayContext = overlay.getContext("2d");
        if (!backgroundContext || !overlayContext) throw new Error("Canvas preview is unavailable.");
        drawBackground(backgroundContext, format, request.outputSize, background, backgroundImage);
        drawLogo(overlayContext, format, logo, logoImage, request.outputSize, request.logoPosition, request.logoBox);
        composition = { background: await canvasPng(backgroundLayer), overlay: await canvasPng(overlay) };
      }
      const init = await previewRequestInit({ format, fontAsset, tournament, entrants, tournamentComplete, entrantsComplete, logoImage }, composition);
      const body = await fetchPreviewJson<LayersResponse>("format-preview/layers", init);
      const animationBlob = body.animation ? dataUrlBlob(body.animation) : null;
      const render: ExactRender = {
        contentKey: keys.contentKey,
        headerKey: keys.headerKey,
        // Discard header responses requested before this render.
        headerSequence: ++headerSequence.current,
        canvasSize: { width: body.width, height: body.height },
        layers: await decodeLayers(body.layers),
        logoIndex: body.logo_index,
        animation: animationBlob ? { blob: animationBlob, url: URL.createObjectURL(animationBlob), signature: keys.signature } : null,
      };
      // The visible canvas redraws from this render once it matches the current inputs.
      setExact(render);
      setHeaderFailedKey(null);
      if (download) {
        let blob = render.animation?.blob;
        if (!blob) {
          const composite = document.createElement("canvas");
          drawExactPreview(composite, render, format, request, background, backgroundImage, logo, logoImage);
          blob = await canvasPng(composite);
        }
        const downloadUrl = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = downloadUrl;
        link.download = previewDownloadName(tournament.title, blob.type);
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
    <button className="format-preview__frame" type="button" onClick={openExpandedPreview} aria-label="Open a larger format preview"><canvas className="format-preview__canvas" ref={canvas} hidden={Boolean(animatedPreviewUrl)} width={request.outputSize.width} height={request.outputSize.height} aria-label={`Layered format preview: ${request.label}`} />{animatedPreviewUrl && <img className="format-preview__canvas" src={animatedPreviewUrl} alt={`Animated format preview: ${request.label}`} />}{loading && <span className="format-preview__loading">Updating layers…</span>}{headerPending && <span className="format-preview__loading">Updating header…</span>}</button>
    <button className={`button button--outline format-preview__refresh${needsRefresh ? " format-preview__refresh--needed" : ""}`} type="button" onClick={() => void refreshWithSelectedImages()} disabled={refreshing} aria-label={needsRefresh ? "Refresh Format Preview; exact render is available" : "Refresh Format Preview; preview is up to date"}><span>{refreshing ? "Refreshing preview…" : "Refresh Format Preview"}</span>{needsRefresh && !refreshing && <span className="format-preview__refresh-status">Exact render available</span>}</button>
    <p><strong>{exactCurrent ? "Exact entrant preview" : "Fast layered preview"}</strong> · {request.label}</p>
    {(failed || headerFailed) && <span className="format-preview__waiting" role="alert">The preview could not be updated. The previous preview is still shown.</span>}
    <dialog className="modal format-preview-modal" ref={expandedDialog} onClick={(event) => { if (event.target === event.currentTarget) event.currentTarget.close(); }}><div className="modal__content"><button className="modal__close" type="button" onClick={() => expandedDialog.current?.close()} aria-label="Close enlarged preview">×</button><canvas className="format-preview-modal__image" ref={expandedCanvas} hidden={Boolean(animatedPreviewUrl)} width={request.outputSize.width} height={request.outputSize.height} aria-label={`Enlarged format preview: ${request.label}`} />{animatedPreviewUrl && <img className="format-preview-modal__image" src={animatedPreviewUrl} alt={`Enlarged animated format preview: ${request.label}`} />}</div></dialog>
  </div>;
}

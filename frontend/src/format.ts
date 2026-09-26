export type CreationMode = "podium" | "eyes" | "squares";
export type EventFormat = "singles" | "doubles";
export type PodiumStyle = "legacy" | "customizable";
export type HeaderPosition = "top_left" | "top_middle" | "top_right";
export type HeaderContent = "tournament_logo" | "tournament_title" | "metadata";
export type SizeMultiplier = "1/4x" | "1/3x" | "1/2x" | "1x" | "2x" | "3x" | "4x";

export interface PixelSize { width: number; height: number }
export interface PixelRect { left: number; top: number; right: number; bottom: number }
export interface BackgroundPlacement {
  asset_id: string;
  source_size: PixelSize;
  output_size: PixelSize;
  size_multiplier: SizeMultiplier;
  alignment: { x: number; y: number };
  source_crop: PixelRect;
  destination: PixelRect;
}

export interface ImageSettings {
  background_color: string;
  logo_size: SizeMultiplier;
  background_size: SizeMultiplier;
  background_placement: BackgroundPlacement | null;
}

export interface FormatSelection {
  mode: CreationMode;
  options: {
    event_format: EventFormat | null;
    entrant_count: number | null;
    variant: string | null;
    podium_style: PodiumStyle | null;
  };
}

export type HeaderLayout = Record<HeaderPosition, HeaderContent>;

export interface FormatConfiguration {
  schema_version: 1;
  selection: FormatSelection;
  header_layout: HeaderLayout;
  image_settings: ImageSettings;
}

export const DEFAULT_HEADER_LAYOUT: HeaderLayout = {
  top_left: "tournament_logo",
  top_middle: "tournament_title",
  top_right: "metadata",
};

export const DEFAULT_IMAGE_SETTINGS: ImageSettings = {
  background_color: "#00000000",
  logo_size: "1x",
  background_size: "1x",
  background_placement: null,
};

export const EMPTY_FORMAT: FormatConfiguration = {
  schema_version: 1,
  selection: {
    mode: "podium",
    options: {
      event_format: null,
      entrant_count: null,
      variant: null,
      podium_style: null,
    },
  },
  header_layout: DEFAULT_HEADER_LAYOUT,
  image_settings: DEFAULT_IMAGE_SETTINGS,
};

const modes = new Set<CreationMode>(["podium", "eyes", "squares"]);
const eventFormats = new Set<EventFormat>(["singles", "doubles"]);
const podiumStyles = new Set<PodiumStyle>(["legacy", "customizable"]);
const headerPositions: HeaderPosition[] = ["top_left", "top_middle", "top_right"];
const headerContents = new Set<HeaderContent>(["tournament_logo", "tournament_title", "metadata"]);
const sizeMultipliers = new Set<SizeMultiplier>(["1/4x", "1/3x", "1/2x", "1x", "2x", "3x", "4x"]);
const rgbaColor = /^#[0-9a-f]{8}$/i;

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function normalizeHeaderLayout(value: unknown): HeaderLayout {
  // Early version-1 exports did not yet contain header placement settings.
  if (value === undefined) return { ...DEFAULT_HEADER_LAYOUT };
  if (!isObject(value)) throw new Error("Format code has an invalid header layout.");
  const layout = Object.fromEntries(headerPositions.map((position) => [position, value[position]])) as HeaderLayout;
  const contents = headerPositions.map((position) => layout[position]);
  if (contents.some((content) => !headerContents.has(content)) || new Set(contents).size !== headerPositions.length) {
    throw new Error("Logo, tournament title, and metadata must each use a unique header position.");
  }
  return layout;
}

function finiteNumber(value: unknown, name: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) throw new Error(`Format code has an invalid ${name}.`);
  return value;
}

function normalizePixelSize(value: unknown, name: string): PixelSize {
  if (!isObject(value)) throw new Error(`Format code has an invalid ${name}.`);
  const width = finiteNumber(value.width, `${name} width`);
  const height = finiteNumber(value.height, `${name} height`);
  if (width <= 0 || height <= 0) throw new Error(`Format code has an invalid ${name}.`);
  return { width, height };
}

function normalizePixelRect(value: unknown, name: string): PixelRect {
  if (!isObject(value)) throw new Error(`Format code has an invalid ${name}.`);
  const result = {
    left: finiteNumber(value.left, `${name} left`),
    top: finiteNumber(value.top, `${name} top`),
    right: finiteNumber(value.right, `${name} right`),
    bottom: finiteNumber(value.bottom, `${name} bottom`),
  };
  if (result.right <= result.left || result.bottom <= result.top) throw new Error(`Format code has an invalid ${name}.`);
  return result;
}

function normalizeBackgroundPlacement(value: unknown): BackgroundPlacement | null {
  if (value === null || value === undefined) return null;
  if (!isObject(value) || typeof value.asset_id !== "string" || !value.asset_id || !isObject(value.alignment) || !sizeMultipliers.has(value.size_multiplier as SizeMultiplier)) {
    throw new Error("Format code has an invalid background placement.");
  }
  const x = finiteNumber(value.alignment.x, "background horizontal alignment");
  const y = finiteNumber(value.alignment.y, "background vertical alignment");
  if (x < 0 || x > 1 || y < 0 || y > 1) throw new Error("Background alignment must be between zero and one.");
  return {
    asset_id: value.asset_id,
    source_size: normalizePixelSize(value.source_size, "background source size"),
    output_size: normalizePixelSize(value.output_size, "background output size"),
    size_multiplier: value.size_multiplier as SizeMultiplier,
    alignment: { x, y },
    source_crop: normalizePixelRect(value.source_crop, "background source crop"),
    destination: normalizePixelRect(value.destination, "background destination"),
  };
}

function normalizeImageSettings(value: unknown): ImageSettings {
  if (value === undefined) return { ...DEFAULT_IMAGE_SETTINGS };
  if (!isObject(value) || typeof value.background_color !== "string" || !rgbaColor.test(value.background_color)) {
    throw new Error("Format code must include an eight-digit RGBA background color.");
  }
  if (!sizeMultipliers.has(value.logo_size as SizeMultiplier) || !sizeMultipliers.has(value.background_size as SizeMultiplier)) {
    throw new Error("Format code has an invalid image size multiplier.");
  }
  return {
    background_color: value.background_color.toUpperCase(),
    logo_size: value.logo_size as SizeMultiplier,
    background_size: value.background_size as SizeMultiplier,
    background_placement: normalizeBackgroundPlacement(value.background_placement),
  };
}

export function normalizeFormat(value: unknown): FormatConfiguration {
  if (!isObject(value) || value.schema_version !== 1) {
    throw new Error("Format code must be a version 1 format object.");
  }
  if (value.selection === null) return { ...EMPTY_FORMAT, header_layout: normalizeHeaderLayout(value.header_layout), image_settings: normalizeImageSettings(value.image_settings) };
  if (!isObject(value.selection) || !modes.has(value.selection.mode as CreationMode)) {
    throw new Error("Format code has an invalid creation mode.");
  }
  const mode = value.selection.mode as CreationMode;
  const options = value.selection.options;
  if (!isObject(options)) throw new Error("Format code has invalid mode options.");
  const rawEventFormat = options.event_format;
  if (rawEventFormat !== null && !eventFormats.has(rawEventFormat as EventFormat)) {
    throw new Error("Format code must choose singles or doubles.");
  }
  const rawEntrantCount = options.entrant_count;
  if (rawEntrantCount !== null && (!Number.isInteger(rawEntrantCount) || Number(rawEntrantCount) <= 0)) {
    throw new Error("Format code has an invalid entrant count.");
  }
  if (options.variant !== null && typeof options.variant !== "string") {
    throw new Error("Format code has an invalid layout variant.");
  }
  const rawStyle = options.podium_style;
  if (rawStyle !== null && !podiumStyles.has(rawStyle as PodiumStyle)) {
    throw new Error("Format code has an invalid podium style.");
  }
  if (mode !== "podium" && rawStyle !== null) {
    throw new Error("Only podium formats can include a podium style.");
  }
  return {
    schema_version: 1,
    selection: {
      mode,
      options: {
        event_format: rawEventFormat as EventFormat | null,
        entrant_count: rawEntrantCount === null ? null : Number(rawEntrantCount),
        variant: options.variant as string | null,
        podium_style: rawStyle as PodiumStyle | null,
      },
    },
    header_layout: normalizeHeaderLayout(value.header_layout),
    image_settings: normalizeImageSettings(value.image_settings),
  };
}

export function parseFormatCode(code: string): FormatConfiguration {
  let value: unknown;
  try {
    value = JSON.parse(code);
  } catch {
    throw new Error("That code is not valid JSON.");
  }
  return normalizeFormat(value);
}

export function isFormatComplete(format: FormatConfiguration): boolean {
  try {
    const normalized = normalizeFormat(format);
    return normalized.selection.mode === "podium"
      && normalized.selection.options.podium_style !== null
      && normalized.selection.options.event_format !== null;
  } catch {
    return false;
  }
}

export function formatCode(format: FormatConfiguration): string {
  return JSON.stringify(format, null, 2);
}

export function sizeMultiplierValue(multiplier: SizeMultiplier): number {
  return ({ "1/4x": 1 / 4, "1/3x": 1 / 3, "1/2x": 1 / 2, "1x": 1, "2x": 2, "3x": 3, "4x": 4 })[multiplier];
}

export function formatCanvasSize(format: FormatConfiguration): PixelSize | null {
  if (format.selection.mode !== "podium") return null;
  if (format.selection.options.podium_style === "customizable") return { width: 1920, height: 941 };
  if (format.selection.options.podium_style === "legacy") return { width: 1672, height: 941 };
  return null;
}

const clamp = (value: number, minimum: number, maximum: number) => Math.min(maximum, Math.max(minimum, value));

export function buildBackgroundPlacement(assetId: string, source: PixelSize, output: PixelSize, multiplier: SizeMultiplier, alignment = { x: .5, y: .5 }): BackgroundPlacement {
  const scale = sizeMultiplierValue(multiplier);
  const x = clamp(alignment.x, 0, 1);
  const y = clamp(alignment.y, 0, 1);
  const scaledWidth = source.width * scale;
  const scaledHeight = source.height * scale;
  const cropWidth = Math.min(source.width, output.width / scale);
  const cropHeight = Math.min(source.height, output.height / scale);
  const sourceLeft = (source.width - cropWidth) * x;
  const sourceTop = (source.height - cropHeight) * y;
  const destinationWidth = Math.min(output.width, scaledWidth);
  const destinationHeight = Math.min(output.height, scaledHeight);
  const destinationLeft = Math.max(0, output.width - destinationWidth) * x;
  const destinationTop = Math.max(0, output.height - destinationHeight) * y;
  return {
    asset_id: assetId,
    source_size: source,
    output_size: output,
    size_multiplier: multiplier,
    alignment: { x, y },
    source_crop: {
      left: Math.round(sourceLeft),
      top: Math.round(sourceTop),
      right: Math.round(sourceLeft + cropWidth),
      bottom: Math.round(sourceTop + cropHeight),
    },
    destination: {
      left: Math.round(destinationLeft),
      top: Math.round(destinationTop),
      right: Math.round(destinationLeft + destinationWidth),
      bottom: Math.round(destinationTop + destinationHeight),
    },
  };
}


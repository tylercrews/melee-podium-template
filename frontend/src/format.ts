export type CreationMode = "podium" | "eyes" | "squares";
export type EventFormat = "singles" | "doubles";
export type PodiumStyle = "legacy" | "customizable";
export type HeaderPosition = "top_left" | "top_middle" | "top_right";
export type HeaderContent = "tournament_logo" | "tournament_title" | "metadata";
export type SizeMultiplier = number;
export type BackgroundSizeOption = SizeMultiplier | "scale_to_width" | "scale_to_height";
export type FormattingColorSelectionMode = "premade" | "pick_1" | "pick_2" | "pick_all";
export type FormattingColorPreset = "smash_player_colors" | "olympic_medals" | "rainbow";

export interface FormattingAssetColor {
  main_color: string;
  face_color: string;
  base_color: string;
  metallic: boolean;
}

export interface FormattingAssetColors {
  mode: FormattingColorSelectionMode;
  preset: FormattingColorPreset | null;
  colors: FormattingAssetColor[];
}

export interface PixelSize { width: number; height: number }
export interface PixelRect { left: number; top: number; right: number; bottom: number }
export interface BackgroundPlacement {
  asset_id: string;
  source_size: PixelSize;
  output_size: PixelSize;
  size_option: BackgroundSizeOption;
  size_multiplier: number;
  alignment: { x: number; y: number };
  source_crop: PixelRect;
  destination: PixelRect;
}

export interface ImageSettings {
  background_color: string;
  logo_size: SizeMultiplier;
  background_size: BackgroundSizeOption;
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

export interface EntrantCountOption {
  entrant_count: number;
  variant: string | null;
  label: string;
  detail?: string;
}

export type HeaderLayout = Record<HeaderPosition, HeaderContent>;

export interface FormatConfiguration {
  schema_version: 1;
  selection: FormatSelection;
  header_layout: HeaderLayout;
  image_settings: ImageSettings;
  formatting_asset_colors: FormattingAssetColors;
}

export const DEFAULT_HEADER_LAYOUT: HeaderLayout = {
  top_left: "tournament_logo",
  top_middle: "tournament_title",
  top_right: "metadata",
};

export const DEFAULT_IMAGE_SETTINGS: ImageSettings = {
  background_color: "#00000000",
  logo_size: 1,
  background_size: 1,
  background_placement: null,
};

export const DEFAULT_FORMATTING_ASSET_COLORS: FormattingAssetColors = {
  mode: "premade",
  preset: "smash_player_colors",
  colors: [],
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
  formatting_asset_colors: DEFAULT_FORMATTING_ASSET_COLORS,
};

const modes = new Set<CreationMode>(["podium", "eyes", "squares"]);
const eventFormats = new Set<EventFormat>(["singles", "doubles"]);
const podiumStyles = new Set<PodiumStyle>(["legacy", "customizable"]);
const headerPositions: HeaderPosition[] = ["top_left", "top_middle", "top_right"];
const headerContents = new Set<HeaderContent>(["tournament_logo", "tournament_title", "metadata"]);
const legacySizeMultipliers: Record<string, number> = {
  "1/4x": 1 / 4,
  "1/3x": 1 / 3,
  "1/2x": 1 / 2,
  "1x": 1,
  "2x": 2,
  "3x": 3,
  "4x": 4,
};
const MIN_SIZE_MULTIPLIER = .001;
const MAX_SIZE_MULTIPLIER = 100;
const rgbaColor = /^#[0-9a-f]{8}$/i;
const formattingColorModes = new Set<FormattingColorSelectionMode>(["premade", "pick_1", "pick_2", "pick_all"]);
const formattingColorPresets = new Set<FormattingColorPreset>(["smash_player_colors", "olympic_medals", "rainbow"]);

export const FORMAT_ENTRANT_OPTIONS: Record<CreationMode, Record<EventFormat, EntrantCountOption[]>> = {
  podium: {
    singles: [
      { entrant_count: 3, variant: null, label: "Top 3" },
      { entrant_count: 4, variant: null, label: "Top 4" },
      { entrant_count: 8, variant: null, label: "Top 8", detail: "Eight podiums" },
      { entrant_count: 8, variant: "four_podium", label: "Top 8 – 4 Podiums", detail: "Four podiums with lower summaries" },
    ],
    doubles: [
      { entrant_count: 3, variant: null, label: "Top 3" },
      { entrant_count: 4, variant: null, label: "Top 4" },
    ],
  },
  eyes: {
    singles: [3, 4, 8, 10, 15, 20, 25, 32].map((entrant_count) => ({ entrant_count, variant: null, label: `Top ${entrant_count}` })),
    doubles: [3, 4, 8].map((entrant_count) => ({ entrant_count, variant: null, label: `Top ${entrant_count}` })),
  },
  squares: {
    singles: [{ entrant_count: 8, variant: null, label: "Top 8" }],
    doubles: [
      { entrant_count: 3, variant: null, label: "Top 3" },
      { entrant_count: 4, variant: null, label: "Top 4" },
    ],
  },
};

export function entrantCountOptions(selection: FormatSelection): EntrantCountOption[] {
  return selection.options.event_format
    ? FORMAT_ENTRANT_OPTIONS[selection.mode][selection.options.event_format]
    : [];
}

export function hasValidEntrantCount(selection: FormatSelection): boolean {
  return entrantCountOptions(selection).some((option) =>
    option.entrant_count === selection.options.entrant_count
      && option.variant === selection.options.variant,
  );
}

export function formattingAssetCount(format: FormatConfiguration): number {
  if (format.selection.mode === "podium" && format.selection.options.variant === "four_podium") return 4;
  return format.selection.options.entrant_count ?? (format.selection.mode === "podium" ? 3 : 1);
}

function hasCompleteFormattingAssetColors(format: FormatConfiguration): boolean {
  if (format.selection.mode === "podium" && format.selection.options.podium_style !== "customizable") return true;
  const colors = format.formatting_asset_colors;
  if (colors.mode === "premade") return colors.preset !== null;
  if (colors.mode === "pick_1") return colors.colors.length === 1;
  if (colors.mode === "pick_2") return colors.colors.length === 2;
  return colors.colors.length === formattingAssetCount(format);
}

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

function normalizeSizeMultiplier(value: unknown, name: string): SizeMultiplier {
  const multiplier = typeof value === "string" ? legacySizeMultipliers[value] : value;
  const normalized = finiteNumber(multiplier, name);
  if (normalized < MIN_SIZE_MULTIPLIER || normalized > MAX_SIZE_MULTIPLIER) {
    throw new Error(`Format code has an invalid ${name}.`);
  }
  return normalized;
}

function normalizeBackgroundSizeOption(value: unknown): BackgroundSizeOption {
  if (value === "scale_to_width" || value === "scale_to_height") return value;
  return normalizeSizeMultiplier(value, "background size multiplier");
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
  if (!isObject(value) || typeof value.asset_id !== "string" || !value.asset_id || !isObject(value.alignment)) {
    throw new Error("Format code has an invalid background placement.");
  }
  const sourceSize = normalizePixelSize(value.source_size, "background source size");
  const outputSize = normalizePixelSize(value.output_size, "background output size");
  // Early version-1 placements stored the fixed option directly in size_multiplier.
  const rawOption = value.size_option ?? value.size_multiplier;
  const sizeOption = normalizeBackgroundSizeOption(rawOption);
  const resolvedMultiplier = typeof value.size_multiplier === "number"
    ? finiteNumber(value.size_multiplier, "background size multiplier")
    : backgroundSizeValue(sizeOption, sourceSize, outputSize);
  if (resolvedMultiplier <= 0) throw new Error("Format code has an invalid background size multiplier.");
  const x = finiteNumber(value.alignment.x, "background horizontal alignment");
  const y = finiteNumber(value.alignment.y, "background vertical alignment");
  if (x < 0 || x > 1 || y < 0 || y > 1) throw new Error("Background alignment must be between zero and one.");
  return {
    asset_id: value.asset_id,
    source_size: sourceSize,
    output_size: outputSize,
    size_option: sizeOption,
    size_multiplier: resolvedMultiplier,
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
  return {
    background_color: value.background_color.toUpperCase(),
    logo_size: normalizeSizeMultiplier(value.logo_size, "logo size multiplier"),
    background_size: normalizeBackgroundSizeOption(value.background_size),
    background_placement: normalizeBackgroundPlacement(value.background_placement),
  };
}

function normalizeFormattingAssetColors(value: unknown): FormattingAssetColors {
  // Early version-1 formats predate formatting-asset color controls.
  if (value === undefined) return { ...DEFAULT_FORMATTING_ASSET_COLORS, colors: [] };
  if (!isObject(value) || !formattingColorModes.has(value.mode as FormattingColorSelectionMode) || !Array.isArray(value.colors)) {
    throw new Error("Format code has invalid formatting asset colors.");
  }
  const mode = value.mode as FormattingColorSelectionMode;
  const preset = value.preset === null ? null : value.preset as FormattingColorPreset;
  if (mode === "premade" ? !preset || !formattingColorPresets.has(preset) || value.colors.length !== 0 : preset !== null) {
    throw new Error("Format code has an invalid formatting color selection.");
  }
  const colors = value.colors.map((item) => {
    if (!isObject(item) || !rgbaColor.test(String(item.main_color)) || !rgbaColor.test(String(item.face_color)) || !rgbaColor.test(String(item.base_color)) || typeof item.metallic !== "boolean") {
      throw new Error("Every formatting asset color must include valid eight-digit RGBA colors.");
    }
    return {
      main_color: String(item.main_color).toUpperCase(),
      face_color: String(item.face_color).toUpperCase(),
      base_color: String(item.base_color).toUpperCase(),
      metallic: item.metallic,
    };
  });
  const expectedCount = mode === "pick_1" ? 1 : mode === "pick_2" ? 2 : null;
  if ((expectedCount !== null && colors.length !== expectedCount) || (mode === "pick_all" && colors.length === 0)) {
    throw new Error("Format code has the wrong number of formatting color selections.");
  }
  return { mode, preset, colors };
}

export function normalizeFormat(value: unknown): FormatConfiguration {
  if (!isObject(value) || value.schema_version !== 1) {
    throw new Error("Format code must be a version 1 format object.");
  }
  if (value.selection === null) return { ...EMPTY_FORMAT, header_layout: normalizeHeaderLayout(value.header_layout), image_settings: normalizeImageSettings(value.image_settings), formatting_asset_colors: normalizeFormattingAssetColors(value.formatting_asset_colors) };
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
    formatting_asset_colors: normalizeFormattingAssetColors(value.formatting_asset_colors),
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
      && normalized.selection.options.event_format !== null
      && hasValidEntrantCount(normalized.selection)
      && hasCompleteFormattingAssetColors(normalized);
  } catch {
    return false;
  }
}

export function formatCode(format: FormatConfiguration): string {
  return JSON.stringify(format, null, 2);
}

export function sizeMultiplierValue(multiplier: SizeMultiplier): number {
  return multiplier;
}

export function backgroundSizeValue(option: BackgroundSizeOption, source: PixelSize, output: PixelSize): number {
  if (option === "scale_to_width") return output.width / source.width;
  if (option === "scale_to_height") return output.height / source.height;
  return sizeMultiplierValue(option);
}

export function formatCanvasSize(format: FormatConfiguration): PixelSize | null {
  if (format.selection.mode !== "podium") return null;
  if (format.selection.options.podium_style === "customizable") return { width: 1920, height: 941 };
  if (format.selection.options.podium_style === "legacy") return { width: 1672, height: 941 };
  return null;
}

const clamp = (value: number, minimum: number, maximum: number) => Math.min(maximum, Math.max(minimum, value));

export function buildBackgroundPlacement(assetId: string, source: PixelSize, output: PixelSize, sizeOption: BackgroundSizeOption, alignment = { x: .5, y: .5 }): BackgroundPlacement {
  const scale = backgroundSizeValue(sizeOption, source, output);
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
    size_option: sizeOption,
    size_multiplier: scale,
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


export type CreationMode = "podium" | "eyes" | "squares";
export type EventFormat = "singles" | "doubles";
export type PodiumStyle = "legacy" | "customizable";
export type HeaderPosition = "top_left" | "top_middle" | "top_right";
export type HeaderContent = "tournament_logo" | "tournament_title" | "metadata";
export type SizeMultiplier = number;
export type BackgroundSizeOption = SizeMultiplier | "scale_to_width" | "scale_to_height";
export type FormattingColorSelectionMode = "premade" | "pick_1" | "pick_2" | "pick_all";
export type EntrantTextColorSelectionMode = "match_podium" | "pick_1" | "pick_2" | "pick_all";
export type FormattingColorPreset = "smash_player_colors" | "olympic_medals" | "rainbow";
export type MetadataField = "event" | "date" | "entrants_count" | "tournament_link" | "tournament_location" | "stream_link" | "vod_link" | "to_x_account" | "to_twitch_account" | "to_bluesky_account";

export interface FormattingAssetColor {
  main_color: string;
  face_color: string;
  base_color: string;
  metallic: boolean;
}

export interface PresetTransparency {
  main_color: number;
  face_color: number;
  base_color: number;
}

export interface FormattingAssetColors {
  mode: FormattingColorSelectionMode;
  preset: FormattingColorPreset | null;
  preset_transparency: PresetTransparency;
  colors: FormattingAssetColor[];
}

export interface EntrantTextColors {
  mode: EntrantTextColorSelectionMode;
  colors: string[];
  metallic: boolean[];
}

export interface TextSettings {
  heading_color: string;
  heading_metallic: boolean;
  font_asset_id: string;
  font_size_adjustment: number;
  include_seeding: boolean;
  replace_base_urls_with_icons: boolean;
  metadata_fields: MetadataField[];
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
  logo_asset_id: string | null;
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
  entrant_text_colors: EntrantTextColors;
  text_settings: TextSettings;
}

export const DEFAULT_HEADER_LAYOUT: HeaderLayout = {
  top_left: "tournament_logo",
  top_middle: "tournament_title",
  top_right: "metadata",
};

export const DEFAULT_IMAGE_SETTINGS: ImageSettings = {
  background_color: "#00000000",
  logo_asset_id: null,
  logo_size: 1,
  background_size: 1,
  background_placement: null,
};

export const DEFAULT_FORMATTING_ASSET_COLORS: FormattingAssetColors = {
  mode: "premade",
  preset: "smash_player_colors",
  preset_transparency: { main_color: 0, face_color: 0, base_color: 0 },
  colors: [],
};

export const DEFAULT_ENTRANT_TEXT_COLORS: EntrantTextColors = {
  mode: "match_podium",
  colors: [],
  metallic: [],
};

export const ALL_METADATA_FIELDS: MetadataField[] = ["tournament_link", "event", "date", "entrants_count", "tournament_location", "stream_link", "vod_link", "to_x_account", "to_twitch_account", "to_bluesky_account"];

export const DEFAULT_TEXT_SETTINGS: TextSettings = {
  heading_color: "#FFFFFFFF",
  heading_metallic: false,
  font_asset_id: "provided:tyrowo",
  font_size_adjustment: 0,
  include_seeding: true,
  replace_base_urls_with_icons: true,
  metadata_fields: ["tournament_link", "event", "date", "entrants_count"],
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
  entrant_text_colors: DEFAULT_ENTRANT_TEXT_COLORS,
  text_settings: DEFAULT_TEXT_SETTINGS,
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
const entrantTextColorModes = new Set<EntrantTextColorSelectionMode>(["match_podium", "pick_1", "pick_2", "pick_all"]);
const metadataFields = new Set<MetadataField>(ALL_METADATA_FIELDS);

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
    singles: [8, 10, 15, 16, 20, 25].map((entrant_count) => ({
      entrant_count,
      variant: null,
      label: entrant_count === 16 ? "Tournament Top 16" : entrant_count === 8 ? "Top 8" : `PR Top ${entrant_count}`,
    })),
    doubles: [3, 4].map((entrant_count) => ({ entrant_count, variant: null, label: `Top ${entrant_count}` })),
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

function hasCompleteEntrantTextColors(format: FormatConfiguration): boolean {
  const selection = format.entrant_text_colors;
  if (selection.mode === "match_podium") return selection.colors.length === 0;
  if (selection.mode === "pick_1") return selection.colors.length === 1;
  if (selection.mode === "pick_2") return selection.colors.length === 2;
  return selection.colors.length === format.selection.options.entrant_count;
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
    logo_asset_id: typeof value.logo_asset_id === "string" && value.logo_asset_id.trim() ? value.logo_asset_id.trim() : null,
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
  const rawTransparency = value.preset_transparency;
  const transparencyValue = (part: keyof PresetTransparency): number => {
    // Early version-1 formats stored one percentage for the whole preset.
    const candidate = isObject(rawTransparency)
      ? rawTransparency[part]
      : rawTransparency ?? 0;
    const normalized = finiteNumber(candidate, `${part.replace("_color", "")} preset transparency`);
    if (!Number.isInteger(normalized) || normalized < 0 || normalized > 100) {
      throw new Error("Format code has an invalid preset transparency.");
    }
    return normalized;
  };
  const presetTransparency: PresetTransparency = {
    main_color: transparencyValue("main_color"),
    face_color: transparencyValue("face_color"),
    base_color: transparencyValue("base_color"),
  };
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
  return {
    mode,
    preset,
    preset_transparency: mode === "premade"
      ? presetTransparency
      : { ...DEFAULT_FORMATTING_ASSET_COLORS.preset_transparency },
    colors,
  };
}

function normalizeEntrantTextColors(value: unknown): EntrantTextColors {
  // Early version-1 formats used the podium palette for entrant text implicitly.
  if (value === undefined) return { ...DEFAULT_ENTRANT_TEXT_COLORS, colors: [] };
  if (!isObject(value) || !entrantTextColorModes.has(value.mode as EntrantTextColorSelectionMode) || !Array.isArray(value.colors)) {
    throw new Error("Format code has invalid entrant text colors.");
  }
  const mode = value.mode as EntrantTextColorSelectionMode;
  const colors = value.colors.map((color) => {
    if (typeof color !== "string" || !rgbaColor.test(color)) throw new Error("Every entrant text color must be an eight-digit RGBA color.");
    return color.toUpperCase();
  });
  const rawMetallic = value.metallic === undefined ? colors.map(() => false) : value.metallic;
  if (!Array.isArray(rawMetallic) || rawMetallic.length !== colors.length || rawMetallic.some((item) => typeof item !== "boolean")) {
    throw new Error("Every entrant text color must include a valid Metallic setting.");
  }
  const expectedCount = mode === "match_podium" ? 0 : mode === "pick_1" ? 1 : mode === "pick_2" ? 2 : null;
  if ((expectedCount !== null && colors.length !== expectedCount) || (mode === "pick_all" && colors.length === 0)) {
    throw new Error("Format code has the wrong number of entrant text colors.");
  }
  return { mode, colors, metallic: rawMetallic as boolean[] };
}

function normalizeTextSettings(value: unknown): TextSettings {
  if (value === undefined) return { ...DEFAULT_TEXT_SETTINGS, metadata_fields: [...DEFAULT_TEXT_SETTINGS.metadata_fields] };
  if (!isObject(value) || (value.heading_color !== undefined && (typeof value.heading_color !== "string" || !rgbaColor.test(value.heading_color))) || (value.heading_metallic !== undefined && typeof value.heading_metallic !== "boolean") || typeof value.font_asset_id !== "string" || !value.font_asset_id.trim() || !Number.isInteger(value.font_size_adjustment) || Number(value.font_size_adjustment) < -20 || Number(value.font_size_adjustment) > 20 || (value.include_seeding !== undefined && typeof value.include_seeding !== "boolean") || (value.replace_base_urls_with_icons !== undefined && typeof value.replace_base_urls_with_icons !== "boolean") || !Array.isArray(value.metadata_fields)) {
    throw new Error("Format code has invalid text settings.");
  }
  const fields = value.metadata_fields as unknown[];
  if (fields.some((field) => !metadataFields.has(field as MetadataField)) || new Set(fields).size !== fields.length) {
    throw new Error("Format code has invalid or duplicate metadata fields.");
  }
  const fontAssetId = value.font_asset_id.trim();
  return {
    heading_color: typeof value.heading_color === "string" ? value.heading_color.toUpperCase() : DEFAULT_TEXT_SETTINGS.heading_color,
    heading_metallic: value.heading_metallic === true,
    font_asset_id: fontAssetId,
    font_size_adjustment: fontAssetId.startsWith("provided:") ? 0 : Number(value.font_size_adjustment),
    include_seeding: value.include_seeding !== false,
    replace_base_urls_with_icons: value.replace_base_urls_with_icons !== false,
    metadata_fields: fields as MetadataField[],
  };
}

export function normalizeFormat(value: unknown): FormatConfiguration {
  if (!isObject(value) || value.schema_version !== 1) {
    throw new Error("Format code must be a version 1 format object.");
  }
  if (value.selection === null) return { ...EMPTY_FORMAT, header_layout: normalizeHeaderLayout(value.header_layout), image_settings: normalizeImageSettings(value.image_settings), formatting_asset_colors: normalizeFormattingAssetColors(value.formatting_asset_colors), entrant_text_colors: normalizeEntrantTextColors(value.entrant_text_colors), text_settings: normalizeTextSettings(value.text_settings) };
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
    entrant_text_colors: normalizeEntrantTextColors(value.entrant_text_colors),
    text_settings: normalizeTextSettings(value.text_settings),
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
    const supportedMode = normalized.selection.mode !== "podium"
      || normalized.selection.options.podium_style !== null;
    return supportedMode
      && normalized.selection.options.event_format !== null
      && hasValidEntrantCount(normalized.selection)
      && hasCompleteFormattingAssetColors(normalized)
      && hasCompleteEntrantTextColors(normalized);
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
  if (format.selection.mode === "squares") return { width: 1920, height: 1080 };
  if (format.selection.mode === "eyes") {
    const count = format.selection.options.entrant_count;
    if (format.selection.options.event_format === "doubles" || count === 8) return { width: 1080, height: 1920 };
    if (count === 10) return { width: 1920, height: 1542 };
    if (count === 15) return { width: 1920, height: 2114 };
    if (count === 16) return { width: 2400, height: 1828 };
    if (count === 20) return { width: 1920, height: 2686 };
    if (count === 25) return { width: 2400, height: 2400 };
    return null;
  }
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


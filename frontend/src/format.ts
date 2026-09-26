export type CreationMode = "podium" | "eyes" | "squares";
export type EventFormat = "singles" | "doubles";
export type PodiumStyle = "legacy" | "customizable";
export type HeaderPosition = "top_left" | "top_middle" | "top_right";
export type HeaderContent = "tournament_logo" | "tournament_title" | "metadata";

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
}

export const DEFAULT_HEADER_LAYOUT: HeaderLayout = {
  top_left: "tournament_logo",
  top_middle: "tournament_title",
  top_right: "metadata",
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
};

const modes = new Set<CreationMode>(["podium", "eyes", "squares"]);
const eventFormats = new Set<EventFormat>(["singles", "doubles"]);
const podiumStyles = new Set<PodiumStyle>(["legacy", "customizable"]);
const headerPositions: HeaderPosition[] = ["top_left", "top_middle", "top_right"];
const headerContents = new Set<HeaderContent>(["tournament_logo", "tournament_title", "metadata"]);

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

export function normalizeFormat(value: unknown): FormatConfiguration {
  if (!isObject(value) || value.schema_version !== 1) {
    throw new Error("Format code must be a version 1 format object.");
  }
  if (value.selection === null) return { ...EMPTY_FORMAT, header_layout: normalizeHeaderLayout(value.header_layout) };
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


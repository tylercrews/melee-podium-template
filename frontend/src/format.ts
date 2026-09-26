export type CreationMode = "podium" | "eyes" | "squares";
export type EventFormat = "singles" | "doubles";
export type PodiumStyle = "legacy" | "customizable";

export interface FormatSelection {
  mode: CreationMode;
  options: {
    event_format: EventFormat;
    entrant_count: number;
    variant: string | null;
    podium_style: PodiumStyle | null;
  };
}

export interface FormatConfiguration {
  schema_version: 1;
  selection: FormatSelection | null;
}

export const EMPTY_FORMAT: FormatConfiguration = {
  schema_version: 1,
  selection: null,
};

const modes = new Set<CreationMode>(["podium", "eyes", "squares"]);
const eventFormats = new Set<EventFormat>(["singles", "doubles"]);
const podiumStyles = new Set<PodiumStyle>(["legacy", "customizable"]);

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function normalizeFormat(value: unknown): FormatConfiguration {
  if (!isObject(value) || value.schema_version !== 1) {
    throw new Error("Format code must be a version 1 format object.");
  }
  if (value.selection === null) return EMPTY_FORMAT;
  if (!isObject(value.selection) || !modes.has(value.selection.mode as CreationMode)) {
    throw new Error("Format code has an invalid creation mode.");
  }
  const mode = value.selection.mode as CreationMode;
  const options = value.selection.options;
  if (!isObject(options) || !eventFormats.has(options.event_format as EventFormat)) {
    throw new Error("Format code must choose singles or doubles.");
  }
  if (!Number.isInteger(options.entrant_count) || Number(options.entrant_count) <= 0) {
    throw new Error("Format code must include a positive entrant count.");
  }
  if (options.variant !== null && typeof options.variant !== "string") {
    throw new Error("Format code has an invalid layout variant.");
  }
  const rawStyle = options.podium_style;
  if (mode === "podium" && !podiumStyles.has(rawStyle as PodiumStyle)) {
    throw new Error("Podium formats must choose legacy or customizable styling.");
  }
  if (mode !== "podium" && rawStyle !== null) {
    throw new Error("Only podium formats can include a podium style.");
  }
  return {
    schema_version: 1,
    selection: {
      mode,
      options: {
        event_format: options.event_format as EventFormat,
        entrant_count: Number(options.entrant_count),
        variant: options.variant as string | null,
        podium_style: rawStyle as PodiumStyle | null,
      },
    },
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
    return normalizeFormat(format).selection !== null;
  } catch {
    return false;
  }
}

export function formatCode(format: FormatConfiguration): string {
  return JSON.stringify(format, null, 2);
}


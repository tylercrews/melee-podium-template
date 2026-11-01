import type { FormatConfiguration, TextSettings } from "./format";

/**
 * Text settings drawn only by the tournament header. Changing them, the header
 * assignment, or the tournament details replaces just the header layers of an
 * exact preview; every other setting needs a complete server render.
 */
export const HEADER_TEXT_SETTINGS = [
  "heading_color",
  "heading_metallic",
  "title_font_size_adjustment",
  "subtitle_font_size_adjustment",
  "metadata_row_font_size_adjustments",
  "metadata_rows",
  "replace_base_urls_with_icons",
] as const satisfies ReadonlyArray<keyof TextSettings>;

export interface ExactPreviewInputs {
  format: FormatConfiguration;
  fontId: string | null;
  /** Completed tournament details, or null while the server uses sample data. */
  tournament: unknown;
  /** Completed visible entrants, or null while the server uses sample data. */
  entrants: unknown;
  visibility: unknown;
  logoId: string | null;
}

export interface ExactPreviewKeys {
  contentKey: string;
  headerKey: string;
}

/** Background and (outside Radial) logo changes need neither key: the browser draws them. */
export function exactPreviewKeys({ format, fontId, tournament, entrants, visibility, logoId }: ExactPreviewInputs): ExactPreviewKeys {
  const headerFields = new Set<string>(HEADER_TEXT_SETTINGS);
  const textEntries = Object.entries(format.text_settings);
  // Radial draws its logo on the server, and its attribution samples the
  // finished composite, so its logo and placement require a full render.
  const radialLogo = format.selection.mode === "radial" && logoId
    ? { logoId, logoSize: format.image_settings.logo_size, headerLayout: format.header_layout }
    : null;
  return {
    contentKey: JSON.stringify({
      selection: format.selection,
      formattingColors: format.formatting_asset_colors,
      entrantTextColors: format.entrant_text_colors,
      text: Object.fromEntries(textEntries.filter(([key]) => !headerFields.has(key))),
      fontId,
      entrants,
      visibility,
      radialLogo,
    }),
    headerKey: JSON.stringify({
      headerLayout: format.header_layout,
      text: Object.fromEntries(textEntries.filter(([key]) => headerFields.has(key))),
      tournament,
    }),
  };
}

/** Swap header layers in stack order, or return null when the counts disagree. */
export function replaceHeaderLayers<T extends { kind: string }>(layers: readonly T[], headers: readonly T[]): T[] | null {
  if (layers.filter((layer) => layer.kind === "header").length !== headers.length) return null;
  let index = 0;
  return layers.map((layer) => layer.kind === "header" ? headers[index++] : layer);
}

/** Interleave the browser-drawn logo beneath the layer at ``logoIndex``. */
export function layersWithLogo<T>(layers: readonly T[], logoIndex: number): Array<T | "logo"> {
  const index = Math.max(0, Math.min(logoIndex, layers.length));
  return [...layers.slice(0, index), "logo", ...layers.slice(index)];
}

export function dataUrlBlob(dataUrl: string): Blob {
  const separator = dataUrl.indexOf(",");
  const header = dataUrl.slice(0, separator);
  const binary = atob(dataUrl.slice(separator + 1));
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return new Blob([bytes], { type: header.slice("data:".length).split(";")[0] });
}

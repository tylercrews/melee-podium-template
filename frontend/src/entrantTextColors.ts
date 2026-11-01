import type { MatchedEntrantTextColors } from "./api";
import { EntrantTextColorSelectionMode, EntrantTextColors, FormatConfiguration, hasValidEntrantCount } from "./format";

/** Resolves each entrant's text color and Metallic finish under Match podium color selection. */
export type MatchEntrantTextColors = (payload: object) => Promise<MatchedEntrantTextColors>;

export function entrantTextColorCount(mode: EntrantTextColorSelectionMode, entrantCount: number): number {
  return mode === "match_podium" ? 0 : mode === "pick_1" ? 1 : mode === "pick_2" ? 2 : entrantCount;
}

/** The layout and palette the renderer needs to resolve matched colors; null until the layout is chosen. */
export function matchedEntrantTextColorsRequest(format: FormatConfiguration): object | null {
  const { mode, options } = format.selection;
  if (!hasValidEntrantCount(format.selection) || (mode === "podium" && !options.podium_style)) return null;
  return { mode, style: options.podium_style ?? "legacy", event_format: options.event_format, entrant_count: options.entrant_count,
    variant: options.variant, formatting_asset_colors: format.formatting_asset_colors };
}

/**
 * Resize entrant text colors for a selection mode. Colors the user already
 * picked keep their slots; new slots start from the matched colors, so
 * leaving Match podium color selection keeps the image unchanged until edited.
 */
export function seedEntrantTextColors(current: EntrantTextColors, mode: EntrantTextColorSelectionMode, entrantCount: number,
  matched: MatchedEntrantTextColors | null, fallback: (index: number) => string): EntrantTextColors {
  const count = entrantTextColorCount(mode, entrantCount);
  return {
    mode,
    colors: Array.from({ length: count }, (_, index) => current.colors[index] ?? matched?.colors[index] ?? fallback(index)),
    metallic: Array.from({ length: count }, (_, index) => current.metallic[index] ?? matched?.metallic[index] ?? false),
  };
}

import type { FormatConfiguration, FormatSelection } from "./format";

/** Flying V Singles can flip top to bottom: first place leads from the top. */
export const FLYING_V_VERTICALLY_REVERSED = "vertically_reversed";
/** Flying V Singles can mirror second place's label to the other side of its area. */
export const FLYING_V_SECOND_PLACE_FLIPPED = "second_place_flipped";

/** Each combination of the two Singles layout checkboxes is its own layout variant. */
export function flyingVSinglesVariant(verticallyReversed: boolean, secondPlaceFlipped: boolean): string | null {
  const parts = [verticallyReversed && FLYING_V_VERTICALLY_REVERSED, secondPlaceFlipped && FLYING_V_SECOND_PLACE_FLIPPED].filter(Boolean);
  return parts.length ? parts.join("_") : null;
}

export const FLYING_V_SINGLES_VARIANTS = [false, true].flatMap((reversed) =>
  [false, true].map((flipped) => flyingVSinglesVariant(reversed, flipped)));

function isFlyingVSingles(selection: FormatSelection): boolean {
  return selection.mode === "flying_v" && selection.options.event_format === "singles";
}

export function isFlyingVVerticallyReversed(selection: FormatSelection): boolean {
  return isFlyingVSingles(selection) && (selection.options.variant ?? "").startsWith(FLYING_V_VERTICALLY_REVERSED);
}

export function isFlyingVSecondPlaceFlipped(selection: FormatSelection): boolean {
  return isFlyingVSingles(selection) && (selection.options.variant ?? "").endsWith(FLYING_V_SECOND_PLACE_FLIPPED);
}

function withSinglesVariant(format: FormatConfiguration, reversed: boolean, flipped: boolean): FormatConfiguration {
  const { selection } = format;
  if (!isFlyingVSingles(selection)) return format;
  return { ...format, selection: { ...selection, options: { ...selection.options, variant: flyingVSinglesVariant(reversed, flipped) } } };
}

/** Toggle the reversed Singles layout, keeping second place's side; other selections are returned unchanged. */
export function setFlyingVVerticallyReversed(format: FormatConfiguration, reversed: boolean): FormatConfiguration {
  return withSinglesVariant(format, reversed, isFlyingVSecondPlaceFlipped(format.selection));
}

/** Mirror second place's label to the other side, keeping the orientation; other selections are returned unchanged. */
export function setFlyingVSecondPlaceFlipped(format: FormatConfiguration, flipped: boolean): FormatConfiguration {
  return withSinglesVariant(format, isFlyingVVerticallyReversed(format.selection), flipped);
}

/** Cached placeholder and numbering layers are keyed by the full layout, including every variant. */
export function flyingVLayoutId(selection: FormatSelection): string {
  if (selection.options.event_format === "doubles") return "doubles_top_3";
  const variant = flyingVSinglesVariant(isFlyingVVerticallyReversed(selection), isFlyingVSecondPlaceFlipped(selection));
  return variant ? `singles_top_8_${variant}` : "singles_top_8";
}

/** Header layers depend on bracket type and orientation, not entrant data or second place's side. */
export function flyingVHeaderGeometryId(selection: FormatSelection): string {
  if (selection.options.event_format === "doubles") return "doubles";
  return isFlyingVVerticallyReversed(selection) ? "singles_vertically_reversed" : "singles";
}

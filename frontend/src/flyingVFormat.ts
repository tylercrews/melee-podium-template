import type { FormatConfiguration, FormatSelection } from "./format";

/** Flying V Singles can flip top to bottom: first place leads from the top. */
export const FLYING_V_VERTICALLY_REVERSED = "vertically_reversed";

export function isFlyingVVerticallyReversed(selection: FormatSelection): boolean {
  return selection.mode === "flying_v" && selection.options.event_format === "singles"
    && selection.options.variant === FLYING_V_VERTICALLY_REVERSED;
}

/** Toggle the reversed Singles layout; other selections are returned unchanged. */
export function setFlyingVVerticallyReversed(format: FormatConfiguration, reversed: boolean): FormatConfiguration {
  const { selection } = format;
  if (selection.mode !== "flying_v" || selection.options.event_format !== "singles") return format;
  return { ...format, selection: { ...selection, options: { ...selection.options, variant: reversed ? FLYING_V_VERTICALLY_REVERSED : null } } };
}

/** Cached placeholder and numbering layers are keyed by the full layout, including orientation. */
export function flyingVLayoutId(selection: FormatSelection): string {
  if (selection.options.event_format === "doubles") return "doubles_top_3";
  return isFlyingVVerticallyReversed(selection) ? "singles_top_8_vertically_reversed" : "singles_top_8";
}

/** Header layers depend on bracket type and orientation, not entrant data. */
export function flyingVHeaderGeometryId(selection: FormatSelection): string {
  if (selection.options.event_format === "doubles") return "doubles";
  return isFlyingVVerticallyReversed(selection) ? "singles_vertically_reversed" : "singles";
}

import type { FormatConfiguration } from "./format";
import { clappingGridLayout } from "./clappingGrid";

export function placementRank(slot: number, tournament = true): number {
  if (!Number.isInteger(slot) || slot < 1) throw new Error("Placement slot must be a positive integer.");
  if (!tournament || slot <= 4) return slot;
  const base = 2 ** Math.floor(Math.log2(slot - 1));
  const group = base / 2;
  return base + 1 + Math.floor((slot - 1 - base) / group) * group;
}

/** Match the representative canvas used while the user's layout choices are incomplete. */
export function placementNumberPreviewPath(format: FormatConfiguration): string {
  const { mode, options } = format.selection;
  const event = options.event_format ?? "singles";
  let count = options.entrant_count ?? (event === "doubles" ? (mode === "radial" ? 4 : 3) : 8);
  let variant = "";
  let style = "";
  if (mode === "podium") {
    style = `${options.podium_style ?? "legacy"}/`;
    if (options.variant === "four_podium") { count = 8; variant = "_four_podium"; }
    else if (options.variant === "clapping" && count === 16) variant = "_clapping";
    else if (clappingGridLayout(format.selection)) variant = `_${options.variant}`;
    else if (![3, 4, 8].includes(count)) count = 8;
  }
  const numbering = format.text_settings.use_tournament_placing !== false ? "tournament" : "sequential";
  return `placement_numbers/${mode}/${style}${event}_top_${count}${variant}/${numbering}.png`;
}

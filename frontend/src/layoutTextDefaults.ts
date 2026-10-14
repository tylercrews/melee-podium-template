import type { FormatSelection, MetadataField, TextSettings } from "./format";
import { clappingGridLayout } from "./clappingGrid";

export function isPrLayout(selection: FormatSelection): boolean {
  return (selection.mode === "eyes" && [10, 15, 20, 25].includes(selection.options.entrant_count ?? 0))
    || !!clappingGridLayout(selection);
}

export function layoutTextDefaults(base: TextSettings, selection: FormatSelection): TextSettings {
  const pr = isPrLayout(selection);
  const metadata_rows: MetadataField[][] = pr ? [["event"], ["date_range"], ["entrants_count"]]
    : [["tournament_link"], ["event"], ["date"], ["entrants_count"]];
  return { ...base, include_seeding: !pr, use_tournament_placing: !pr,
    metadata_rows, metadata_row_font_size_adjustments: metadata_rows.map(() => 0) };
}

export function transitionLayoutTextSettings(settings: TextSettings, previous: FormatSelection, next: FormatSelection): TextSettings {
  if (isPrLayout(previous) === isPrLayout(next)) return settings;
  const pr = isPrLayout(next);
  const seen = new Set<MetadataField>();
  const rows: MetadataField[][] = [];
  const sizes: number[] = [];
  settings.metadata_rows.forEach((row, index) => {
    const fields = row.flatMap((field): MetadataField[] => {
      if (pr && field === "tournament_link") return [];
      const renamed = pr && field === "date" ? "date_range" : !pr && field === "date_range" ? "date" : field;
      if (seen.has(renamed)) return [];
      seen.add(renamed);
      return [renamed];
    });
    if (fields.length) { rows.push(fields); sizes.push(settings.metadata_row_font_size_adjustments[index] ?? 0); }
  });
  if (!pr && !seen.has("tournament_link")) {
    if (rows.length < 5) { rows.unshift(["tournament_link"]); sizes.unshift(0); }
    else rows[0].unshift("tournament_link");
  }
  return { ...settings, include_seeding: !pr, use_tournament_placing: !pr,
    metadata_rows: rows, metadata_row_font_size_adjustments: sizes };
}

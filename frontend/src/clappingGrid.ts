import layouts from "../../clapping_grid_layouts.json";
import type { FormatSelection } from "./format";

export const CLAPPING_GRID_LAYOUTS = layouts;
export const clappingGridVariant = (columns: number): string => `clapping_grid_${columns}`;

export function clappingGridLayout(selection: FormatSelection) {
  if (selection.mode !== "podium" || selection.options.podium_style !== "customizable" || selection.options.event_format !== "singles") return undefined;
  return layouts.find((layout) => layout.entrant_count === selection.options.entrant_count
    && clappingGridVariant(layout.columns) === selection.options.variant);
}

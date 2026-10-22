import catalog from "./quickPicks.json";
import { DEFAULT_HEADER_LAYOUT, EMPTY_FORMAT, FormatConfiguration, buildBackgroundPlacement, defaultTextSettings, formatCanvasSize, normalizeFormat } from "./format";

export const QUICK_PICKS = catalog;
const BATTLEFIELD_ID = "builtin:00_Battlefield_5000_5000_resaved.png";

export function quickPickLayoutLabel(pick: typeof QUICK_PICKS[number]): string {
  if (pick.mode === "podium") {
    if (pick.variant === "four_podium" || pick.variant?.startsWith("clapping_grid_")) return "Podiums+Clapping";
    return pick.podium_style === "customizable" ? "Customizable Podiums" : "Legacy Podiums";
  }
  return pick.mode === "eyes" ? "Eyes" : pick.mode === "radial" ? "Radial" : pick.mode === "flying_v" ? "Flying V" : "Squares";
}

/** Return independent, serializable settings through the saved-format boundary. */
export function quickPickFormat(id: string): FormatConfiguration {
  const pick = QUICK_PICKS.find((item) => item.id === id);
  if (!pick) throw new Error("Unknown Quick Pick format.");
  const format = normalizeFormat({
    ...EMPTY_FORMAT,
    selection: {
      mode: pick.mode,
      options: {
        event_format: pick.event_format,
        entrant_count: pick.entrant_count,
        variant: pick.variant ?? null,
        animated: pick.animated ?? false,
        podium_style: pick.podium_style ?? null,
      },
    },
    // Flying V's middle position is its top-center title box, so it keeps its own default.
    header_layout: pick.mode === "flying_v" ? { ...DEFAULT_HEADER_LAYOUT }
      : { top_left: "tournament_title", top_middle: "tournament_logo", top_right: "metadata" },
    text_settings: { ...EMPTY_FORMAT.text_settings, font_asset_id: "provided:ubuntu" },
  });
  format.text_settings = { ...defaultTextSettings(format.selection), font_asset_id: "provided:ubuntu" };
  const output = formatCanvasSize(format)!;
  const source = { width: 5000, height: 5000 };
  // Fill the canvas without stretching; serialize the resolved scale and crop.
  const scale = Math.max(output.width / source.width, output.height / source.height);
  format.image_settings.background_size = scale;
  format.image_settings.background_placement = buildBackgroundPlacement(BATTLEFIELD_ID, source, output, scale);
  return format;
}

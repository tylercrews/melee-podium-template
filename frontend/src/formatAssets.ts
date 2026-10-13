import { FormatConfiguration, PixelSize, buildBackgroundPlacement, formatCanvasSize } from "./format";

/** Commit asset choices immediately, including while the Format step is closed. */
export function selectFormatBackground(format: FormatConfiguration, background: (PixelSize & { id: string }) | null): FormatConfiguration {
  const output = formatCanvasSize(format);
  return {
    ...format,
    image_settings: {
      ...format.image_settings,
      background_placement: background && output
        ? buildBackgroundPlacement(background.id, background, output, format.image_settings.background_size, format.image_settings.background_placement?.alignment)
        : null,
    },
  };
}

import type { EventFormat, FormatConfiguration } from "./format";

export const RADIAL_LAYOUT_CHOICES = [
  { eventFormat: "singles" as const, entrantCount: 8 },
  { eventFormat: "doubles" as const, entrantCount: 4 },
];

export function selectRadialLayout(format: FormatConfiguration, eventFormat: EventFormat): FormatConfiguration {
  const choice = RADIAL_LAYOUT_CHOICES.find((item) => item.eventFormat === eventFormat);
  if (!choice) throw new Error("Choose Singles Top 8 or Doubles Top 4.");
  return {
    ...format,
    selection: {
      mode: "radial",
      options: { event_format: choice.eventFormat, entrant_count: choice.entrantCount, variant: null, podium_style: null },
    },
  };
}

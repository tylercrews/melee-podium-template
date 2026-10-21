import { selectFixedLayout, type EventFormat, type FormatConfiguration } from "./format";

export const RADIAL_LAYOUT_CHOICES = [
  { eventFormat: "singles" as const, entrantCount: 8 },
  { eventFormat: "doubles" as const, entrantCount: 4 },
];

export function selectRadialLayout(format: FormatConfiguration, eventFormat: EventFormat): FormatConfiguration {
  return selectFixedLayout(format, "radial", eventFormat);
}

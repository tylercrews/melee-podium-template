import { KeyboardEvent, useEffect, useState } from "react";

interface SliderValueInputProps {
  label: string;
  value: number;
  min: number;
  max: number;
  format: (value: number) => string;
  onChange: (value: number) => void;
  /** Rounds a typed value to what the slider stores; whole numbers by default. */
  round?: (value: number) => number;
}

export const formatPercent = (value: number) => `${value}%`;

/** Reads the first number in typed text, ignoring units such as px, %, or ×. */
export function parseSliderNumber(text: string): number | null {
  const match = text.replace(/[−–]/g, "-").replace(",", ".").match(/[-+]?(?:\d+\.?\d*|\.\d+)/);
  return match ? Number(match[0]) : null;
}

/**
 * A slider's value readout that also accepts typing. Enter or leaving the
 * field commits the value, clamped to the slider's range; Escape or text
 * without a number restores the current value.
 */
export default function SliderValueInput({ label, value, min, max, format, onChange, round = Math.round }: SliderValueInputProps) {
  const display = format(value);
  const [draft, setDraft] = useState(display);
  useEffect(() => setDraft(display), [display]);

  function commit() {
    const typed = parseSliderNumber(draft);
    if (typed === null) {
      setDraft(display);
      return;
    }
    const next = Math.min(max, Math.max(min, round(typed)));
    setDraft(format(next));
    if (next !== value) onChange(next);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      // Never submit a surrounding form; the typed value is the only intent.
      event.preventDefault();
      commit();
    } else if (event.key === "Escape") {
      setDraft(display);
    }
  }

  return <input className="slider-value" type="text" inputMode={min < 0 ? "text" : "decimal"} value={draft} onChange={(event) => setDraft(event.target.value)}
    onBlur={commit} onKeyDown={handleKeyDown} spellCheck={false} autoComplete="off" aria-label={`${label} value`} />;
}

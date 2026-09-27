import { FormEvent, useEffect, useState } from "react";

interface RgbaColorPickerProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  metallic?: boolean;
  onMetallicChange?: (value: boolean) => void;
}

const rgbaColor = /^#[0-9a-f]{8}$/i;

export default function RgbaColorPicker({ label, value, onChange, metallic, onMetallicChange }: RgbaColorPickerProps) {
  const [draft, setDraft] = useState(value);
  useEffect(() => setDraft(value), [value]);
  const alpha = Number.parseInt(value.slice(7, 9), 16);

  function commitDraft(event?: FormEvent) {
    event?.preventDefault();
    if (rgbaColor.test(draft)) onChange(draft.toUpperCase());
    else setDraft(value);
  }

  return <div className="rgba-picker">
    <div className="rgba-picker__heading"><span className="rgba-picker__label">{label}</span>{onMetallicChange && <label className="rgba-picker__metallic"><input type="checkbox" checked={metallic ?? false} onChange={(event) => onMetallicChange(event.target.checked)} /><span>Metallic</span></label>}</div>
    <div className="rgba-picker__controls">
      <label className="rgba-picker__swatch" title="Choose the RGB color"><input type="color" value={value.slice(0, 7)} onChange={(event) => onChange(`${event.target.value}${value.slice(7, 9)}`.toUpperCase())} /><span style={{ background: value }} /></label>
      <form onSubmit={commitDraft}><label>RGBA hex<input value={draft} onChange={(event) => setDraft(event.target.value)} onBlur={() => commitDraft()} maxLength={9} spellCheck={false} aria-label={`${label} RGBA hex value`} /></label></form>
      <label className="rgba-picker__alpha">Opacity <span>{Math.round(alpha / 255 * 100)}%</span><input type="range" min="0" max="255" value={alpha} onChange={(event) => onChange(`${value.slice(0, 7)}${Number(event.target.value).toString(16).padStart(2, "0")}`.toUpperCase())} /></label>
    </div>
  </div>;
}


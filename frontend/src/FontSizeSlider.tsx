interface Props {
  label: string;
  value: number;
  onChange: (value: number) => void;
}

export default function FontSizeSlider({ label, value, onChange }: Props) {
  return <label className="font-size-slider">
    <span><strong>{label}</strong><output>{value > 0 ? "+" : ""}{value}px</output></span>
    <input aria-label={label} type="range" min="-20" max="20" step="1" value={value} onChange={(event) => onChange(Number(event.target.value))} />
    <span className="font-size-slider__marks" aria-hidden="true"><span>−20px</span><span>0</span><span>+20px</span></span>
  </label>;
}

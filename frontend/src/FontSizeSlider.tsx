import SliderValueInput from "./SliderValueInput";

interface Props {
  label: string;
  value: number;
  onChange: (value: number) => void;
}

const pixelLabel = (value: number) => `${value > 0 ? "+" : ""}${value}px`;

export default function FontSizeSlider({ label, value, onChange }: Props) {
  return <label className="font-size-slider">
    <span><strong>{label}</strong><SliderValueInput label={label} value={value} min={-20} max={20} format={pixelLabel} onChange={onChange} /></span>
    <input aria-label={label} type="range" min="-20" max="20" step="1" value={value} onChange={(event) => onChange(Number(event.target.value))} />
    <span className="font-size-slider__marks" aria-hidden="true"><span>−20px</span><span>0</span><span>+20px</span></span>
  </label>;
}

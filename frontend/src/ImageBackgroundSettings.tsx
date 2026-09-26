import { useEffect } from "react";
import BackgroundPositionDialog, { FormatImageInfo } from "./BackgroundPositionDialog";
import RgbaColorPicker from "./RgbaColorPicker";
import { BackgroundSizeOption, FormatConfiguration, buildBackgroundPlacement, backgroundSizeValue, formatCanvasSize } from "./format";

interface ImageBackgroundSettingsProps {
  value: FormatConfiguration;
  backgroundImage: FormatImageInfo | null;
  onChange: (value: FormatConfiguration) => void;
}

const sliderPosition = (multiplier: number) => Math.round(Math.log10(Math.min(10, Math.max(.1, multiplier))) * 100);
const sliderMultiplier = (position: number) => Number((10 ** (position / 100)).toFixed(3));
const multiplierLabel = (multiplier: number) => `${multiplier < 1 ? multiplier.toFixed(2).replace(/0+$/, "").replace(/\.$/, "") : multiplier.toFixed(2).replace(/0+$/, "").replace(/\.$/, "")}×`;

interface SizeSliderProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
}

function SizeSlider({ label, value, onChange }: SizeSliderProps) {
  return <label className="size-slider">
    <span className="size-slider__heading"><strong>{label}</strong><output>{multiplierLabel(value)}</output></span>
    <input type="range" min="-100" max="100" step="1" value={sliderPosition(value)} onChange={(event) => onChange(sliderMultiplier(Number(event.target.value)))} />
    <span className="size-slider__marks" aria-hidden="true"><span>0.1×</span><span>1×</span><span>10×</span></span>
  </label>;
}

export default function ImageBackgroundSettings({ value, backgroundImage, onChange }: ImageBackgroundSettingsProps) {
  const settings = value.image_settings;
  const outputSize = formatCanvasSize(value);

  useEffect(() => {
    const placement = settings.background_placement;
    if (!backgroundImage) {
      if (placement) onChange({ ...value, image_settings: { ...settings, background_placement: null } });
      return;
    }
    if (!outputSize) return;
    const sourceChanged = placement?.asset_id !== backgroundImage.id || placement?.source_size.width !== backgroundImage.width || placement?.source_size.height !== backgroundImage.height;
    const outputChanged = placement?.output_size.width !== outputSize.width || placement?.output_size.height !== outputSize.height;
    if (!placement || sourceChanged || outputChanged || placement.size_option !== settings.background_size) {
      onChange({ ...value, image_settings: { ...settings, background_placement: buildBackgroundPlacement(backgroundImage.id, backgroundImage, outputSize, settings.background_size, placement?.alignment) } });
    }
  }, [backgroundImage, onChange, outputSize, settings, value]);

  function updateSettings(update: Partial<typeof settings>) {
    onChange({ ...value, image_settings: { ...settings, ...update } });
  }

  function updateBackgroundSize(background_size: BackgroundSizeOption) {
    updateSettings({
      background_size,
      background_placement: backgroundImage && outputSize
        ? buildBackgroundPlacement(backgroundImage.id, backgroundImage, outputSize, background_size, settings.background_placement?.alignment)
        : null,
    });
  }

  const backgroundMultiplier = typeof settings.background_size === "number"
    ? settings.background_size
    : backgroundImage && outputSize
      ? backgroundSizeValue(settings.background_size, backgroundImage, outputSize)
      : 1;

  return <>
    <section className="format-settings-card" aria-labelledby="image-background-heading">
      <div className="format-settings-card__heading"><span className="eyebrow">Canvas assets</span><h2 id="image-background-heading">Image and Background Settings</h2><p>Set the canvas color and scale the logo and background selected in the Images step.</p></div>
      <RgbaColorPicker label="Background Color" value={settings.background_color} onChange={(background_color) => updateSettings({ background_color })} />
      <div className="image-size-settings">
        <SizeSlider label="Tournament logo size" value={settings.logo_size} onChange={(logo_size) => updateSettings({ logo_size })} />
        <div className="background-size-control">
          <SizeSlider label="Background image size" value={backgroundMultiplier} onChange={updateBackgroundSize} />
          <div className="background-fit-actions"><button className={`button button--outline${settings.background_size === "scale_to_width" ? " is-selected" : ""}`} type="button" onClick={() => updateBackgroundSize("scale_to_width")}>Scale to width</button><button className={`button button--outline${settings.background_size === "scale_to_height" ? " is-selected" : ""}`} type="button" onClick={() => updateBackgroundSize("scale_to_height")}>Scale to height</button></div>
        </div>
      </div>
      <div className="background-position-control"><div><strong>Background position</strong><span>{!backgroundImage ? "Select a background in the Images step to position it." : !outputSize ? "Choose a podium style before positioning the background." : "Drag the image or crop window to control the final framing."}</span></div>{backgroundImage && outputSize ? <BackgroundPositionDialog image={backgroundImage} outputSize={outputSize} multiplier={settings.background_size} value={settings.background_placement} onChange={(background_placement) => updateSettings({ background_placement })} /> : <button className="button button--outline" type="button" disabled>Choose position</button>}</div>
    </section>
  </>;
}

import { useEffect } from "react";
import BackgroundPositionDialog, { FormatImageInfo } from "./BackgroundPositionDialog";
import RgbaColorPicker from "./RgbaColorPicker";
import { BackgroundSizeOption, FormatConfiguration, SizeMultiplier, buildBackgroundPlacement, formatCanvasSize } from "./format";

interface ImageBackgroundSettingsProps {
  value: FormatConfiguration;
  backgroundImage: FormatImageInfo | null;
  onChange: (value: FormatConfiguration) => void;
}

const multiplierOptions: Array<{ value: SizeMultiplier; label: string }> = [
  { value: "1/4x", label: "¼×" },
  { value: "1/3x", label: "⅓×" },
  { value: "1/2x", label: "½×" },
  { value: "1x", label: "1×" },
  { value: "2x", label: "2×" },
  { value: "3x", label: "3×" },
  { value: "4x", label: "4×" },
];

const backgroundSizeOptions: Array<{ value: BackgroundSizeOption; label: string; className?: string }> = [
  ...multiplierOptions,
  { value: "scale_to_width", label: "Scale to width", className: "is-fit-width" },
  { value: "scale_to_height", label: "Scale to height", className: "is-fit-height" },
];

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

  return <>
    <section className="format-settings-card" aria-labelledby="image-background-heading">
      <div className="format-settings-card__heading"><span className="eyebrow">Canvas assets</span><h2 id="image-background-heading">Image and Background Settings</h2><p>Set the canvas color and scale the logo and background selected in the Images step.</p></div>
      <RgbaColorPicker label="Background Color" value={settings.background_color} onChange={(background_color) => updateSettings({ background_color })} />
      <div className="image-size-settings">
        <fieldset className="multiplier-control"><legend>Tournament logo size</legend><div>{multiplierOptions.map((option) => <label key={option.value}><input type="radio" name="logo-size" value={option.value} checked={settings.logo_size === option.value} onChange={() => updateSettings({ logo_size: option.value })} /><span>{option.label}</span></label>)}</div></fieldset>
        <fieldset className="multiplier-control"><legend>Background image size</legend><div className="background-size-options">{backgroundSizeOptions.map((option) => <label className={option.className} key={option.value}><input type="radio" name="background-size" value={option.value} checked={settings.background_size === option.value} onChange={() => updateBackgroundSize(option.value)} /><span>{option.label}</span></label>)}</div></fieldset>
      </div>
      <div className="background-position-control"><div><strong>Background position</strong><span>{!backgroundImage ? "Select a background in the Images step to position it." : !outputSize ? "Choose a podium style before positioning the background." : "Drag the image or crop window to control the final framing."}</span></div>{backgroundImage && outputSize ? <BackgroundPositionDialog image={backgroundImage} outputSize={outputSize} multiplier={settings.background_size} value={settings.background_placement} onChange={(background_placement) => updateSettings({ background_placement })} /> : <button className="button button--outline" type="button" disabled>Choose position</button>}</div>
    </section>
    {value.selection.options.podium_style === "customizable" && <section className="format-settings-card customizable-podium-stub"><span className="stub-step__number">Coming next</span><h2>Customizable podium settings</h2><p>Podium color modes and metallic styling will be configured here.</p></section>}
  </>;
}

import { useEffect } from "react";
import RgbaColorPicker from "./RgbaColorPicker";
import { FormatConfiguration, FormattingAssetColor, FormattingAssetColors, FormattingColorPreset, FormattingColorSelectionMode, formattingAssetCount } from "./format";

interface FormattingAssetColorSettingsProps {
  value: FormatConfiguration;
  onChange: (value: FormatConfiguration) => void;
}

const DEFAULT_COLORS: FormattingAssetColor[] = [
  { main_color: "#E53935FF", face_color: "#8E1B18FF", base_color: "#000000FF", metallic: false },
  { main_color: "#2878E8FF", face_color: "#174B94FF", base_color: "#000000FF", metallic: false },
  { main_color: "#F5C542FF", face_color: "#96731CFF", base_color: "#000000FF", metallic: false },
  { main_color: "#35B75AFF", face_color: "#1B7136FF", base_color: "#000000FF", metallic: false },
  { main_color: "#F18432FF", face_color: "#99491AFF", base_color: "#000000FF", metallic: false },
  { main_color: "#22BFC7FF", face_color: "#14757AFF", base_color: "#000000FF", metallic: false },
  { main_color: "#C23ECFFF", face_color: "#75247DFF", base_color: "#000000FF", metallic: false },
  { main_color: "#858B99FF", face_color: "#50545EFF", base_color: "#000000FF", metallic: false },
];

const choices: Array<{ value: FormattingColorSelectionMode; label: string }> = [
  { value: "premade", label: "Premade" },
  { value: "pick_1", label: "Pick 1" },
  { value: "pick_2", label: "Pick 2" },
  { value: "pick_all", label: "Pick all" },
];

const presets: Array<{ value: FormattingColorPreset; label: string }> = [
  { value: "smash_player_colors", label: "Smash Player Colors" },
  { value: "olympic_medals", label: "Olympic Medals" },
  { value: "rainbow", label: "Rainbow" },
];

function resizeColors(colors: FormattingAssetColor[], count: number): FormattingAssetColor[] {
  return Array.from({ length: count }, (_, index) => ({ ...(colors[index] ?? DEFAULT_COLORS[index % DEFAULT_COLORS.length]) }));
}

export default function FormattingAssetColorSettings({ value, onChange }: FormattingAssetColorSettingsProps) {
  const configuration = value.formatting_asset_colors;
  const assetCount = formattingAssetCount(value);
  const requiredCount = configuration.mode === "pick_1" ? 1 : configuration.mode === "pick_2" ? 2 : configuration.mode === "pick_all" ? assetCount : 0;

  useEffect(() => {
    if (configuration.mode !== "premade" && configuration.colors.length !== requiredCount) {
      onChange({ ...value, formatting_asset_colors: { ...configuration, colors: resizeColors(configuration.colors, requiredCount) } });
    }
  }, [configuration, onChange, requiredCount, value]);

  function setConfiguration(formatting_asset_colors: FormattingAssetColors) {
    onChange({ ...value, formatting_asset_colors });
  }

  function selectMode(mode: FormattingColorSelectionMode) {
    if (mode === "premade") {
      setConfiguration({ mode, preset: configuration.preset ?? "smash_player_colors", colors: [] });
      return;
    }
    const count = mode === "pick_1" ? 1 : mode === "pick_2" ? 2 : assetCount;
    setConfiguration({ mode, preset: null, colors: resizeColors(configuration.colors, count) });
  }

  function updateColor(index: number, field: "main_color" | "face_color" | "base_color", color: string) {
    const colors = resizeColors(configuration.colors, requiredCount);
    colors[index] = { ...colors[index], [field]: color };
    setConfiguration({ ...configuration, colors });
  }

  return <section className="format-settings-card formatting-colors" aria-labelledby="formatting-colors-heading">
    <div className="format-settings-card__heading"><span className="eyebrow">Formatting assets</span><h2 id="formatting-colors-heading">Color customization</h2><p>Choose a ready-made palette or set the colors used by each formatting asset.</p></div>
    <label className="formatting-colors__select">How do you want to pick colors?<select value={configuration.mode} onChange={(event) => selectMode(event.target.value as FormattingColorSelectionMode)}>{choices.map((choice) => <option value={choice.value} key={choice.value}>{choice.label}</option>)}</select></label>
    {configuration.mode === "premade" ? <label className="formatting-colors__select">Premade palette<select value={configuration.preset ?? "smash_player_colors"} onChange={(event) => setConfiguration({ mode: "premade", preset: event.target.value as FormattingColorPreset, colors: [] })}>{presets.map((preset) => <option value={preset.value} key={preset.value}>{preset.label}</option>)}</select></label> : <div className="formatting-color-sets">
      {resizeColors(configuration.colors, requiredCount).map((colors, index) => <section className="formatting-color-set" key={index}><div className="formatting-color-set__heading"><span>{configuration.mode === "pick_all" ? `Podium ${index + 1}` : `Color set ${index + 1}`}</span><small>{configuration.mode === "pick_2" ? (index === 0 ? "Odd podiums" : "Even podiums") : configuration.mode === "pick_1" ? "Applied to every podium" : `Formatting asset ${index + 1}`}</small></div><div className="formatting-color-set__pickers"><RgbaColorPicker label="Main Color" value={colors.main_color} onChange={(color) => updateColor(index, "main_color", color)} /><RgbaColorPicker label="Face Color" value={colors.face_color} onChange={(color) => updateColor(index, "face_color", color)} /><RgbaColorPicker label="Sides Color" value={colors.base_color} onChange={(color) => updateColor(index, "base_color", color)} /></div></section>)}
    </div>}
    {configuration.mode === "premade" && configuration.preset === "rainbow" && <p className="formatting-colors__note">Rainbow adapts to the layout: three podiums use red, green, and violet; four podiums use orange, green, blue, and violet.</p>}
  </section>;
}

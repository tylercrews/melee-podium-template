import { useEffect } from "react";
import RgbaColorPicker from "./RgbaColorPicker";
import { EntrantTextColorSelectionMode, FormatConfiguration, FormattingAssetColor, FormattingAssetColors, FormattingColorPreset, FormattingColorSelectionMode, formattingAssetCount } from "./format";

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

const entrantTextChoices: Array<{ value: EntrantTextColorSelectionMode; label: string }> = [
  { value: "match_podium", label: "Match podium color selection" },
  { value: "pick_1", label: "Pick 1" },
  { value: "pick_2", label: "Pick 2" },
  { value: "pick_all", label: "Pick all" },
];

function resizeColors(colors: FormattingAssetColor[], count: number): FormattingAssetColor[] {
  return Array.from({ length: count }, (_, index) => ({ ...(colors[index] ?? DEFAULT_COLORS[index % DEFAULT_COLORS.length]) }));
}

export default function FormattingAssetColorSettings({ value, onChange }: FormattingAssetColorSettingsProps) {
  const configuration = value.formatting_asset_colors;
  const assetCount = formattingAssetCount(value);
  const requiredCount = configuration.mode === "pick_1" ? 1 : configuration.mode === "pick_2" ? 2 : configuration.mode === "pick_all" ? assetCount : 0;
  const entrantConfiguration = value.entrant_text_colors;
  const entrantCount = value.selection.options.entrant_count ?? 3;
  const entrantColorCount = entrantConfiguration.mode === "pick_1" ? 1 : entrantConfiguration.mode === "pick_2" ? 2 : entrantConfiguration.mode === "pick_all" ? entrantCount : 0;

  useEffect(() => {
    const resizeAssets = configuration.mode !== "premade" && configuration.colors.length !== requiredCount;
    const resizeEntrants = entrantConfiguration.colors.length !== entrantColorCount;
    if (resizeAssets || resizeEntrants) {
      onChange({
        ...value,
        formatting_asset_colors: resizeAssets ? { ...configuration, colors: resizeColors(configuration.colors, requiredCount) } : configuration,
        entrant_text_colors: resizeEntrants ? { ...entrantConfiguration, colors: resizeTextColors(entrantConfiguration.colors, entrantColorCount), metallic: resizeMetallic(entrantConfiguration.metallic, entrantColorCount) } : entrantConfiguration,
      });
    }
  }, [configuration, entrantColorCount, entrantConfiguration, onChange, requiredCount, value]);

  function setConfiguration(formatting_asset_colors: FormattingAssetColors) {
    onChange({ ...value, formatting_asset_colors });
  }

  function selectMode(mode: FormattingColorSelectionMode) {
    if (mode === "premade") {
      setConfiguration({ mode, preset: configuration.preset ?? "smash_player_colors", preset_transparency: configuration.preset_transparency, colors: [] });
      return;
    }
    const count = mode === "pick_1" ? 1 : mode === "pick_2" ? 2 : assetCount;
    setConfiguration({ mode, preset: null, preset_transparency: 0, colors: resizeColors(configuration.colors, count) });
  }

  function updateColor(index: number, field: "main_color" | "face_color" | "base_color", color: string) {
    const colors = resizeColors(configuration.colors, requiredCount);
    colors[index] = { ...colors[index], [field]: color };
    setConfiguration({ ...configuration, colors });
  }

  function updatePodiumMetallic(index: number, metallic: boolean) {
    const colors = resizeColors(configuration.colors, requiredCount);
    colors[index] = { ...colors[index], metallic };
    setConfiguration({ ...configuration, colors });
  }

  function selectEntrantTextMode(mode: EntrantTextColorSelectionMode) {
    const count = mode === "match_podium" ? 0 : mode === "pick_1" ? 1 : mode === "pick_2" ? 2 : entrantCount;
    onChange({ ...value, entrant_text_colors: { mode, colors: resizeTextColors(entrantConfiguration.colors, count), metallic: resizeMetallic(entrantConfiguration.metallic, count) } });
  }

  function updateEntrantTextColor(index: number, color: string) {
    const colors = resizeTextColors(entrantConfiguration.colors, entrantColorCount);
    colors[index] = color;
    onChange({ ...value, entrant_text_colors: { ...entrantConfiguration, colors } });
  }

  function updateEntrantTextMetallic(index: number, metallic: boolean) {
    const values = resizeMetallic(entrantConfiguration.metallic, entrantColorCount);
    values[index] = metallic;
    onChange({ ...value, entrant_text_colors: { ...entrantConfiguration, metallic: values } });
  }

  return <section className="format-settings-card formatting-colors" aria-labelledby="formatting-colors-heading">
    <div className="format-settings-card__heading"><span className="eyebrow">Podiums and entrants</span><h2 id="formatting-colors-heading">Color customization</h2><p>Choose podium colors and how entrant text should relate to them.</p></div>
    {value.selection.mode !== "podium" || value.selection.options.podium_style === "customizable" ? <><label className="formatting-colors__select">How do you want to pick colors?<select value={configuration.mode} onChange={(event) => selectMode(event.target.value as FormattingColorSelectionMode)}>{choices.map((choice) => <option value={choice.value} key={choice.value}>{choice.label}</option>)}</select></label>
    {configuration.mode === "premade" ? <div className="formatting-colors__preset"><label className="formatting-colors__select">Premade palette<select value={configuration.preset ?? "smash_player_colors"} onChange={(event) => setConfiguration({ ...configuration, mode: "premade", preset: event.target.value as FormattingColorPreset, colors: [] })}>{presets.map((preset) => <option value={preset.value} key={preset.value}>{preset.label}</option>)}</select></label><label className="formatting-colors__transparency">Transparency <output>{configuration.preset_transparency}%</output><input type="range" min="0" max="100" value={configuration.preset_transparency} onChange={(event) => setConfiguration({ ...configuration, preset_transparency: Number(event.target.value) })} /></label></div> : <div className="formatting-color-sets">
      {resizeColors(configuration.colors, requiredCount).map((colors, index) => <section className="formatting-color-set" key={index}><div className="formatting-color-set__heading"><span>{configuration.mode === "pick_all" ? `Podium ${index + 1}` : `Color set ${index + 1}`}</span><small>{configuration.mode === "pick_2" ? (index === 0 ? "Odd podiums" : "Even podiums") : configuration.mode === "pick_1" ? "Applied to every podium" : `Formatting asset ${index + 1}`}</small></div><div className="formatting-color-set__pickers"><RgbaColorPicker label="Main Color" value={colors.main_color} onChange={(color) => updateColor(index, "main_color", color)} metallic={colors.metallic} onMetallicChange={(metallic) => updatePodiumMetallic(index, metallic)} /><RgbaColorPicker label="Face Color" value={colors.face_color} onChange={(color) => updateColor(index, "face_color", color)} /><RgbaColorPicker label="Sides Color" value={colors.base_color} onChange={(color) => updateColor(index, "base_color", color)} /></div></section>)}
    </div>}
    {configuration.mode === "premade" && configuration.preset === "rainbow" && <p className="formatting-colors__note">Rainbow adapts to the layout: three podiums use red, green, and violet; four podiums use orange, green, blue, and violet.</p>}</> : <p className="formatting-colors__note">Legacy podium artwork uses its built-in podium colors.</p>}
    <div className="entrant-text-colors"><label className="formatting-colors__select">Entrant Text Color<select value={entrantConfiguration.mode} onChange={(event) => selectEntrantTextMode(event.target.value as EntrantTextColorSelectionMode)}>{entrantTextChoices.map((choice) => <option value={choice.value} key={choice.value}>{choice.label}</option>)}</select></label>
      {resizeTextColors(entrantConfiguration.colors, entrantColorCount).map((color, index) => <section className="formatting-color-set" key={index}><div className="formatting-color-set__heading"><span>{entrantConfiguration.mode === "pick_all" ? `Entrant ${index + 1}` : `Text color ${index + 1}`}</span><small>{entrantConfiguration.mode === "pick_2" ? (index === 0 ? "Odd placements" : "Even placements") : entrantConfiguration.mode === "pick_1" ? "Applied to every entrant" : `Placement ${index + 1}`}</small></div><RgbaColorPicker label="Entrant Text Color" value={color} onChange={(nextColor) => updateEntrantTextColor(index, nextColor)} metallic={resizeMetallic(entrantConfiguration.metallic, entrantColorCount)[index]} onMetallicChange={(metallic) => updateEntrantTextMetallic(index, metallic)} /></section>)}
    </div>
  </section>;
}

function resizeTextColors(colors: string[], count: number): string[] {
  return Array.from({ length: count }, (_, index) => colors[index] ?? DEFAULT_COLORS[index % DEFAULT_COLORS.length].main_color);
}

function resizeMetallic(values: boolean[], count: number): boolean[] {
  return Array.from({ length: count }, (_, index) => values[index] ?? false);
}

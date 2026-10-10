import { DEFAULT_RADIAL_HEADER_LAYOUT, CreationMode, EventFormat, FormatConfiguration, HeaderContent, HeaderPosition, PodiumStyle, metadataRowSizeAdjustments } from "./format";
import { FormatImageInfo } from "./BackgroundPositionDialog";
import ImageBackgroundSettings from "./ImageBackgroundSettings";
import EntrantCountSettings from "./EntrantCountSettings";
import { selectRadialLayout } from "./radialFormat";
import FormattingAssetColorSettings from "./FormattingAssetColorSettings";
import RgbaColorPicker from "./RgbaColorPicker";
import MetadataRowEditor from "./MetadataRowEditor";
import FontSizeSlider from "./FontSizeSlider";

interface FormatSettingsProps {
  value: FormatConfiguration;
  backgroundImage: FormatImageInfo | null;
  onChange: (value: FormatConfiguration) => void;
}

const headerPositions: Array<{ value: HeaderPosition; label: string }> = [
  { value: "top_left", label: "Top left" },
  { value: "top_middle", label: "Top middle" },
  { value: "top_right", label: "Top right" },
];

const headerContents: Array<{ value: HeaderContent; label: string }> = [
  { value: "tournament_logo", label: "Tournament logo" },
  { value: "tournament_title", label: "Tournament title" },
  { value: "metadata", label: "Metadata" },
];

export default function FormatSettings({ value, backgroundImage, onChange }: FormatSettingsProps) {
  const { selection } = value;

  function updateMode(mode: CreationMode) {
    onChange({
      ...value,
      selection: {
        ...selection,
        mode,
        options: { ...selection.options, entrant_count: mode === "radial" && selection.options.event_format ? (selection.options.event_format === "singles" ? 8 : 4) : null, variant: null, podium_style: mode === "podium" ? selection.options.podium_style : null },
      },
      header_layout: mode === "radial" ? { ...DEFAULT_RADIAL_HEADER_LAYOUT } : value.header_layout,
    });
  }

  function updateStyle(podium_style: PodiumStyle) {
    onChange({ ...value, selection: { ...selection, options: { ...selection.options, podium_style } } });
  }

  function updateEventFormat(event_format: EventFormat) {
    if (selection.mode === "radial") {
      onChange(selectRadialLayout(value, event_format));
      return;
    }
    onChange({ ...value, selection: { ...selection, options: { ...selection.options, event_format, entrant_count: null, variant: null } } });
  }

  function assignHeader(position: HeaderPosition, content: HeaderContent) {
    const previousContent = value.header_layout[position];
    if (previousContent === content) return;
    const occupiedPosition = headerPositions.find(({ value: candidate }) => value.header_layout[candidate] === content)?.value;
    const header_layout = { ...value.header_layout, [position]: content };
    if (occupiedPosition) header_layout[occupiedPosition] = previousContent;
    onChange({ ...value, header_layout });
  }

  function headerPositionLabel(position: HeaderPosition, fallback: string) {
    if (selection.mode === "radial") return { top_left: "Middle Top", top_middle: "Middle", top_right: "Middle Bottom" }[position];
    const verticalEyes = selection.mode === "eyes"
      && (selection.options.event_format === "doubles" || selection.options.entrant_count === 8);
    if (!verticalEyes) return fallback;
    return {
      top_left: "Top",
      top_middle: "Middle",
      top_right: "Bottom",
    }[position];
  }

  return <div className="format-settings">
    <section className="format-settings-card" aria-labelledby="image-format-heading">
      <div className="format-settings-card__heading"><span className="eyebrow">Format settings</span><h2 id="image-format-heading">Image format</h2><p>Choose the kind of results image, its visual style, and the bracket type.</p></div>
      <fieldset className="format-choice-group"><legend>Image type</legend><div className="format-choice-grid">
        {([
          { value: "podium" as const, label: "Podiums", detail: "Entrants arranged across placement podiums", disabled: false, thumbnail: "podium.webp" },
          { value: "eyes" as const, label: "Eyes", detail: "Close-up portrait strips with placement numbers", disabled: false, thumbnail: "eyes.webp" },
          { value: "squares" as const, label: "Squares", detail: "Portrait cards with customizable borders and backgrounds", disabled: false, thumbnail: "squares.webp" },
          { value: "radial" as const, label: "Radial", detail: "Eight triangular portraits around a central tournament header", disabled: false, thumbnail: "radial.webp" },
        ]).map((option) => <label className={`format-choice format-choice--with-thumbnail${option.disabled ? " format-choice--disabled" : ""}`} key={option.value}><input type="radio" name="image-format" value={option.value} checked={selection.mode === option.value} onChange={() => updateMode(option.value)} disabled={option.disabled} /><span className="format-choice__control" aria-hidden="true" /><span><strong>{option.label}</strong><small>{option.detail}</small></span><img className="format-choice__thumbnail" src={`${import.meta.env.BASE_URL}format_mode_thumbnails/${option.thumbnail}`} alt={`${option.label} example`} /></label>)}
      </div></fieldset>

      {selection.mode === "podium" && <fieldset className="format-choice-group"><legend>Podium style</legend><div className="format-choice-grid">
        {([
          { value: "customizable" as const, label: "Customizable podiums", detail: "Choose colors and styling" },
          { value: "legacy" as const, label: "Legacy podiums", detail: "Use the original podium artwork" },
        ]).map((option) => <label className="format-choice" key={option.value}><input type="radio" name="podium-style" value={option.value} checked={selection.options.podium_style === option.value} onChange={() => updateStyle(option.value)} /><span className="format-choice__control" aria-hidden="true" /><span><strong>{option.label}</strong><small>{option.detail}</small></span></label>)}
      </div></fieldset>}

      <fieldset className="format-choice-group"><legend>Bracket type</legend><div className="format-choice-grid">
        {(["singles", "doubles"] as const).map((eventFormat) => <label className="format-choice" key={eventFormat}><input type="radio" name="event-format" value={eventFormat} checked={selection.options.event_format === eventFormat} onChange={() => updateEventFormat(eventFormat)} /><span className="format-choice__control" aria-hidden="true" /><span><strong>{eventFormat === "singles" ? "Singles" : "Doubles"}</strong><small>{eventFormat === "singles" ? "One player per result" : "Two-player teams"}</small></span></label>)}
      </div></fieldset>
    </section>

    {selection.mode !== "radial" && <EntrantCountSettings value={value} onChange={onChange} />}

    <section className="format-settings-card" aria-labelledby="header-layout-heading">
      <div className="format-settings-card__heading"><span className="eyebrow">Text and header</span><h2 id="header-layout-heading">Content Selections</h2><p>Assign the header positions and choose which supporting details appear in the image.</p></div>
      <div className="format-header-map">
        {headerPositions.map((position) => <label className={`format-header-slot format-header-slot--${position.value}`} key={position.value}><span>{headerPositionLabel(position.value, position.label)}</span><select value={value.header_layout[position.value]} onChange={(event) => assignHeader(position.value, event.target.value as HeaderContent)}>{headerContents.map((content) => <option value={content.value} key={content.value}>{content.label}</option>)}</select><span className="format-header-slot__preview" aria-hidden="true">{headerContents.find((content) => content.value === value.header_layout[position.value])?.label}</span></label>)}
      </div>
      <RgbaColorPicker label="Heading Text Color" value={value.text_settings.heading_color} onChange={(heading_color) => onChange({ ...value, text_settings: { ...value.text_settings, heading_color } })} metallic={value.text_settings.heading_metallic} onMetallicChange={(heading_metallic) => onChange({ ...value, text_settings: { ...value.text_settings, heading_metallic } })} />
      <div className="text-settings">
        <p className="metadata-selector__help">Size sliders add or subtract pixels from the layout's default sizes. Use Refresh Format Preview to see the changes.</p>
        {value.text_settings.font_asset_id.startsWith("user:") && <label className="font-size-slider"><span><strong>Custom font size adjustment</strong><output>{value.text_settings.font_size_adjustment > 0 ? "+" : ""}{value.text_settings.font_size_adjustment}px</output></span><input type="range" min="-20" max="20" step="1" value={value.text_settings.font_size_adjustment} onChange={(event) => onChange({ ...value, text_settings: { ...value.text_settings, font_size_adjustment: Number(event.target.value) } })} /><span className="font-size-slider__marks" aria-hidden="true"><span>−20px</span><span>0</span><span>+20px</span></span></label>}
        <fieldset className="text-preferences"><legend>Preferences</legend><div>
          <label className="text-setting-check"><input type="checkbox" checked={value.text_settings.include_seeding} onChange={(event) => onChange({ ...value, text_settings: { ...value.text_settings, include_seeding: event.target.checked } })} /><span><strong>Include seeding</strong><small>Show each entrant or team's original bracket seed.</small></span></label>
          <label className="text-setting-check"><input type="checkbox" checked={value.text_settings.replace_base_urls_with_icons} onChange={(event) => onChange({ ...value, text_settings: { ...value.text_settings, replace_base_urls_with_icons: event.target.checked } })} /><span><strong>Replace Base URLs With Icons</strong><small>Use service icons for start.gg, YouTube, X, Bluesky, parry.gg, Challonge, and Twitch links.</small></span></label>
        </div></fieldset>
        <FontSizeSlider label="Tournament title size adjustment" value={value.text_settings.title_font_size_adjustment} onChange={(title_font_size_adjustment) => onChange({ ...value, text_settings: { ...value.text_settings, title_font_size_adjustment } })} />
        <FontSizeSlider label="Subtitle size adjustment" value={value.text_settings.subtitle_font_size_adjustment} onChange={(subtitle_font_size_adjustment) => onChange({ ...value, text_settings: { ...value.text_settings, subtitle_font_size_adjustment } })} />
        {value.text_settings.include_seeding && <FontSizeSlider label="Seed size adjustment" value={value.text_settings.seed_font_size_adjustment} onChange={(seed_font_size_adjustment) => onChange({ ...value, text_settings: { ...value.text_settings, seed_font_size_adjustment } })} />}
        <MetadataRowEditor rows={value.text_settings.metadata_rows} onChange={(metadata_rows) => onChange({ ...value, text_settings: { ...value.text_settings, metadata_rows, metadata_row_font_size_adjustments: metadataRowSizeAdjustments(value.text_settings.metadata_rows, value.text_settings.metadata_row_font_size_adjustments, metadata_rows) } })} fontSizeAdjustments={value.text_settings.metadata_row_font_size_adjustments} onFontSizeChange={(index, adjustment) => onChange({ ...value, text_settings: { ...value.text_settings, metadata_row_font_size_adjustments: value.text_settings.metadata_row_font_size_adjustments.map((current, row) => row === index ? adjustment : current) } })} />
      </div>
    </section>
    <ImageBackgroundSettings value={value} backgroundImage={backgroundImage} onChange={onChange} />
    <FormattingAssetColorSettings value={value} onChange={onChange} />
  </div>;
}

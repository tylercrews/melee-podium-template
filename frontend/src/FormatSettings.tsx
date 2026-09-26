import { ALL_METADATA_FIELDS, CreationMode, EventFormat, FormatConfiguration, HeaderContent, HeaderPosition, MetadataField, PodiumStyle } from "./format";
import { FormatImageInfo } from "./BackgroundPositionDialog";
import ImageBackgroundSettings from "./ImageBackgroundSettings";
import EntrantCountSettings from "./EntrantCountSettings";
import FormattingAssetColorSettings from "./FormattingAssetColorSettings";

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

const metadataLabels: Record<MetadataField, string> = {
  event: "Event name",
  date: "Date",
  entrants_count: "Entrant or team count",
  tournament_link: "Tournament link",
  stream_link: "Stream link",
  vod_link: "VOD link",
  to_x_account: "TO X account",
  to_twitch_account: "TO Twitch account",
  to_bluesky_account: "TO Bluesky account",
};

export default function FormatSettings({ value, backgroundImage, onChange }: FormatSettingsProps) {
  const { selection } = value;

  function updateMode(mode: CreationMode) {
    onChange({
      ...value,
      selection: {
        ...selection,
        mode,
        options: { ...selection.options, entrant_count: null, variant: null, podium_style: mode === "podium" ? selection.options.podium_style : null },
      },
    });
  }

  function updateStyle(podium_style: PodiumStyle) {
    onChange({ ...value, selection: { ...selection, options: { ...selection.options, podium_style } } });
  }

  function updateEventFormat(event_format: EventFormat) {
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

  function toggleMetadata(field: MetadataField) {
    const selected = value.text_settings.metadata_fields.includes(field);
    onChange({ ...value, text_settings: { ...value.text_settings, metadata_fields: selected ? value.text_settings.metadata_fields.filter((item) => item !== field) : [...value.text_settings.metadata_fields, field] } });
  }

  return <div className="format-settings">
    <section className="format-settings-card" aria-labelledby="image-format-heading">
      <div className="format-settings-card__heading"><span className="eyebrow">Format settings</span><h2 id="image-format-heading">Image format</h2><p>Choose the kind of results image, its visual style, and the bracket type.</p></div>
      <fieldset className="format-choice-group"><legend>Image type</legend><div className="format-choice-grid format-choice-grid--three">
        {([
          { value: "podium" as const, label: "Podiums", detail: "Entrants arranged across placement podiums", disabled: false },
          { value: "eyes" as const, label: "Eyes", detail: "Coming later", disabled: true },
          { value: "squares" as const, label: "Squares", detail: "Coming later", disabled: true },
        ]).map((option) => <label className={`format-choice${option.disabled ? " format-choice--disabled" : ""}`} key={option.value}><input type="radio" name="image-format" value={option.value} checked={selection.mode === option.value} onChange={() => updateMode(option.value)} disabled={option.disabled} /><span className="format-choice__control" aria-hidden="true" /><span><strong>{option.label}</strong><small>{option.detail}</small></span></label>)}
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

    <EntrantCountSettings value={value} onChange={onChange} />

    <section className="format-settings-card" aria-labelledby="header-layout-heading">
      <div className="format-settings-card__heading"><span className="eyebrow">Header content</span><h2 id="header-layout-heading">Assign the top positions</h2><p>Each item appears exactly once. Choosing an item already assigned elsewhere swaps the two positions.</p></div>
      <div className="format-header-map">
        {headerPositions.map((position) => <label className={`format-header-slot format-header-slot--${position.value}`} key={position.value}><span>{position.label}</span><select value={value.header_layout[position.value]} onChange={(event) => assignHeader(position.value, event.target.value as HeaderContent)}>{headerContents.map((content) => <option value={content.value} key={content.value}>{content.label}</option>)}</select><span className="format-header-slot__preview" aria-hidden="true">{headerContents.find((content) => content.value === value.header_layout[position.value])?.label}</span></label>)}
      </div>
      <div className="text-settings">
        {value.text_settings.font_asset_id.startsWith("user:") && <label className="font-size-slider"><span><strong>Custom font size adjustment</strong><output>{value.text_settings.font_size_adjustment > 0 ? "+" : ""}{value.text_settings.font_size_adjustment}px</output></span><input type="range" min="-20" max="20" step="1" value={value.text_settings.font_size_adjustment} onChange={(event) => onChange({ ...value, text_settings: { ...value.text_settings, font_size_adjustment: Number(event.target.value) } })} /><span className="font-size-slider__marks" aria-hidden="true"><span>−20px</span><span>0</span><span>+20px</span></span></label>}
        <label className="text-setting-check"><input type="checkbox" checked={value.text_settings.replace_base_urls_with_icons} onChange={(event) => onChange({ ...value, text_settings: { ...value.text_settings, replace_base_urls_with_icons: event.target.checked } })} /><span><strong>Replace Base URLs With Icons</strong><small>Use service icons for start.gg, YouTube, X, Bluesky, parry.gg, Challonge, and Twitch links.</small></span></label>
        <fieldset className="metadata-selector"><legend>Metadata Selector</legend><div>{ALL_METADATA_FIELDS.map((field) => <label key={field}><input type="checkbox" checked={value.text_settings.metadata_fields.includes(field)} onChange={() => toggleMetadata(field)} /><span>{metadataLabels[field]}</span></label>)}</div><div className="metadata-selector__actions"><button type="button" onClick={() => onChange({ ...value, text_settings: { ...value.text_settings, metadata_fields: [...ALL_METADATA_FIELDS] } })}>Select all</button><button type="button" onClick={() => onChange({ ...value, text_settings: { ...value.text_settings, metadata_fields: [] } })}>Deselect all</button></div></fieldset>
      </div>
    </section>
    <ImageBackgroundSettings value={value} backgroundImage={backgroundImage} onChange={onChange} />
    {(selection.mode !== "podium" || selection.options.podium_style === "customizable") && <FormattingAssetColorSettings value={value} onChange={onChange} />}
  </div>;
}

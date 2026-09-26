import { EntrantCountOption, FormatConfiguration, entrantCountOptions } from "./format";

interface EntrantCountSettingsProps {
  value: FormatConfiguration;
  onChange: (value: FormatConfiguration) => void;
}

export default function EntrantCountSettings({ value, onChange }: EntrantCountSettingsProps) {
  const options = entrantCountOptions(value.selection);

  function selectOption(option: EntrantCountOption) {
    onChange({
      ...value,
      selection: {
        ...value.selection,
        options: {
          ...value.selection.options,
          entrant_count: option.entrant_count,
          variant: option.variant,
        },
      },
    });
  }

  return <section className="format-settings-card" aria-labelledby="entrant-count-heading">
    <div className="format-settings-card__heading"><span className="eyebrow">Results shown</span><h2 id="entrant-count-heading">Entrants included</h2><p>Choose how many finishing positions appear in the final image.</p></div>
    {!value.selection.options.event_format ? <div className="format-dependent-message">Choose Singles or Doubles above to see the available layouts.</div> : <fieldset className="format-choice-group"><legend>{value.selection.options.event_format === "singles" ? "Singles layouts" : "Doubles layouts"}</legend><div className={`format-choice-grid${options.length > 4 ? " format-choice-grid--many" : ""}`}>
      {options.map((option) => {
        const checked = value.selection.options.entrant_count === option.entrant_count && value.selection.options.variant === option.variant;
        return <label className="format-choice" key={`${option.entrant_count}-${option.variant ?? "standard"}`}><input type="radio" name="entrant-count" checked={checked} onChange={() => selectOption(option)} /><span className="format-choice__control" aria-hidden="true" /><span><strong>{option.label}</strong>{option.detail && <small>{option.detail}</small>}</span></label>;
      })}
    </div></fieldset>}
  </section>;
}

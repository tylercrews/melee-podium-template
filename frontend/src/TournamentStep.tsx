import { METADATA_FIELD_DETAILS, TournamentDetails } from "./creationData";
import { MetadataField } from "./format";

interface TournamentStepProps {
  value: TournamentDetails;
  selectedFields: MetadataField[];
  onChange: (value: TournamentDetails) => void;
}

export default function TournamentStep({ value, selectedFields, onChange }: TournamentStepProps) {
  function update(key: keyof TournamentDetails, nextValue: string) {
    onChange({ ...value, [key]: nextValue });
  }

  return <section className="step-content tournament-step">
    <div className="step-intro"><h1>Tournament Details</h1><p>Review the tournament title and fill in the metadata selected in your format.</p></div>
    <section className="tournament-settings-card" aria-labelledby="tournament-content-heading">
      <div className="tournament-settings-card__heading"><span className="eyebrow">Title content</span><h2 id="tournament-content-heading">Tournament name</h2><p>The title is always used by the header. The subtitle remains optional.</p></div>
      <div className="tournament-field-grid">
        <label className="field tournament-field--wide">Tournament title<input value={value.title} onChange={(event) => update("title", event.target.value)} placeholder="Friday Night Melee" required /></label>
        <label className="field tournament-field--wide">Tournament subtitle <small>Optional</small><input value={value.subtitle} onChange={(event) => update("subtitle", event.target.value)} placeholder="Weekly #42" /></label>
      </div>
    </section>

    <section className="tournament-settings-card" aria-labelledby="selected-metadata-heading">
      <div className="tournament-settings-card__heading"><span className="eyebrow">Format selection</span><h2 id="selected-metadata-heading">Selected metadata</h2><p>Only fields enabled in Content Selections appear here. Imported values can still be edited.</p></div>
      {selectedFields.length ? <div className="tournament-field-grid">{selectedFields.map((field) => {
        const details = METADATA_FIELD_DETAILS[field];
        return <label className={`field${details.type === "url" ? " tournament-field--wide" : ""}`} key={field}>{details.label}<input type={details.type ?? "text"} min={details.type === "number" ? 1 : undefined} value={value[details.key]} onChange={(event) => update(details.key, event.target.value)} placeholder={details.placeholder} required /></label>;
      })}</div> : <div className="tournament-settings-card__empty">No metadata fields are enabled. You can continue with the title alone.</div>}
    </section>
  </section>;
}


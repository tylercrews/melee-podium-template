interface DateRangeFieldsProps {
  start: string;
  end: string;
  onStartChange: (value: string) => void;
  onEndChange: (value: string) => void;
}

export default function DateRangeFields({ start, end, onStartChange, onEndChange }: DateRangeFieldsProps) {
  return <fieldset className="tournament-date-range">
    <legend>Date (Range)</legend>
    <div className="tournament-date-range__fields">
      <label className="field">Start date<input type="date" value={start} max={end || undefined} onChange={(event) => onStartChange(event.target.value)} required /></label>
      <span>to</span>
      <label className="field">End date<input type="date" value={end} min={start || undefined} onChange={(event) => onEndChange(event.target.value)} required /></label>
    </div>
  </fieldset>;
}

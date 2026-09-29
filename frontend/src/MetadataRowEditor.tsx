import { DragEvent, useState } from "react";
import { ALL_METADATA_FIELDS, MAX_METADATA_ROWS, MetadataField } from "./format";

interface MetadataRowEditorProps {
  rows: MetadataField[][];
  onChange: (rows: MetadataField[][]) => void;
}

const labels: Record<MetadataField, string> = {
  event: "Event name",
  date: "Date",
  entrants_count: "Entrant or team count",
  tournament_link: "Tournament link",
  tournament_location: "Tournament location",
  stream_link: "Stream link",
  vod_link: "VOD link",
  to_x_account: "TO X account",
  to_twitch_account: "TO Twitch account",
  to_bluesky_account: "TO Bluesky account",
};

function withoutField(rows: MetadataField[][], field: MetadataField): MetadataField[][] {
  return rows
    .map((row) => row.filter((candidate) => candidate !== field))
    .filter((row) => row.length > 0);
}

export default function MetadataRowEditor({ rows, onChange }: MetadataRowEditorProps) {
  const [draggedField, setDraggedField] = useState<MetadataField | null>(null);
  const selected = new Set(rows.flat());

  function startDragging(event: DragEvent<HTMLElement>, field: MetadataField) {
    setDraggedField(field);
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", field);
  }

  function removeField(field: MetadataField) {
    onChange(withoutField(rows, field));
  }

  function addField(field: MetadataField) {
    if (selected.has(field)) {
      removeField(field);
      return;
    }
    const next = rows.map((row) => [...row]);
    if (next.length < MAX_METADATA_ROWS) next.push([field]);
    else if (next.length > 0) next[next.length - 1].push(field);
    else next.push([field]);
    onChange(next);
  }

  function dropOnRow(event: DragEvent<HTMLElement>, targetRow: number) {
    event.preventDefault();
    if (!draggedField) return;
    const sourceRow = rows.findIndex((row) => row.includes(draggedField));
    if (sourceRow === targetRow) {
      setDraggedField(null);
      return;
    }
    const sourceWillDisappear = sourceRow >= 0 && rows[sourceRow].length === 1;
    const next = withoutField(rows, draggedField);
    const adjustedTarget = sourceWillDisappear && sourceRow < targetRow
      ? targetRow - 1
      : targetRow;
    const destination = Math.max(0, Math.min(adjustedTarget, next.length - 1));
    if (next.length === 0) next.push([draggedField]);
    else next[destination].push(draggedField);
    setDraggedField(null);
    onChange(next);
  }

  function dropAsNewRow(event: DragEvent<HTMLElement>) {
    event.preventDefault();
    if (!draggedField) return;
    const next = withoutField(rows, draggedField);
    if (next.length < MAX_METADATA_ROWS) next.push([draggedField]);
    else if (next.length > 0) next[next.length - 1].push(draggedField);
    else next.push([draggedField]);
    setDraggedField(null);
    onChange(next);
  }

  function moveRow(index: number, offset: -1 | 1) {
    const destination = index + offset;
    if (destination < 0 || destination >= rows.length) return;
    const next = rows.map((row) => [...row]);
    [next[index], next[destination]] = [next[destination], next[index]];
    onChange(next);
  }

  function moveWithinRow(rowIndex: number, fieldIndex: number, offset: -1 | 1) {
    const destination = fieldIndex + offset;
    if (destination < 0 || destination >= rows[rowIndex].length) return;
    const next = rows.map((row) => [...row]);
    [next[rowIndex][fieldIndex], next[rowIndex][destination]] = [next[rowIndex][destination], next[rowIndex][fieldIndex]];
    onChange(next);
  }

  function splitToNewRow(rowIndex: number, field: MetadataField) {
    if (rows.length >= MAX_METADATA_ROWS || rows[rowIndex].length < 2) return;
    const next = rows.map((row) => row.filter((candidate) => candidate !== field));
    next.splice(rowIndex + 1, 0, [field]);
    onChange(next);
  }

  function moveToAdjacentRow(rowIndex: number, field: MetadataField, offset: -1 | 1) {
    const originalDestination = rowIndex + offset;
    if (originalDestination < 0 || originalDestination >= rows.length) return;
    const next = rows.map((row) => [...row]);
    next[rowIndex] = next[rowIndex].filter((candidate) => candidate !== field);
    const sourceRemoved = next[rowIndex].length === 0;
    if (sourceRemoved) next.splice(rowIndex, 1);
    const destination = offset === -1
      ? rowIndex - 1
      : sourceRemoved ? rowIndex : rowIndex + 1;
    next[destination].push(field);
    onChange(next);
  }

  function selectAll() {
    const fieldsPerRow = Math.ceil(ALL_METADATA_FIELDS.length / MAX_METADATA_ROWS);
    onChange(Array.from(
      { length: MAX_METADATA_ROWS },
      (_unused, index) => ALL_METADATA_FIELDS.slice(index * fieldsPerRow, (index + 1) * fieldsPerRow),
    ).filter((row) => row.length > 0));
  }

  return <fieldset className="metadata-selector">
    <legend>Metadata Selector</legend>
    <p className="metadata-selector__help">Use up to {MAX_METADATA_ROWS} rows. Drag fields onto the same row to join them with <strong>•</strong> in the image.</p>
    <div className="metadata-selector__layout">
      {rows.map((row, rowIndex) => <section className="metadata-selector__layout-row" key={row.join("-")} onDragOver={(event) => event.preventDefault()} onDrop={(event) => dropOnRow(event, rowIndex)}>
        <div className="metadata-selector__row-heading"><span>Row {rowIndex + 1}</span><span><button type="button" onClick={() => moveRow(rowIndex, -1)} disabled={rowIndex === 0} aria-label={`Move metadata row ${rowIndex + 1} up`}>↑</button><button type="button" onClick={() => moveRow(rowIndex, 1)} disabled={rowIndex === rows.length - 1} aria-label={`Move metadata row ${rowIndex + 1} down`}>↓</button></span></div>
        <div className="metadata-selector__row-fields">
          {row.map((field, fieldIndex) => <div className={`metadata-selector__chip${draggedField === field ? " is-dragging" : ""}`} key={field} draggable onDragStart={(event) => startDragging(event, field)} onDragEnd={() => setDraggedField(null)}>
            <span className="metadata-selector__handle" aria-hidden="true">⋮⋮</span>
            <label><input type="checkbox" checked onChange={() => removeField(field)} /><span>{labels[field]}</span></label>
            <span className="metadata-selector__chip-actions"><button type="button" onClick={() => moveWithinRow(rowIndex, fieldIndex, -1)} disabled={fieldIndex === 0} aria-label={`Move ${labels[field]} left`}>←</button><button type="button" onClick={() => moveWithinRow(rowIndex, fieldIndex, 1)} disabled={fieldIndex === row.length - 1} aria-label={`Move ${labels[field]} right`}>→</button><button type="button" onClick={() => moveToAdjacentRow(rowIndex, field, -1)} disabled={rowIndex === 0} aria-label={`Move ${labels[field]} into the previous row`}>⇡</button><button type="button" onClick={() => moveToAdjacentRow(rowIndex, field, 1)} disabled={rowIndex === rows.length - 1} aria-label={`Move ${labels[field]} into the next row`}>⇣</button>{row.length > 1 && rows.length < MAX_METADATA_ROWS && <button type="button" onClick={() => splitToNewRow(rowIndex, field)} aria-label={`Move ${labels[field]} to a new row`} title="Move to a new row">↵</button>}</span>
          </div>)}
          <span className="metadata-selector__drop-hint">Drop here to add to row {rowIndex + 1}</span>
        </div>
      </section>)}
      {rows.length < MAX_METADATA_ROWS && <button className="metadata-selector__new-row" type="button" onDragOver={(event) => event.preventDefault()} onDrop={dropAsNewRow} disabled={!draggedField}>Drop here to create row {rows.length + 1}</button>}
    </div>
    <div className="metadata-selector__available"><span>Available fields</span><div>{ALL_METADATA_FIELDS.filter((field) => !selected.has(field)).map((field) => <label className="metadata-selector__available-field" key={field} draggable onDragStart={(event) => startDragging(event, field)} onDragEnd={() => setDraggedField(null)}><span className="metadata-selector__handle" aria-hidden="true">⋮⋮</span><input type="checkbox" checked={false} onChange={() => addField(field)} /><span>{labels[field]}</span></label>)}</div></div>
    <div className="metadata-selector__actions"><button type="button" onClick={selectAll}>Select all</button><button type="button" onClick={() => onChange([])}>Deselect all</button><span>{rows.length}/{MAX_METADATA_ROWS} rows used</span></div>
  </fieldset>;
}

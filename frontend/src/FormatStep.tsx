import { FormEvent, MouseEvent, useEffect, useMemo, useRef, useState } from "react";
import { SavedFormat, createSavedFormat, listSavedFormats, replaceSavedFormat } from "./api";
import { User } from "./firebaseAuth";
import { FormatConfiguration, formatCode, isFormatComplete, normalizeFormat, parseFormatCode } from "./format";

interface FormatStepProps {
  user: User | null;
  value: FormatConfiguration;
  onChange: (value: FormatConfiguration) => void;
  onSignIn: () => void;
}

function closeOnBackdrop(event: MouseEvent<HTMLDialogElement>) {
  if (event.target === event.currentTarget) event.currentTarget.close();
}

export default function FormatStep({ user, value, onChange, onSignIn }: FormatStepProps) {
  const [savedFormats, setSavedFormats] = useState<SavedFormat[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [formatName, setFormatName] = useState("");
  const [importText, setImportText] = useState("");
  const [message, setMessage] = useState("");
  const [dialogMessage, setDialogMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [overwriteTarget, setOverwriteTarget] = useState<SavedFormat | null>(null);
  const importDialog = useRef<HTMLDialogElement>(null);
  const exportDialog = useRef<HTMLDialogElement>(null);
  const saveDialog = useRef<HTMLDialogElement>(null);
  const overwriteDialog = useRef<HTMLDialogElement>(null);
  const exportedCode = useMemo(() => formatCode(value), [value]);

  useEffect(() => {
    if (!user) {
      setSavedFormats([]);
      setSelectedId("");
      return;
    }
    let current = true;
    setLoading(true);
    user.getIdToken().then(listSavedFormats).then((items) => {
      if (current) setSavedFormats(items);
    }).catch((error: unknown) => {
      if (current) setMessage(error instanceof Error ? error.message : "Could not load your saved formats.");
    }).finally(() => {
      if (current) setLoading(false);
    });
    return () => { current = false; };
  }, [user]);

  function loadSavedFormat(id: string) {
    setSelectedId(id);
    if (!id) return;
    const saved = savedFormats.find((item) => item.id === id);
    if (!saved) return;
    try {
      onChange(normalizeFormat(saved.data));
      setMessage(`Loaded “${saved.name}”.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "That saved format could not be loaded.");
    }
  }

  function importFormat(event: FormEvent) {
    event.preventDefault();
    try {
      onChange(parseFormatCode(importText));
      setSelectedId("");
      setMessage("Format settings imported.");
      setDialogMessage("");
      importDialog.current?.close();
    } catch (error) {
      setDialogMessage(error instanceof Error ? error.message : "That format code could not be imported.");
    }
  }

  async function copyExport() {
    try {
      await navigator.clipboard.writeText(exportedCode);
      setDialogMessage("Copied format code.");
    } catch {
      setDialogMessage("Could not copy automatically. Select the text and copy it manually.");
    }
  }

  function downloadExport() {
    const blob = new Blob([exportedCode], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "melee-podium-format.json";
    link.click();
    URL.revokeObjectURL(url);
  }

  async function persistFormat(target?: SavedFormat) {
    if (!user) return;
    setSaving(true);
    setDialogMessage("");
    try {
      const token = await user.getIdToken();
      const saved = target
        ? await replaceSavedFormat(token, target.id, formatName.trim(), value)
        : await createSavedFormat(token, formatName.trim(), value);
      setSavedFormats((current) => target
        ? current.map((item) => item.id === saved.id ? saved : item)
        : [saved, ...current]);
      setSelectedId(saved.id);
      setMessage(target ? `Updated “${saved.name}”.` : `Saved “${saved.name}”.`);
      setOverwriteTarget(null);
      overwriteDialog.current?.close();
      saveDialog.current?.close();
    } catch (error) {
      setDialogMessage(error instanceof Error ? error.message : "Could not save the format.");
    } finally {
      setSaving(false);
    }
  }

  function requestSave(event: FormEvent) {
    event.preventDefault();
    const normalized = formatName.trim().toLocaleLowerCase();
    const existing = savedFormats.find((item) => item.name.trim().toLocaleLowerCase() === normalized);
    if (existing) {
      setOverwriteTarget(existing);
      saveDialog.current?.close();
      overwriteDialog.current?.showModal();
      return;
    }
    void persistFormat();
  }

  const complete = isFormatComplete(value);
  return <section className="step-content format-step">
    <div className="step-intro"><h1>Choose a Format</h1><p>Load a format you already use, or import one shared by another tournament organizer.</p></div>
    <section className="format-loader" aria-labelledby="load-format-heading">
      <div><span className="eyebrow">Start from saved settings</span><h2 id="load-format-heading">Load a previous format</h2></div>
      {user ? <label className="format-select">Saved formats<select value={selectedId} onChange={(event) => loadSavedFormat(event.target.value)} disabled={loading}><option value="">{loading ? "Loading formats…" : "Choose a saved format"}</option>{savedFormats.map((format) => <option value={format.id} key={format.id}>{format.name}</option>)}</select></label> : <div className="format-signin"><p>Sign in to choose from your saved formats.</p><button className="button button--outline" type="button" onClick={onSignIn}>Sign in</button></div>}
      <div className="format-import-prompt"><span>Or import format from code.</span><button className="button button--outline" type="button" onClick={() => { setImportText(""); setDialogMessage(""); importDialog.current?.showModal(); }}>Import format</button></div>
    </section>

    <section className="format-options-placeholder" aria-labelledby="format-options-heading"><span className="stub-step__number">Next up</span><h2 id="format-options-heading">Format options</h2><p>The mode, layout, entrant count, styling, and placement controls will be added here next. A complete imported or saved format can already unlock the next step.</p><div className={`format-readiness${complete ? " is-ready" : ""}`}><span aria-hidden="true" />{complete ? "All format properties are selected" : "Format properties still need to be selected"}</div></section>

    {message && <p className="inline-message format-message" role="status">{message}</p>}
    <div className="format-actions"><button className="button button--ghost" type="button" onClick={() => { setDialogMessage(""); exportDialog.current?.showModal(); }}>Export Format</button><button className="button button--dark" type="button" disabled={!user || !complete} onClick={() => { setFormatName(savedFormats.find((item) => item.id === selectedId)?.name ?? ""); setDialogMessage(""); saveDialog.current?.showModal(); }}>Save Format</button></div>
    {!user && <p className="format-actions__help">Sign in to save this format. Export remains available without an account.</p>}

    <dialog className="modal format-code-modal" ref={importDialog} onClick={closeOnBackdrop}><form className="modal__content" onSubmit={importFormat}><button className="modal__close" type="button" onClick={() => importDialog.current?.close()} aria-label="Close">×</button><span className="eyebrow">Import</span><h2>Import format from code</h2><p>Paste a JSON format code. Valid settings will replace the current format selections.</p><label className="field">Format JSON<textarea value={importText} onChange={(event) => setImportText(event.target.value)} placeholder={'{\n  "schema_version": 1,\n  "selection": { ... }\n}'} required autoFocus /></label>{dialogMessage && <p className="inline-message" role="alert">{dialogMessage}</p>}<div className="modal__actions"><button className="button button--ghost" type="button" onClick={() => importDialog.current?.close()}>Cancel</button><button className="button button--dark" type="submit" disabled={!importText.trim()}>Import settings</button></div></form></dialog>

    <dialog className="modal format-code-modal" ref={exportDialog} onClick={closeOnBackdrop}><div className="modal__content"><button className="modal__close" type="button" onClick={() => exportDialog.current?.close()} aria-label="Close">×</button><span className="eyebrow">Export</span><h2>Export format</h2><p>Copy this code to share it, or download it as a JSON file.</p><label className="field">Format JSON<textarea value={exportedCode} readOnly /></label>{dialogMessage && <p className="inline-message" role="status">{dialogMessage}</p>}<div className="modal__actions"><button className="button button--ghost" type="button" onClick={downloadExport}>Download JSON</button><button className="button button--dark" type="button" onClick={() => void copyExport()}>Copy code</button></div></div></dialog>

    <dialog className="modal" ref={saveDialog} onClick={closeOnBackdrop}><form className="modal__content" onSubmit={requestSave}><button className="modal__close" type="button" onClick={() => saveDialog.current?.close()} aria-label="Close">×</button><span className="eyebrow">Save for later</span><h2>Save Format</h2><p>Give this format a name you will recognize next time.</p><label className="field">Format name<input value={formatName} maxLength={120} onChange={(event) => setFormatName(event.target.value)} placeholder="e.g. Weekly Top 8" required autoFocus /></label>{dialogMessage && <p className="inline-message" role="alert">{dialogMessage}</p>}<div className="modal__actions"><button className="button button--ghost" type="button" onClick={() => saveDialog.current?.close()}>Cancel</button><button className="button button--dark" type="submit" disabled={saving || !formatName.trim()}>{saving ? "Saving…" : "Save format"}</button></div></form></dialog>

    <dialog className="modal" ref={overwriteDialog} onClick={(event) => { if (event.target === event.currentTarget && !saving) event.currentTarget.close(); }}><div className="modal__content"><button className="modal__close" type="button" onClick={() => overwriteDialog.current?.close()} aria-label="Close" disabled={saving}>×</button><span className="eyebrow">Existing name</span><h2>Overwrite saved format?</h2><p>You already have a format called <strong>{overwriteTarget?.name}</strong>. Do you want to overwrite it?</p>{dialogMessage && <p className="inline-message" role="alert">{dialogMessage}</p>}<div className="modal__actions"><button className="button button--ghost" type="button" onClick={() => overwriteDialog.current?.close()} disabled={saving}>Cancel</button><button className="button button--dark" type="button" onClick={() => overwriteTarget && void persistFormat(overwriteTarget)} disabled={saving}>{saving ? "Overwriting…" : "Overwrite format"}</button></div></div></dialog>
  </section>;
}


import { FormEvent, MouseEvent, useEffect, useMemo, useRef, useState } from "react";
import { SavedFormat, createSavedFormat, listSavedFormats, replaceSavedFormat } from "./api";
import { User } from "./firebaseAuth";
import { FormatConfiguration, formatCode, isFormatComplete } from "./format";
import FormatSettings from "./FormatSettings";
import { FormatImageInfo } from "./BackgroundPositionDialog";

interface FormatStepProps {
  user: User | null;
  value: FormatConfiguration;
  backgroundImage: FormatImageInfo | null;
  onChange: (value: FormatConfiguration) => void;
  onProceed: () => void;
}

function closeOnBackdrop(event: MouseEvent<HTMLDialogElement>) {
  if (event.target === event.currentTarget) event.currentTarget.close();
}

export default function FormatStep({ user, value, backgroundImage, onChange, onProceed }: FormatStepProps) {
  const [savedFormats, setSavedFormats] = useState<SavedFormat[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [formatName, setFormatName] = useState("");
  const [message, setMessage] = useState("");
  const [messageIsError, setMessageIsError] = useState(false);
  const [dialogMessage, setDialogMessage] = useState("");
  const [dialogMessageIsError, setDialogMessageIsError] = useState(false);
  const [saving, setSaving] = useState(false);
  const [overwriteTarget, setOverwriteTarget] = useState<SavedFormat | null>(null);
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
    user.getIdToken().then(listSavedFormats).then((items) => {
      if (current) setSavedFormats(items);
    }).catch((error: unknown) => {
      if (current) { setMessageIsError(true); setMessage(error instanceof Error ? error.message : "Could not load your saved formats."); }
    });
    return () => { current = false; };
  }, [user]);

  async function copyExport() {
    try {
      await navigator.clipboard.writeText(exportedCode);
      setDialogMessageIsError(false);
      setDialogMessage("Copied format code.");
    } catch {
      setDialogMessageIsError(true);
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
    setDialogMessageIsError(false);
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
      setMessageIsError(false);
      setMessage(target ? `Updated “${saved.name}”.` : `Saved “${saved.name}”.`);
      setOverwriteTarget(null);
      overwriteDialog.current?.close();
      saveDialog.current?.close();
    } catch (error) {
      setDialogMessageIsError(true);
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
    <div className="step-intro"><div className="step-heading-row"><h1>Choose a Format</h1><button className="button button--ghost" type="button" disabled={!complete} onClick={onProceed}>{complete ? "Proceed to Bracket Import" : "Cannot Skip"}</button></div><p>Configure the image layout, header content, colors, and text settings.</p></div>

    <FormatSettings value={value} backgroundImage={backgroundImage} onChange={(nextValue) => { setSelectedId(""); onChange(nextValue); }} />
    <div className={`format-readiness format-readiness--summary${complete ? " is-ready" : ""}`}><span aria-hidden="true" />{complete ? "All available format properties are selected" : "Choose a podium style, bracket type, and entrant layout to continue"}</div>

    {message && <p className="inline-message format-message" role={messageIsError ? "alert" : "status"}>{message}</p>}
    <div className="format-actions"><button className="button button--ghost" type="button" onClick={() => { setDialogMessage(""); exportDialog.current?.showModal(); }}>Export Format</button><button className="button button--dark" type="button" disabled={!user || !complete} onClick={() => { setFormatName(savedFormats.find((item) => item.id === selectedId)?.name ?? ""); setDialogMessage(""); saveDialog.current?.showModal(); }}>Save Format</button></div>
    {!user && <p className="format-actions__help">Sign in to save this format. Export remains available without an account.</p>}

    <dialog className="modal format-code-modal" ref={exportDialog} onClick={closeOnBackdrop}><div className="modal__content"><button className="modal__close" type="button" onClick={() => exportDialog.current?.close()} aria-label="Close">×</button><span className="eyebrow">Export</span><h2>Export format</h2><p>Copy this code to share it, or download it as a JSON file.</p><label className="field">Format JSON<span className="format-code-field"><textarea value={exportedCode} readOnly /><button className="format-copy-button" type="button" onClick={() => void copyExport()} aria-label="Copy format JSON" title="Copy format JSON"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="8" width="11" height="11" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/></svg></button></span></label>{dialogMessage && <p className="inline-message" role={dialogMessageIsError ? "alert" : "status"}>{dialogMessage}</p>}<div className="modal__actions"><button className="button button--dark" type="button" onClick={downloadExport}>Download JSON</button></div></div></dialog>

    <dialog className="modal" ref={saveDialog} onClick={closeOnBackdrop}><form className="modal__content" onSubmit={requestSave}><button className="modal__close" type="button" onClick={() => saveDialog.current?.close()} aria-label="Close">×</button><span className="eyebrow">Save for later</span><h2>Save Format</h2><p>Give this format a name you will recognize next time.</p><label className="field">Format name<input value={formatName} maxLength={120} onChange={(event) => setFormatName(event.target.value)} placeholder="e.g. Weekly Top 8" required autoFocus /></label>{dialogMessage && <p className="inline-message" role="alert">{dialogMessage}</p>}<div className="modal__actions"><button className="button button--ghost" type="button" onClick={() => saveDialog.current?.close()}>Cancel</button><button className="button button--dark" type="submit" disabled={saving || !formatName.trim()}>{saving ? "Saving…" : "Save format"}</button></div></form></dialog>

    <dialog className="modal" ref={overwriteDialog} onClick={(event) => { if (event.target === event.currentTarget && !saving) event.currentTarget.close(); }}><div className="modal__content"><button className="modal__close" type="button" onClick={() => overwriteDialog.current?.close()} aria-label="Close" disabled={saving}>×</button><span className="eyebrow">Existing name</span><h2>Overwrite saved format?</h2><p>You already have a format called <strong>{overwriteTarget?.name}</strong>. Do you want to overwrite it?</p>{dialogMessage && <p className="inline-message" role="alert">{dialogMessage}</p>}<div className="modal__actions"><button className="button button--ghost" type="button" onClick={() => overwriteDialog.current?.close()} disabled={saving}>Cancel</button><button className="button button--dark" type="button" onClick={() => overwriteTarget && void persistFormat(overwriteTarget)} disabled={saving}>{saving ? "Overwriting…" : "Overwrite format"}</button></div></div></dialog>
  </section>;
}


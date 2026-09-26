import { FormEvent, MouseEvent, useEffect, useRef, useState } from "react";
import { SavedFormat, listSavedFormats } from "./api";
import { User } from "./firebaseAuth";
import { FormatConfiguration, normalizeFormat, parseFormatCode } from "./format";

interface LoadStepProps {
  user: User | null;
  onChange: (value: FormatConfiguration) => void;
  onSignIn: () => void;
}

function closeOnBackdrop(event: MouseEvent<HTMLDialogElement>) {
  if (event.target === event.currentTarget) event.currentTarget.close();
}

export default function LoadStep({ user, onChange, onSignIn }: LoadStepProps) {
  const [savedFormats, setSavedFormats] = useState<SavedFormat[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [importText, setImportText] = useState("");
  const [message, setMessage] = useState("");
  const [dialogMessage, setDialogMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const importDialog = useRef<HTMLDialogElement>(null);

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
      setMessage(`Loaded “${saved.name}”. Continue to Assets to review its selections.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "That saved format could not be loaded.");
    }
  }

  function importFormat(event: FormEvent) {
    event.preventDefault();
    try {
      onChange(parseFormatCode(importText));
      setSelectedId("");
      setMessage("Format settings imported. Continue to Assets to review its selections.");
      setDialogMessage("");
      importDialog.current?.close();
    } catch (error) {
      setDialogMessage(error instanceof Error ? error.message : "That format code could not be imported.");
    }
  }

  return <section className="step-content load-step">
    <div className="step-intro"><h1>Load a Format</h1><p>Start with saved settings, import a shared format code, or continue without loading one.</p></div>
    <section className="format-loader" aria-labelledby="load-format-heading">
      <div><span className="eyebrow">Optional starting point</span><h2 id="load-format-heading">Load a previous format</h2></div>
      {user ? <label className="format-select">Saved formats<select value={selectedId} onChange={(event) => loadSavedFormat(event.target.value)} disabled={loading}><option value="">{loading ? "Loading formats…" : "Choose a saved format"}</option>{savedFormats.map((format) => <option value={format.id} key={format.id}>{format.name}</option>)}</select></label> : <div className="format-signin"><p>Sign in to choose from your saved formats.</p><button className="button button--outline" type="button" onClick={onSignIn}>Sign in</button></div>}
      <div className="format-import-prompt"><span>Or import format from code.</span><button className="button button--outline" type="button" onClick={() => { setImportText(""); setDialogMessage(""); importDialog.current?.showModal(); }}>Import format</button></div>
    </section>
    {message && <p className="inline-message format-message" role="status">{message}</p>}
    <dialog className="modal format-code-modal" ref={importDialog} onClick={closeOnBackdrop}><form className="modal__content" onSubmit={importFormat}><button className="modal__close" type="button" onClick={() => importDialog.current?.close()} aria-label="Close">×</button><span className="eyebrow">Import</span><h2>Import format from code</h2><p>Paste a JSON format code. Valid settings will be loaded before you choose assets.</p><label className="field">Format JSON<textarea value={importText} onChange={(event) => setImportText(event.target.value)} placeholder={'{\n  "schema_version": 1,\n  "selection": { ... }\n}'} required autoFocus /></label>{dialogMessage && <p className="inline-message" role="alert">{dialogMessage}</p>}<div className="modal__actions"><button className="button button--ghost" type="button" onClick={() => importDialog.current?.close()}>Cancel</button><button className="button button--dark" type="submit" disabled={!importText.trim()}>Import settings</button></div></form></dialog>
  </section>;
}

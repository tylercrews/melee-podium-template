import { FormEvent, useState } from "react";
import {
  createAccountWithEmail,
  firebaseAuthErrorMessage,
  signInWithEmail,
} from "./firebaseAuth";

type AuthMode = "sign_in" | "create_account";

export default function EmailAuthForm({
  disabled,
  onComplete,
}: {
  disabled: boolean;
  onComplete: () => void;
}) {
  const [mode, setMode] = useState<AuthMode>("sign_in");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");

  function selectMode(nextMode: AuthMode) {
    setMode(nextMode);
    setPassword("");
    setConfirmation("");
    setMessage("");
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (mode === "create_account" && password !== confirmation) {
      setMessage("The passwords do not match.");
      return;
    }
    setSubmitting(true);
    setMessage("");
    try {
      if (mode === "create_account") {
        await createAccountWithEmail(email.trim(), password);
      } else {
        await signInWithEmail(email.trim(), password);
      }
      onComplete();
    } catch (error) {
      setMessage(firebaseAuthErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  return <section className="email-auth" aria-label="Email and password authentication">
    <div className="email-auth__modes" role="tablist" aria-label="Account action">
      <button type="button" role="tab" aria-selected={mode === "sign_in"} className={mode === "sign_in" ? "is-active" : ""} onClick={() => selectMode("sign_in")}>Sign in</button>
      <button type="button" role="tab" aria-selected={mode === "create_account"} className={mode === "create_account" ? "is-active" : ""} onClick={() => selectMode("create_account")}>Create account</button>
    </div>
    <form className="email-auth__form" onSubmit={submit}>
      <label className="field">Email address<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required disabled={disabled || submitting} /></label>
      <label className="field">Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={mode === "create_account" ? "new-password" : "current-password"} minLength={6} required disabled={disabled || submitting} /></label>
      {mode === "create_account" && <label className="field">Confirm password<input type="password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} autoComplete="new-password" minLength={6} required disabled={disabled || submitting} /></label>}
      {message && <p className="inline-message" role="alert">{message}</p>}
      <button className="button button--dark" type="submit" disabled={disabled || submitting}>{submitting ? "Please wait…" : mode === "create_account" ? "Create account" : "Sign in with email"}</button>
    </form>
  </section>;
}

import { useState } from "react";
import Alert from "../components/Alert.jsx";
import Button from "../components/Button.jsx";
import TextInput from "../components/TextInput.jsx";
import { mapRegistrationError, validateRegistration } from "../components/auth.js";
import { registerAccount } from "../api/client";
import "../styles/login.css";

/** Account creation (route #/sign-in) — Stitch login visual language on
 * the real POST /api/v1/auth/register contract. Client validation mirrors
 * backend rules for instant feedback; every server rejection maps to the
 * same user-facing texts. Success stores nothing and grants no session —
 * the flow continues at #/login per the required register-then-login flow.
 */
export default function SignUp() {
  const [name, setName] = useState("");
  const [idNumber, setIdNumber] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [busy, setBusy] = useState(false);

  function eye(open, setOpen, label) {
    return (
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? `Hide ${label}` : `Show ${label}`}
        aria-pressed={open}
      >
        {open ? (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        )}
      </button>
    );
  }

  async function submit(e) {
    e.preventDefault();
    if (busy) return; // duplicate submission: ignore
    setFormError("");
    const trimmed = {
      name: name.trim(),
      idNumber: idNumber.trim(),
      email: email.trim(),
      password,
      confirm,
    };
    const fieldErrors = validateRegistration(trimmed);
    setErrors(fieldErrors);
    if (Object.keys(fieldErrors).length > 0) return;
    setBusy(true);
    try {
      // POST /api/v1/auth/register — the only account-creation path.
      // Passwords travel exclusively in this request body, never logged.
      await registerAccount({
        name: trimmed.name,
        id_number: trimmed.idNumber,
        email: trimmed.email,
        password: trimmed.password,
      });
      try {
        sessionStorage.setItem("qa_registered", "1");
      } catch {
        // Flag is a nicety; the login page works without it.
      }
      window.location.hash = "#/login";
    } catch (err) {
      const mapped = mapRegistrationError(err);
      setErrors(mapped.fields);
      setFormError(mapped.form);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login">
      <section className="login-brand" aria-label="Land Record Intelligence">
        <div className="login-brand-grid bg-cadastral-grid" aria-hidden="true" />
        <div className="login-brandmark">
          <span className="login-brandmark-badge" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
            </svg>
          </span>
          <div>
            <span className="login-brandmark-name">Bhoomi Intel<span className="login-ps-chip">PS-26018</span></span>
            <div className="login-brandmark-sub">SIH 2026 • Intelligent Cadastral Extraction</div>
          </div>
        </div>

        <div>
          <h1>Land Record Intelligence</h1>
          <p className="login-lede">From legacy documents to structured, review-ready records.</p>
        </div>

        <div className="login-brand-foot">
          <span className="login-live"><span className="login-live-dot" aria-hidden="true" />SIH 2026 • PS-26018</span>
          <span>Role-based access • Full audit trail</span>
        </div>
      </section>

      <section className="login-panel" aria-label="Create account">
        <div className="login-context">
          <span className="login-context-crumb">
            <span className="login-context-dot" aria-hidden="true" />
            <span>National Cadastre Portal</span>
            <span className="sep">/</span>
            <strong>Workspace entry</strong>
          </span>
        </div>

        <div className="login-form-wrap">
          <h2>Sign in</h2>
          <p className="login-sub">Create your workspace account. Accounts start with read-only access.</p>

          <Alert tone="error" title="Account not created">{formError}</Alert>

          <form className="login-form" onSubmit={submit} noValidate>
            <TextInput
              label="Name"
              id="signup-name"
              autoComplete="name"
              placeholder="Your full name"
              value={name}
              disabled={busy}
              error={errors.name}
              onChange={(e) => setName(e.target.value)}
            />
            <TextInput
              label="ID number"
              hint="Official identity number"
              id="signup-id"
              placeholder="e.g. ID-2026-001"
              value={idNumber}
              disabled={busy}
              error={errors.idNumber}
              onChange={(e) => setIdNumber(e.target.value)}
            />
            <TextInput
              label="Email ID"
              id="signup-email"
              type="email"
              autoComplete="email"
              placeholder="officer@example.com"
              value={email}
              disabled={busy}
              error={errors.email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <TextInput
              label="Password"
              hint="8+ characters"
              id="signup-password"
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              placeholder="••••••••"
              value={password}
              disabled={busy}
              error={errors.password}
              onChange={(e) => setPassword(e.target.value)}
              trailing={eye(showPassword, setShowPassword, "password")}
            />
            <TextInput
              label="Confirm password"
              id="signup-confirm"
              type={showConfirm ? "text" : "password"}
              autoComplete="new-password"
              placeholder="••••••••"
              value={confirm}
              disabled={busy}
              error={errors.confirm}
              onChange={(e) => setConfirm(e.target.value)}
              trailing={eye(showConfirm, setShowConfirm, "confirm password")}
            />
            <Button type="submit" variant="primary" fullWidth disabled={busy} className="login-submit">
              {busy ? "Creating account…" : "Sign in"}
            </Button>
            <p className="login-secure-note">Already have an account? <a href="#/login">Login</a></p>
          </form>
        </div>

        <div className="login-foot">
          <span><span className="login-node-chip">SIH 2026 • PS-26018</span></span>
          <span>Strictly authorized personnel only</span>
        </div>
      </section>
    </div>
  );
}

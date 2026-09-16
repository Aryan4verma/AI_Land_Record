import { useState } from "react";
import Alert from "../components/Alert.jsx";
import Button from "../components/Button.jsx";
import TextInput from "../components/TextInput.jsx";
import { getMe, login, setToken, setUser } from "../api/client";
import "../styles/login.css";

/** Stitch Login (1a3bd1dbc5a14deda00bd6d93824e86a) on the existing auth
 * contract: POST /api/v1/auth/login {email, password} -> {access_token}.
 * No forgot-password / remember-me: the backend exposes neither, so the
 * screen omits them instead of faking them.
 */
export default function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [emailError, setEmailError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  // One-shot notice after registration (flag set by #/sign-in, cleared here).
  const [registered] = useState(() => {
    try {
      const flag = sessionStorage.getItem("qa_registered");
      if (flag) sessionStorage.removeItem("qa_registered");
      return Boolean(flag);
    } catch {
      return false;
    }
  });

  async function submit(e) {
    e.preventDefault();
    if (busy) return;
    setError("");
    const trimmedEmail = email.trim();
    let valid = true;
    if (!trimmedEmail) {
      setEmailError("Enter your official email address.");
      valid = false;
    } else if (!trimmedEmail.includes("@")) {
      setEmailError("Enter a valid email address.");
      valid = false;
    } else {
      setEmailError("");
    }
    if (!password) {
      setPasswordError("Enter your password.");
      valid = false;
    } else {
      setPasswordError("");
    }
    if (!valid) return;
    setBusy(true);
    try {
      // Drop any stale session first so a failed login never leaves the
      // previous token behind; a 401 here stays a form error (no redirect).
      setToken("");
      setUser(null);
      const data = await login({ email: trimmedEmail, password });
      setToken(data.access_token);
      const me = await getMe();
      setUser(me);
      onLogin(me);
    } catch (err) {
      // Backend envelope message only (e.g. "Invalid email or password.");
      // raw exceptions and request internals never reach the UI.
      setError(err && err.code ? String(err.message).split(" (request")[0] : "Sign in failed. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login">
      <section className="login-brand" aria-label="Land Record Intelligence">
        <div className="login-brand-grid bg-cadastral-grid" aria-hidden="true" />
        <svg className="login-brand-vectors" viewBox="0 0 600 800" preserveAspectRatio="none" aria-hidden="true">
          <polygon points="80,140 240,110 320,230 140,280" fill="none" stroke="#94A3B8" strokeWidth="1" strokeDasharray="4 4" />
          <polygon points="240,110 490,80 540,240 320,230" fill="rgba(37,99,235,0.03)" stroke="#94A3B8" strokeWidth="1.2" />
          <polygon points="140,280 320,230 380,440 210,480" fill="none" stroke="#64748B" strokeWidth="1" />
          <polygon points="320,230 540,240 510,470 380,440" fill="none" stroke="#94A3B8" strokeWidth="1" strokeDasharray="3 3" />
          <circle cx="240" cy="110" r="3.5" fill="#38BDF8" />
          <circle cx="320" cy="230" r="3.5" fill="#38BDF8" />
          <circle cx="140" cy="280" r="2.5" fill="#94A3B8" />
          <circle cx="380" cy="440" r="2.5" fill="#94A3B8" />
          <line x1="240" y1="110" x2="320" y2="230" stroke="#38BDF8" strokeWidth="1" strokeOpacity="0.4" />
        </svg>

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
          <span className="login-env-pill"><span className="login-env-dot" aria-hidden="true" />Secure officer workspace</span>
          <h1>Land Record Intelligence</h1>
          <p className="login-lede">From legacy documents to structured, review-ready records.</p>
          <div className="login-pillars">
            <span className="login-pillar"><span className="login-pillar-assist" aria-hidden="true">●</span>AI-assisted</span>
            <span className="sep" aria-hidden="true">•</span>
            <span className="login-pillar"><span className="login-pillar-human" aria-hidden="true">●</span>Human verified</span>
            <span className="sep" aria-hidden="true">•</span>
            <span className="login-pillar"><span className="login-pillar-audit" aria-hidden="true">●</span>Audit ready</span>
          </div>
          <div className="login-pipeline-card">
            <div className="login-pipeline-head"><span>OCR INGESTION PIPELINE</span><span className="active">OCR • EXTRACTION • VALIDATION</span></div>
            <p>Reads land records, flags what needs checking, and keeps a verified officer in control of every decision.</p>
          </div>
        </div>

        <div className="login-brand-foot">
          <span className="login-live"><span className="login-live-dot" aria-hidden="true" />SIH 2026 • PS-26018</span>
          <span>Role-based access • Full audit trail</span>
        </div>
      </section>

      <section className="login-panel" aria-label="Sign in">
        <div className="login-context">
          <span className="login-context-crumb">
            <span className="login-context-dot" aria-hidden="true" />
            <span>National Cadastre Portal</span>
            <span className="sep">/</span>
            <strong>Adjudication Console</strong>
          </span>
        </div>

        <div className="login-form-wrap">
          <span className="login-gateway">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            Officer Verification Gateway
          </span>
          <h2>Sign in</h2>
          <p className="login-sub">Access your land-record digitization workspace.</p>

          <Alert tone="error" title="Authentication failed">{error}</Alert>
          {registered && !error && (
            <Alert tone="success" title="Account created">Sign in with your email and password.</Alert>
          )}

          <form className="login-form" onSubmit={submit} noValidate>
            <TextInput
              label="Official Email"
              hint="Official email address"
              id="login-email"
              type="email"
              autoComplete="email"
              placeholder="officer@example.com"
              value={email}
              disabled={busy}
              error={emailError}
              onChange={(e) => setEmail(e.target.value)}
            />
            <TextInput
              label="Password / Secure Token"
              id="login-password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              placeholder="••••••••••••"
              value={password}
              disabled={busy}
              error={passwordError}
              onChange={(e) => setPassword(e.target.value)}
              trailing={
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  aria-pressed={showPassword}
                  tabIndex={0}
                >
                  {showPassword ? (
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
              }
            />
            <Button type="submit" variant="primary" fullWidth disabled={busy} className="login-submit">
              {busy ? (
                <>
                  <svg className="login-submit-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" opacity="0.25" />
                    <path d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" fill="currentColor" />
                  </svg>
                  Signing in…
                </>
              ) : (
                <>
                  Sign in
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                  </svg>
                </>
              )}
            </Button>
            <p className="login-secure-note">Secure access to your document-processing workspace.</p>
            <p className="login-secure-note">New here? <a href="#/auth">Create your workspace account</a></p>
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

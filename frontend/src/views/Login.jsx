import { useState } from "react";
import Alert from "../components/Alert.jsx";
import Button from "../components/Button.jsx";
import { getMe, login, logout, setToken, setUser } from "../api/client";
import { loginRoleMatches, validateLoginIdentifier } from "../components/auth.js";
import "../styles/login.css";

/** Stitch Login (6d3155c51cfb4bea8d5b5ca7043ed57a) on the existing auth
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
  // Presentation-only intent. The authenticated user's real role still
  // comes from the existing backend response after login.
  const [selectedRole, setSelectedRole] = useState("officer");
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
    const identifierError = validateLoginIdentifier(trimmedEmail, selectedRole);
    setEmailError(identifierError);
    if (identifierError) valid = false;
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
      if (!loginRoleMatches(selectedRole, me)) {
        await logout();
        setEmailError("");
        setError("This account does not match the selected access type.");
        return;
      }
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
    <div className="login-screen-page">
      <header className="login-institutional-header">
        <div className="login-header-identity">
          <span className="login-header-emblem" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
              <path d="M4 4h16v16H4zM8 4v16M12 4v16M16 4v16M4 8h16M4 12h16M4 16h16" />
            </svg>
          </span>
          <span className="login-header-name">BHOOMI INTEL</span>
          <span className="login-header-divider" aria-hidden="true">|</span>
          <span className="login-header-chip">PS-26018</span>
          <span className="login-header-description">National Land Records Modernization Cadastre Verification</span>
        </div>
        <div className="login-header-security">
          <span className="login-secure-status"><span aria-hidden="true" />GATEWAY-SECURE</span>
          <span className="login-header-divider" aria-hidden="true">|</span>
          <span>TLS 1.3 / SHA-256</span>
        </div>
      </header>

      <main className="login-screen-main">
        <div className="login-screen-shell">
          <section className="login-institutional-panel" aria-label="Land Record Intelligence">
            <svg className="login-cadastre-linework" viewBox="0 0 520 740" fill="none" aria-hidden="true">
              <polygon points="35,50 185,35 245,165 75,200" stroke="currentColor" strokeDasharray="4 4" strokeWidth="1.2" />
              <polygon points="185,35 460,25 500,225 245,165" stroke="currentColor" strokeWidth="1.2" />
              <polygon points="75,200 245,165 315,415 105,465" stroke="currentColor" strokeWidth="1.8" />
              <polygon points="245,165 500,225 475,475 315,415" stroke="currentColor" strokeDasharray="5 3" strokeWidth="1.2" />
              <polygon points="105,465 315,415 285,680 65,615" stroke="currentColor" strokeWidth="1.2" />
              <polygon points="315,415 475,475 460,710 285,680" stroke="currentColor" strokeWidth="1.2" />
              <circle cx="185" cy="35" r="3.5" fill="#38bdf8" />
              <circle cx="245" cy="165" r="3" fill="white" />
              <circle cx="315" cy="415" r="4" fill="#38bdf8" />
              <circle cx="105" cy="465" r="3" fill="white" />
              <circle cx="475" cy="475" r="3" fill="white" />
              <path d="M185 35 315 415M75 200l400 275" stroke="#38bdf8" strokeDasharray="3 3" />
            </svg>
            <div className="login-institutional-content">
              <div className="login-left-rail">
                <span className="login-left-rail-mark" aria-hidden="true" />
                <span>OFFICIAL CADASTRAL GATEWAY</span>
              </div>
              <div className="login-left-kicker"><span aria-hidden="true" />AI PROPOSES • RULES VALIDATE • HUMANS DECIDE</div>
              <h1>Land Records Intelligence<br />System</h1>
              <p className="login-left-description">Unified authentication interface for jurisdictional cadastral officers and authorized public land record inquiries.</p>

              <div className="login-access-matrix">
                <div className="login-access-title">ACCESS MATRIX BY ROLE</div>
                <div className="login-access-card">
                  <div className="login-access-card-head">
                    <div className="login-access-card-name"><span className="login-access-icon" aria-hidden="true">✓</span>Officer / Operator</div>
                    <span className="login-access-badge login-access-badge-active">Full Action</span>
                  </div>
                  <ul>
                    <li>Upload &amp; batch OCR land deeds</li>
                    <li>Review polygon overlaps &amp; mutate titles</li>
                    <li>Approve or reject cadastral survey discrepancies</li>
                  </ul>
                </div>
                <div className="login-access-card login-access-card-muted">
                  <div className="login-access-card-head">
                    <div className="login-access-card-name"><span className="login-access-icon" aria-hidden="true">◉</span>Citizen / Read-Only</div>
                    <span className="login-access-badge">Audit Only</span>
                  </div>
                  <ul>
                    <li>Search gazetted parcels by Khasra / Survey No</li>
                    <li>Inspect sanitized public title extracts</li>
                    <li>No modification, override, or approval permissions</li>
                  </ul>
                </div>
              </div>
            </div>
            <div className="login-institutional-footer">
              <span>DEPT. OF LAND RESOURCES</span><span aria-hidden="true">•</span><span>SIH 2026</span>
            </div>
          </section>

          <section className="login-screen-workspace" aria-label="Sign in">
            <svg className="login-workspace-linework" viewBox="0 0 740 820" preserveAspectRatio="none" fill="none" aria-hidden="true">
              <g opacity=".08" stroke="#0f5e91" strokeWidth="1.3">
                <path d="M420-30C510 40 590 110 770 100M440 20C530 90 620 160 780 150M470 70C560 140 640 220 780 210M500 120C590 200 660 280 780 270" />
              </g>
              <g opacity=".07" stroke="#087f78" strokeWidth="1.2">
                <polygon points="90,40 310,25 380,145 170,170" /><polygon points="310,25 610,15 640,175 380,145" />
                <polygon points="380,145 640,175 590,410 340,370" strokeDasharray="4 3" /><polygon points="170,170 380,145 340,370 130,400" />
                <polygon points="130,400 340,370 300,670 80,600" /><polygon points="340,370 590,410 560,710 300,670" strokeDasharray="5 3" />
              </g>
              <g opacity=".12" stroke="#0f5e91"><path d="M170 165v10M165 170h10M380 140v10M375 145h10M340 365v10M335 370h10" /><circle cx="310" cy="25" r="2.5" fill="#0f5e91" /><circle cx="380" cy="145" r="2.5" fill="#087f78" /><circle cx="340" cy="370" r="2.5" fill="#0f5e91" /></g>
            </svg>
            <div className="login-auth-card">
              <div className="login-auth-card-body">
                <div className="login-auth-rail">
                  <div className="login-auth-rail-left">
                    <span className="login-auth-gateway">OFFICIAL CADASTRAL GATEWAY</span>
                    <span className="login-auth-rail-signal"><span aria-hidden="true" />AI PROPOSES • RULES VALIDATE • HUMANS DECIDE</span>
                  </div>
                  <span className="login-auth-secure"><span aria-hidden="true" />SECURE FORM</span>
                </div>

                <div className="login-profile-context">
                  <div className="login-profile-label">WORKSPACE PROFILE CONTEXT</div>
                  <div className="login-role-switcher" role="radiogroup" aria-label="Workspace profile context">
                    <button
                      type="button"
                      role="radio"
                      className={`login-role-card ${selectedRole === "officer" ? "login-role-card-selected" : ""}`}
                      aria-checked={selectedRole === "officer"}
                      onClick={() => setSelectedRole("officer")}
                    >
                      <span className="login-role-radio" aria-hidden="true">{selectedRole === "officer" && <span />}</span>
                      <span><strong>Government Officer / Operator</strong><small>Revenue Console / Full Mutation</small></span>
                    </button>
                    <button
                      type="button"
                      role="radio"
                      className={`login-role-card ${selectedRole === "public" ? "login-role-card-selected" : ""}`}
                      aria-checked={selectedRole === "public"}
                      onClick={() => setSelectedRole("public")}
                    >
                      <span className="login-role-radio" aria-hidden="true">{selectedRole === "public" && <span />}</span>
                      <span><strong>Public / Read-Only User</strong><small>Title Extracts / Cadastral Inquiry</small></span>
                    </button>
                  </div>
                </div>

                <div className="login-permission-banner" role="note">
                  <span className="login-info-icon" aria-hidden="true">i</span>
                  <span>Operator permissions enabled: Deed ingestion, parcel polygon reconciliation, and title mutation approvals.</span>
                </div>

                {error && <Alert tone="error" title="Authentication failed">{error}</Alert>}
                {registered && !error && <Alert tone="success" title="Account created">Sign in with your email and password.</Alert>}

                <form className="login-screen-form" onSubmit={submit} noValidate>
                  <div className="login-screen-field">
                    <div className="login-screen-field-label"><label htmlFor="login-email">Official Email / Institutional ID</label><span>@gov.in or registered domain</span></div>
                    <div className="login-screen-input-wrap">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2" /><path d="m4 7 8 6 8-6" /></svg>
                      <input id="login-email" type="email" autoComplete="email" placeholder="officer.name@nic.in" value={email} disabled={busy} aria-invalid={!!emailError} onChange={(e) => setEmail(e.target.value)} />
                      <span aria-hidden="true">@</span>
                    </div>
                    {emailError && <p className="login-screen-field-error">{emailError}</p>}
                  </div>
                  <div className="login-screen-field">
                    <div className="login-screen-field-label"><label htmlFor="login-password">Password</label></div>
                    <div className="login-screen-input-wrap">
                      <input id="login-password" type={showPassword ? "text" : "password"} autoComplete="current-password" placeholder="Enter authorized password" value={password} disabled={busy} aria-invalid={!!passwordError} onChange={(e) => setPassword(e.target.value)} />
                      <button type="button" onClick={() => setShowPassword((v) => !v)} aria-label={showPassword ? "Hide password" : "Show password"} aria-pressed={showPassword}>
                        {showPassword ? <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M3 3l18 18M10.6 10.6a2 2 0 0 0 2.8 2.8M9.9 5.2A10.8 10.8 0 0 1 12 5c4.5 0 8.4 2.8 10 7-.5 1.3-1.3 2.5-2.3 3.5M6.2 6.2C4.3 7.3 2.9 9.3 2 12c1.6 4.2 5.5 7 10 7 1.1 0 2.1-.2 3-.5" /></svg> : <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z" /><circle cx="12" cy="12" r="3" /></svg>}
                      </button>
                    </div>
                    {passwordError && <p className="login-screen-field-error">{passwordError}</p>}
                  </div>

                  <div className="login-session-notice" role="note">
                    <span aria-hidden="true">!</span><div><strong>Institutional Session Notice:</strong> Sessions are authenticated through the secure gateway and recorded in the application audit trail.</div>
                  </div>

                  <Button type="submit" variant="primary" fullWidth disabled={busy} className="login-screen-submit">
                    {busy ? <><svg className="login-submit-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" opacity=".25" /><path d="M4 12a8 8 0 0 1 8-8V0C5.4 0 0 5.4 0 12h4Z" fill="currentColor" /></svg>Signing in…</> : <><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M10 17l5-5-5-5M15 12H3M21 4v16" /></svg>Sign In to Revenue Console<span className="login-enter-key">↵ Enter</span></>}
                  </Button>
                </form>

                <div className="login-create-account">
                  <div><strong>New to Bhoomi Intel?</strong><span>Institutional onboarding &amp; public access registry</span></div>
                  <a href="#/sign-in">Create Account <span aria-hidden="true">→</span></a>
                </div>
              </div>
              <div className="login-auth-card-footer">
                <span><i aria-hidden="true" />Statutory Audit Logging Active</span>
                <span className="login-footer-links">• Security Guidelines &nbsp; • Helpdesk &amp; Support</span>
              </div>
            </div>
          </section>
        </div>
      </main>

      <footer className="login-technical-footer">
        <span>BHOOMI INTEL PROTOCOL • PORTAL: AUTH_SV_26</span>
        <span>SMART INDIA HACKATHON 2026 • PS-26018</span>
      </footer>
    </div>
  );
}

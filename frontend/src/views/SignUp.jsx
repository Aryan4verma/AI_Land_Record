import { useState } from "react";
import Alert from "../components/Alert.jsx";
import Button from "../components/Button.jsx";
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
  const [declarationAccepted, setDeclarationAccepted] = useState(true);
  const [declarationError, setDeclarationError] = useState("");

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
    setDeclarationError("");
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
    if (!declarationAccepted) {
      setDeclarationError("Accept the declaration before creating an account.");
      return;
    }
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
    <div className="signup-screen-page">
      <header className="login-institutional-header">
        <div className="login-header-identity">
          <span className="login-header-emblem" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M4 4h16v16H4zM8 4v16M12 4v16M16 4v16M4 8h16M4 12h16M4 16h16" /></svg>
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

      <main className="signup-screen-main">
        <div className="signup-screen-shell">
          <aside className="signup-institutional-panel" aria-label="Registration access policy">
            <svg className="signup-left-linework" viewBox="0 0 375 580" fill="none" aria-hidden="true">
              <polygon points="25,60 175,25 285,115 145,235 35,185" stroke="#a7f3d0" strokeDasharray="3 3" />
              <polygon points="145,235 285,115 375,280 215,370" stroke="#93c5fd" strokeDasharray="4 2" />
              <path d="M25 60 375 280" stroke="#bae6fd" strokeDasharray="4 4" strokeWidth=".75" />
              <circle cx="145" cy="235" r="3" fill="#38bdf8" /><circle cx="285" cy="115" r="3" fill="#38bdf8" />
              <text x="150" y="230" fill="#a7f3d0" fontFamily="monospace" fontSize="9">K-104/A</text>
              <text x="290" y="110" fill="#bae6fd" fontFamily="monospace" fontSize="9">PTS-08</text>
            </svg>
            <div className="signup-institutional-content">
              <div className="signup-left-badge"><span aria-hidden="true" />OFFICIAL CADASTRAL GATEWAY</div>
              <p className="signup-left-kicker"><span aria-hidden="true" />AI PROPOSES • RULES VALIDATE • HUMANS DECIDE</p>
              <h1>Land Records Intelligence System</h1>
              <p className="signup-left-description">Institutional user registration and credential issuance for jurisdictional cadastral officers and authorized land record researchers.</p>

              <div className="signup-governance-title">ACCESS TIER GOVERNANCE</div>
              <div className="signup-governance-card">
                <div className="signup-governance-card-head"><span><span className="signup-governance-icon" aria-hidden="true">✓</span>Access Tier Notice</span><b>Read-Only Default</b></div>
                <p>All newly registered accounts default strictly to Read-Only / Citizen Inquirer status. Higher-tier permissions require formal administrative endorsement and departmental role assignment.</p>
              </div>
              <div className="signup-governance-card">
                <div className="signup-governance-card-head"><span><span className="signup-governance-icon signup-governance-icon-warning" aria-hidden="true">▣</span>ROLE-VERIFICATION CONTROL</span><b className="signup-mandatory">MANDATORY</b></div>
                <p>Deed ingestion, parcel polygon mutation, and cadastral dispute adjudication remain provisioned only after institutional verification.</p>
              </div>
            </div>
            <footer className="signup-institutional-footer"><span>⌂ &nbsp; DEPT. OF LAND RESOURCES</span><strong>SIH 2026</strong></footer>
          </aside>

          <section className="signup-form-panel" aria-label="Create account">
            <svg className="signup-contours" viewBox="0 0 200 200" fill="none" aria-hidden="true"><circle cx="180" cy="20" r="70" stroke="#071f3b" strokeWidth="1.5" /><circle cx="180" cy="20" r="120" stroke="#071f3b" /></svg>
            <div className="signup-form-content">
              <div className="signup-form-rail"><strong>REGISTRATION FORM</strong><span>DOC-REV-2026-REG</span></div>
              <h2>Create Bhoomi Intel Account</h2>
              <p className="signup-form-subtitle">Jurisdictional institutional registration for national cadastre audit &amp; mutation network.</p>
              <div className="signup-readonly-notice" role="note">
                <span aria-hidden="true">i</span><div><strong>Default Access: Read-Only.</strong> Accounts are created with sanitized public parcel inspection rights. Operational adjudication privileges are provisioned post role-verification.</div>
              </div>

              <Alert tone="error" title="Account not created">{formError}</Alert>

              <form className="signup-form" onSubmit={submit} noValidate>
                <div className="signup-field">
                  <div className="signup-field-label"><label htmlFor="signup-name">Full Legal Name <em>*</em></label><span>As per Gazette / Official ID</span></div>
                  <input id="signup-name" name="name" type="text" autoComplete="name" placeholder="Your full name" value={name} disabled={busy} required aria-invalid={!!errors.name} onChange={(e) => setName(e.target.value)} />
                  {errors.name && <p className="signup-field-error">{errors.name}</p>}
                </div>
                <div className="signup-field">
                  <div className="signup-field-label"><label htmlFor="signup-id">Institutional ID / Official ID Number <em>*</em></label><span>Govt Emp ID / Cadastral Reg</span></div>
                  <input id="signup-id" name="idNumber" type="text" autoComplete="off" placeholder="e.g. ID-2026-001" value={idNumber} disabled={busy} required aria-invalid={!!errors.idNumber} onChange={(e) => setIdNumber(e.target.value)} />
                  {errors.idNumber && <p className="signup-field-error">{errors.idNumber}</p>}
                </div>
                <div className="signup-field">
                  <div className="signup-field-label"><label htmlFor="signup-email">Official Email ID <em>*</em></label><span>@gov.in or authorized domain</span></div>
                  <div className="signup-input-wrap signup-email-wrap"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="m3 8 7.89 5.26a2 2 0 0 0 2.22 0L21 8M5 19h14a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2Z" /></svg><input id="signup-email" name="email" type="email" autoComplete="email" placeholder="officer.name@nic.in" value={email} disabled={busy} required aria-invalid={!!errors.email} onChange={(e) => setEmail(e.target.value)} /><span aria-hidden="true">@</span></div>
                  {errors.email && <p className="signup-field-error">{errors.email}</p>}
                </div>
                <div className="signup-password-grid">
                  <div className="signup-field">
                    <div className="signup-field-label"><label htmlFor="signup-password">Password <em>*</em></label></div>
                    <div className="signup-input-wrap"><input id="signup-password" name="password" type={showPassword ? "text" : "password"} autoComplete="new-password" placeholder="••••••••" value={password} disabled={busy} required aria-invalid={!!errors.password} onChange={(e) => setPassword(e.target.value)} />{eye(showPassword, setShowPassword, "password")}</div>
                    {errors.password ? <p className="signup-field-error">{errors.password}</p> : <p className="signup-field-hint">Min 8 chars, 1 numeral</p>}
                  </div>
                  <div className="signup-field">
                    <div className="signup-field-label"><label htmlFor="signup-confirm">Confirm Password <em>*</em></label></div>
                    <div className="signup-input-wrap"><input id="signup-confirm" name="confirm" type={showConfirm ? "text" : "password"} autoComplete="new-password" placeholder="••••••••" value={confirm} disabled={busy} required aria-invalid={!!errors.confirm} onChange={(e) => setConfirm(e.target.value)} />{eye(showConfirm, setShowConfirm, "confirm password")}</div>
                    {errors.confirm ? <p className="signup-field-error">{errors.confirm}</p> : <p className="signup-field-hint">Re-enter identically</p>}
                  </div>
                </div>

                <label className={`signup-declaration ${declarationError ? "signup-declaration-error" : ""}`}>
                  <input type="checkbox" checked={declarationAccepted} disabled={busy} onChange={(e) => { setDeclarationAccepted(e.target.checked); setDeclarationError(""); }} />
                  <span>I formally declare that the supplied credentials are authentic and comply with Section 65B of the Indian Evidence Act and National Land Records Modernization Programme standards.</span>
                </label>
                {declarationError && <p className="signup-field-error signup-declaration-message">{declarationError}</p>}

                <Button type="submit" variant="primary" fullWidth disabled={busy} className="signup-submit">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><circle cx="9" cy="7" r="4" /><path d="M3 21a6 6 0 0 1 12 0M18 9v6M15 12h6" /></svg>
                  <span>{busy ? "Creating account…" : "Create Account"}</span>
                </Button>
              </form>
            </div>

            <div className="signup-form-footer">
              <div className="signup-signin-return">Already have an institutional account? <a href="#/login">Sign In to Revenue Console <span aria-hidden="true">→</span></a></div>
              <div className="signup-status-row"><span><i aria-hidden="true" />Statutory Audit Logging Active</span><span>Security Guidelines &nbsp; • &nbsp; Helpdesk &amp; Support</span></div>
            </div>
          </section>
        </div>
      </main>

      <footer className="login-technical-footer">
        <span>BHOOMI INTEL PROTOCOL v4.2.1-Prod &nbsp;•&nbsp; NODE: PUNE-DC-R08 &nbsp;•&nbsp; PORTAL: AUTH_SV_26</span>
        <span>SMART INDIA HACKATHON 2026 &nbsp;•&nbsp; <strong>PS-26018</strong></span>
      </footer>
    </div>
  );
}

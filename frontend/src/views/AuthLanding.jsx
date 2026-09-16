import Button from "../components/Button.jsx";
import "../styles/login.css";

/** Workspace entry (route #/auth).
 *
 * One primary path (sign in) with account creation offered as a secondary
 * choice — the previous screen showed two near-identical cards labelled
 * "Login" and "Sign in", which read as the same action twice. The brand panel
 * carries three concise capability statements so the left column holds real
 * content instead of vertical emptiness.
 *
 * Routes are unchanged: #/login and #/sign-in.
 */

const CAPABILITIES = [
  {
    title: "Reads difficult documents",
    body: "Scanned, faded and handwritten land records are converted into structured fields.",
  },
  {
    title: "Shows what needs checking",
    body: "Fixed verification rules flag uncertain values instead of hiding them.",
  },
  {
    title: "Keeps an officer in control",
    body: "Nothing is approved automatically, and every decision is recorded.",
  },
];

export default function AuthLanding() {
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

        <div className="login-brand-body">
          <h1>Land Record Intelligence</h1>
          <p className="login-lede">From legacy documents to structured, review-ready records.</p>

          <ul className="login-caps">
            {CAPABILITIES.map((c) => (
              <li key={c.title}>
                <span className="login-caps-rule" aria-hidden="true" />
                <div>
                  <strong>{c.title}</strong>
                  <p>{c.body}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div className="login-brand-foot">
          <span className="login-live"><span className="login-live-dot" aria-hidden="true" />SIH 2026 • PS-26018</span>
          <span>Role-based access • Full audit trail</span>
        </div>
      </section>

      <section className="login-panel" aria-label="Enter the workspace">
        <div className="login-context">
          <span className="login-context-crumb">
            <span className="login-context-dot" aria-hidden="true" />
            <span>National Cadastre Portal</span>
            <span className="sep">/</span>
            <strong>Workspace entry</strong>
          </span>
        </div>

        <div className="login-form-wrap">
          <h2>Sign in to your workspace</h2>
          <p className="login-sub">
            Use the official account issued to you. Your role determines what you can do once
            you are inside.
          </p>

          <Button
            variant="primary"
            fullWidth
            onClick={() => { window.location.hash = "#/login"; }}
          >
            Sign in
          </Button>

          <p className="login-alt">
            Don&apos;t have an account yet?{" "}
            <a href="#/sign-in">Create one</a>
            <span className="login-alt-note">New accounts start with read-only access.</span>
          </p>
        </div>

        <div className="login-foot">
          <span><span className="login-node-chip">SIH 2026 • PS-26018</span></span>
          <span>Strictly authorized personnel only</span>
        </div>
      </section>
    </div>
  );
}

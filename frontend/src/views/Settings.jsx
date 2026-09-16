import { useState } from "react";
import Alert from "../components/Alert.jsx";
import Button from "../components/Button.jsx";
import EmptyState from "../components/EmptyState.jsx";
import ErrorState from "../components/ErrorState.jsx";
import PageHeader from "../components/PageHeader.jsx";
import Skeleton from "../components/Skeleton.jsx";
import TextInput from "../components/TextInput.jsx";
import { friendlyMessage, requestIdOf } from "../components/errors.js";
import { getApiUrl, getMe, setApiUrl, setUser } from "../api/client";

/** Settings (route #/settings) — Stitch 455495cd structure, strictly
 * limited to supported functionality. The backend exposes no profile
 * update, password change, preferences, or notification endpoints, so
 * those sections do not exist here: profile/account render read-only from
 * GET /me, sign-out uses the real logout flow, and only the local backend
 * API URL is editable (client-side setting, labeled as such). Nothing
 * claims a server save that never happened; there is no danger zone
 * because no destructive backend action exists.
 */
export default function Settings({ user, onLogout }) {
  const [profile, setProfile] = useState(user || null);
  const [profileError, setProfileError] = useState("");
  const [profileRef, setProfileRef] = useState("");
  const [profileLoading, setProfileLoading] = useState(false);
  const [apiUrl, setApiUrlDraft] = useState(getApiUrl());
  const [apiSaved, setApiSaved] = useState(false);
  const [signingOut, setSigningOut] = useState(false);

  async function refreshProfile() {
    setProfileLoading(true);
    setProfileError("");
    setProfileRef("");
    try {
      // GET /api/v1/auth/me — the authoritative account record.
      const me = await getMe();
      setUser(me);
      setProfile(me);
    } catch (err) {
      setProfileError(friendlyMessage(err));
      setProfileRef(requestIdOf(err));
    } finally {
      setProfileLoading(false);
    }
  }

  function saveApiUrl(e) {
    e.preventDefault();
    // Local client setting only (localStorage) — labeled honestly, and the
    // write is synchronous so "Saved" is truthful, never a server claim.
    setApiUrl(apiUrl);
    setApiUrlDraft(getApiUrl());
    setApiSaved(true);
  }

  async function signOut() {
    if (signingOut) return;
    setSigningOut(true);
    try {
      await onLogout();
    } finally {
      setSigningOut(false);
    }
  }

  return (
    <div className="vstack">
      <PageHeader
        title="Settings"
        sub="Account, session, and workspace configuration."
      />

      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>Profile &amp; identity</h2>
            <p className="panel-sub">Your account details. To change them, contact your workspace administrator.</p>
          </div>
          <Button variant="secondary" disabled={profileLoading} onClick={refreshProfile}>
            {profileLoading ? "Refreshing…" : "Refresh"}
          </Button>
        </div>
        {profileLoading && !profile && <Skeleton lines={3} />}
        {profileError && <ErrorState title="Profile unavailable" message={profileError} requestId={profileRef || undefined} onRetry={refreshProfile} />}
        {profile && (
          <dl className="kv">
            <div><dt>Display name</dt><dd>{profile.name || "—"}</dd></div>
            <div><dt>Email</dt><dd>{profile.email}</dd></div>
            <div><dt>ID number</dt><dd>{profile.id_number || "—"}</dd></div>
            <div><dt>Role</dt><dd className="kv-cap">{profile.role}</dd></div>
            <div><dt>Status</dt><dd className="kv-cap">{profile.status || "—"}</dd></div>
          </dl>
        )}
        {!profile && !profileLoading && !profileError && (
          <EmptyState title="No profile loaded">Refresh to load the account record.</EmptyState>
        )}
      </div>

      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>Security &amp; session</h2>
            <p className="panel-sub">Your sign-in is confirmed each time the workspace loads. Password changes are not available yet.</p>
          </div>
        </div>
        <dl className="kv">
          <div><dt>This session</dt><dd>Signed in on this browser tab only. Closing the tab signs you out.</dd></div>
          <div><dt>Sign out</dt><dd>Ends this session on this device</dd></div>
        </dl>
        <div className="upload-actions">
          <Button variant="secondary" disabled={signingOut} onClick={signOut}>
            {signingOut ? "Signing out…" : "Sign out"}
          </Button>
        </div>
      </div>

      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>Workspace</h2>
            <p className="panel-sub">Where this browser looks for the workspace service. Change it only if you were asked to.</p>
          </div>
        </div>
        {apiSaved && <Alert tone="success" title="Saved">API URL updated to {getApiUrl()}.</Alert>}
        <form onSubmit={saveApiUrl}>
          <TextInput
            label="Service address"
            hint="Local only"
            id="settings-api-url"
            value={apiUrl}
            onChange={(e) => { setApiUrlDraft(e.target.value); setApiSaved(false); }}
          />
          <div className="upload-actions">
            <Button type="submit" variant="primary">Save</Button>
          </div>
        </form>
      </div>
    </div>
  );
}

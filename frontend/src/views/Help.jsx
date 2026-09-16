import PageHeader from "../components/PageHeader.jsx";
import { HELP_SECTIONS, TRUST_POINTS } from "../components/help.js";
import "../styles/help.css";

function Section({ id, title, children }) {
  return (
    <section className="panel help-section" aria-labelledby={`help-${id}`}>
      <h2 id={`help-${id}`}>{title}</h2>
      {children}
    </section>
  );
}

/** Help (route #/help) — Stitch 19e6210d structure with real product
 * content. Every statement matches implemented behavior and project
 * terminology (khata/khasra/survey/mutation, deterministic validation,
 * operator approval, append-only audit). No government/legal claims, no
 * fictional contacts — support means your workspace administrator.
 */
export default function Help() {
  return (
    <div className="vstack">
      <PageHeader
        title="Help"
        env="Operator manual"
        sub="How digitization, validation, review, and approval work in this workspace."
      />

      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>How trust works here</h2>
          </div>
        </div>
        <ul className="trust-list">
          {TRUST_POINTS.map((t) => (
            <li key={t}>{t}</li>
          ))}
        </ul>
        <nav className="help-toc" aria-label="Manual sections">
          <ol>
            {HELP_SECTIONS.map((s, i) => (
              <li key={s.id}><a href={`#help-${s.id}`}>{i + 1}. {s.title}</a></li>
            ))}
          </ol>
        </nav>
      </div>

      <Section id="getting-started" title="1. Getting started">
        <p>Sign in with your official account. <b>Operators</b> upload documents and then review, correct, approve or reject the records that come out of them. <b>Read-only users</b> can search and view records. Your role is shown in the sidebar.</p><p>A document travels through six stages: it is uploaded, read, its details are extracted, those details are checked, a person reviews anything uncertain, and finally a person approves or rejects the record. Nothing is approved automatically.</p>
      </Section>

      <Section id="upload" title="2. Upload a document">
        <p>You can upload a <b>PDF, PNG, JPEG or TIFF</b> file up to <b>10 MB</b>. You may also note the document type and language, which helps the system read it more accurately.</p><p>Your file is checked again after it arrives, so an unsupported or damaged file is refused even if it looked fine when you selected it.</p>
      </Section>

      <Section id="processing" title="3. Understanding processing">
        <p>After upload, the document is prepared, read, its details are extracted, and those details are checked. This usually takes under two minutes.</p><p>The processing screen shows the stage the document has actually reached. It never shows a stage as finished before it is. If a document fails, you can retry it.</p>
      </Section>

      <Section id="extraction" title="4. Understanding extraction">
        <p>Extraction is the system's reading of the document: owner name, survey number, area, village, and the other record details.</p><p>A value shown as <b>Not found</b> means the document did not contain it — it does not mean the system failed. Where the original text is available, you can open the evidence for a field to see where the value came from.</p>
      </Section>

      <Section id="confidence" title="5. Understanding confidence">
        <p>Confidence shows how sure the system is about a value it read: <b>High</b>, <b>Medium</b> or <b>Low</b>.</p><p>Treat it as a prompt for attention, not as proof. A value can be read clearly and still be wrong, so a failed check always outweighs high confidence. Confidence never establishes ownership or legal validity.</p>
      </Section>

      <Section id="review" title="6. Reviewing fields">
        <p>When something needs a person to look at it, the record is marked <b>Review required</b> and appears in the review queue.</p><p>Open the record, compare the flagged values against the original document, and correct anything that is wrong. Every correction needs a short reason, and the original value is always kept. When you are finished, mark the review complete.</p><p>Read-only users cannot make corrections.</p>
      </Section>

      <Section id="validation" title="7. Understanding validation">
        <p>Every record is checked against fixed verification rules — required details are present, formats look right, place names match the reference list, and the record does not duplicate an existing one.</p><p>Each finding explains what was found, why it needs attention, and what to check. These checks are deliberately independent of the system's own confidence, so a confidently misread value is still caught.</p>
      </Section>

      <Section id="approve" title="8. Approving a record">
        <p>A record can be approved once its required details are present, the items flagged for attention have been dealt with, and the review has been completed.</p><p>If approval is not yet possible, the record explains what is still outstanding. Approving records your decision as the responsible officer; it does not certify legal ownership. Rejecting requires a reason. Once approved or rejected, a record can no longer be changed.</p>
      </Section>

      <Section id="audit" title="9. Viewing audit history">
        <p>The audit history shows who did what, when, and what changed — every correction with its previous and new value and the reason given, every completed review, and every approval or rejection.</p><p>Audit entries are permanent. They cannot be edited or deleted by anyone using this application.</p>
      </Section>

      <Section id="export" title="10. Exporting a record">
        <p><b>Export</b> downloads the record as a file containing its values, confidence, verification findings and history — useful for sharing or keeping an offline copy.</p><p>This application is not connected to a live government registry. The integration endpoint exists only for testing and says so in its own response.</p>
      </Section>

      <div className="panel">
        <div className="panel-head">
          <div>
            <h2>Support</h2>
            <p className="panel-sub">No helpline is embedded here — account, access, and reference-data issues go through your workspace administrator.</p>
          </div>
        </div>
        <p>If sign-in fails, confirm the backend is reachable and your account is active. For incorrect data behavior, quote the request ID shown in the error message when reporting it.</p>
      </div>
    </div>
  );
}

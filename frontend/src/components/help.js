/** Help content registry. Section ids/titles plus the trust statements the
 * product must always communicate. Bodies live in the Help view; this
 * registry keeps coverage testable (all ten required sections present).
 */
export const HELP_SECTIONS = [
  { id: "getting-started", title: "Getting started" },
  { id: "upload", title: "Upload a document" },
  { id: "processing", title: "Understanding processing" },
  { id: "extraction", title: "Understanding extraction" },
  { id: "confidence", title: "Understanding confidence" },
  { id: "review", title: "Reviewing fields" },
  { id: "validation", title: "Understanding validation" },
  { id: "approve", title: "Approving a record" },
  { id: "audit", title: "Viewing audit history" },
  { id: "export", title: "Exporting a record" },
];

export const TRUST_POINTS = [
  "AI assists extraction: machine reading proposes field values, never conclusions.",
  "Validation identifies issues: deterministic rules flag problems a human must resolve.",
  "Human review provides workflow approval: only an authorized reviewer can approve or reject.",
  "Confidence does not itself establish legal ownership or legal validity.",
];

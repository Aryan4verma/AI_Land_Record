/** Canonical 14-field land-record schema (04_DATA_DICTIONARY) shared by the
 * extraction result and review views: labels and thematic groups.
 * Presentation only — values, confidence, and validation always come from
 * the backend and are never invented here.
 */
export const FIELD_LABELS: Record<string, string> = {
  owner_name: "Owner / holder name",
  father_or_spouse_name: "Father's / guardian's name",
  survey_number: "Survey number",
  khasra_number: "Khasra number",
  khata_number: "Khata number",
  area: "Area",
  area_unit: "Area unit",
  village: "Village",
  tehsil: "Tehsil",
  district: "District",
  land_classification: "Land classification",
  mutation_number: "Mutation number",
  registration_number: "Registration number",
  record_date: "Record date",
};

export interface FieldGroup {
  title: string;
  fields: string[];
}

export const FIELD_GROUPS: FieldGroup[] = [
  {
    title: "Parcel & location",
    fields: ["survey_number", "khasra_number", "khata_number", "area", "area_unit", "village", "tehsil", "district", "land_classification"],
  },
  {
    title: "Holder particulars",
    fields: ["owner_name", "father_or_spouse_name"],
  },
  {
    title: "Registration & mutation",
    fields: ["mutation_number", "registration_number", "record_date"],
  },
];

export function fieldLabel(name: string): string {
  return FIELD_LABELS[name] || name;
}

/** Correction payload mapping: empty input clears the value (null). */
export function correctionValue(draft: string): string | null {
  return draft === "" ? null : draft;
}

/** Terminal record states — read-only everywhere; the backend rejects
 * any further mutation with RECORD_FINALIZED.
 */
export function isTerminalRecord(status: string): boolean {
  return status === "APPROVED" || status === "REJECTED";
}

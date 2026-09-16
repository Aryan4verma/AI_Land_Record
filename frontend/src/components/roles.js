/** Role helpers. UI affordances ONLY — the backend enforces every rule and
 * remains the sole authority. Hiding an action here just stops us offering
 * something the backend would answer with 403.
 */

/** Roles that own the document + review/approval workflow. */
export function isOperator(user) {
  const role = user && typeof user.role === "string" ? user.role.trim().toLowerCase() : "";
  return role === "operator" || role === "admin";
}

/** The read-only role: search/view/export only. */
export function isReadOnly(user) {
  return !!user && !isOperator(user);
}

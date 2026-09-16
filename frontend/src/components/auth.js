/** Registration form validation. Pure field checks with the exact
 * user-facing messages; the backend re-validates everything and stays
 * authoritative (422/409 map to the same texts in the view).
 */export function validateRegistration(input) {
  const errors = {};
  const name = (input.name || "").trim();
  const idNumber = (input.idNumber || "").trim();
  const email = (input.email || "").trim();
  if (!name) errors.name = "Name is required.";
  if (!idNumber) errors.idNumber = "ID number is required.";
  if (!email) errors.email = "Enter a valid email address.";
  else if (!email.includes("@")) errors.email = "Enter a valid email address.";
  if (!input.password) errors.password = "Password is required.";
  else if (input.password.length < 8) errors.password = "Password must be at least 8 characters.";
  if (!input.confirm) errors.confirm = "Please confirm your password.";
  else if (input.confirm !== input.password) errors.confirm = "Passwords do not match.";
  return errors;
}

/**
 * Maps a registration-submit failure to {fields, form} using the exact
 * user-facing texts. Covers every observed failure class: known backend
 * codes, stale backend without the route (404 envelope), unreachable
 * backend / network failure (no HTTP status at all), and anything else.
 */
export function mapRegistrationError(err) {
  const fields = {};
  let form = "";
  const code = err && err.code;
  const status = err && err.status;
  if (code === "USER_EXISTS") {
    fields.email = "An account with this email already exists.";
  } else if (code === "INVALID_EMAIL") {
    fields.email = "Enter a valid email address.";
  } else if (code === "NAME_REQUIRED") {
    fields.name = "Name is required.";
  } else if (code === "ID_NUMBER_REQUIRED") {
    fields.idNumber = "ID number is required.";
  } else if (status === 404) {
    form = "Registration service not found. The backend may need to be updated and restarted.";
  } else if (status === 422) {
    fields.password = "Password must be at least 8 characters.";
  } else if (!status || status === 503 || status >= 500) {
    form = "We couldn't reach the authentication service. Please try again.";
  } else {
    form = "We couldn't create your account. Please try again.";
  }
  return { fields, form };
}

import Alert from "./Alert.jsx";
import { resultBanner } from "../api/types";

/** Overall result banner — green/amber/red display mapping over backend
 * document + validation states. Presentation only; nothing is decided here.
 */
export default function ResultBanner({ docStatus, validationStatus }) {
  const banner = resultBanner(docStatus, validationStatus);
  return (
    <div className="result-banner">
      <Alert tone={banner.tone} title={banner.title}>{banner.body}</Alert>
    </div>
  );
}

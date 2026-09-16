/** Guards a real defect found during browser QA.
 *
 * App.jsx called setUser(me) after GET /me but never imported it. The
 * ReferenceError was swallowed by an empty .catch(), so the signed-in user was
 * never restored on refresh — the sidebar lost its identity and, once the nav
 * became role-aware, an operator silently lost Upload and Review Queue.
 *
 * Nothing type-checks a bare identifier inside a .jsx file, so this asserts
 * that every api/client symbol App.jsx uses is actually imported.
 */
import { describe, expect, it } from "vitest";
// Vite raw import: reads the file as text without pulling in Node type defs.
import source from "../App.jsx?raw";

function importedClientSymbols(text: string): Set<string> {
  const m = text.match(/import\s*\{([^}]*)\}\s*from\s*["']\.\/api\/client["']/);
  if (!m) return new Set();
  return new Set(
    m[1]
      .split(",")
      .map((part) => part.trim())
      .filter(Boolean)
      // support `logout as clientLogout`
      .map((part) => (part.includes(" as ") ? part.split(" as ")[1].trim() : part)),
  );
}

describe("App.jsx client imports", () => {
  const imported = importedClientSymbols(source);

  it("imports the session helpers it calls", () => {
    for (const symbol of ["getMe", "getToken", "getUser", "setUser"]) {
      expect(imported.has(symbol), `${symbol} must be imported in App.jsx`).toBe(true);
    }
  });

  it("still calls setUser so the session is restored on refresh", () => {
    expect(source).toMatch(/setUser\(\s*me\s*\)/);
  });

  it("does not swallow unexpected session-restore errors silently", () => {
    // The catch must do something other than nothing.
    const emptyCatch = /\.catch\(\(\s*\)\s*=>\s*\{\s*(\/\/[^\n]*\n\s*)*\}\)/;
    expect(emptyCatch.test(source)).toBe(false);
  });
});

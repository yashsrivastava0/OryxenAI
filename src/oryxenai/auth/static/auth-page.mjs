import { bootstrapAuthPage } from "./auth-controller.mjs";
import { livingDraftMarkMarkup } from "./living-draft-mark.mjs";

// Purely decorative mount — no auth logic. The progress panel is only ever
// visible while something is genuinely waiting (auth-controller.mjs toggles
// panel visibility, not this mark), so mounting it "active" once is correct.
document.getElementById("draft-mark-slot")?.insertAdjacentHTML(
  "afterbegin",
  livingDraftMarkMarkup({ active: true }),
);

bootstrapAuthPage().catch(() => {
  document.getElementById("global-error")?.replaceChildren(
    document.createTextNode("Authentication could not be initialized."),
  );
  const panel = document.getElementById("sign-in-panel");
  if (panel) panel.hidden = false;
  document.getElementById("progress-panel")?.setAttribute("hidden", "");
});

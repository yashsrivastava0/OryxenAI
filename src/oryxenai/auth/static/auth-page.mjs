import { livingDraftMarkMarkup } from "./living-draft-mark.mjs";

// Entry-point versions alone do not invalidate cached module dependencies.
const controllerVersion = document.querySelector('meta[name="oryxenai-auth-controller-version"]')?.content || "";
const { bootstrapAuthPage } = await import(`./auth-controller.mjs?v=${encodeURIComponent(controllerVersion)}`);

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
  document.getElementById("global-error")?.removeAttribute("hidden");
  document.getElementById("sign-in-status")?.setAttribute("hidden", "");
  document.body.dataset.authOutcome = "provider_unavailable";
  window.dispatchEvent(new CustomEvent("oryxenai-auth-resolved"));
  const panel = document.getElementById("sign-in-panel");
  if (panel) panel.hidden = false;
  document.getElementById("progress-panel")?.setAttribute("hidden", "");
});

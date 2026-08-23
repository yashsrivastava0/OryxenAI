import { bootstrapAuthPage } from "./auth-controller.mjs";

bootstrapAuthPage().catch(() => {
  document.getElementById("global-error")?.replaceChildren(
    document.createTextNode("Authentication could not be initialized."),
  );
  const panel = document.getElementById("sign-in-panel");
  if (panel) panel.hidden = false;
  document.getElementById("progress-panel")?.setAttribute("hidden", "");
});

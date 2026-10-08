// Demo-only handshake. The opaque sandbox cannot read host storage or APIs.
const attempt = new URLSearchParams(location.search).get("attempt");
// Keep portfolio navigation inside the sample's existing history entry, so
// the host's Back action closes the dialog instead of undoing a child anchor.
document.addEventListener("click", event => {
  const anchor = event.target.closest?.("a[href^='#']");
  if (!anchor || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
  event.preventDefault();
  event.stopImmediatePropagation();
  location.replace(anchor.href);
}, { capture: true });
document.addEventListener("keydown", event => {
  if (event.key === "Escape") {
    event.preventDefault();
    parent.postMessage({ type: "oryxenai-demo-close", attempt }, "*");
  }
});
async function ready() {
  await document.fonts.ready;
  await Promise.all([...document.querySelectorAll(".demo-overview img")].map(image =>
    image.decode().catch(() => image.setAttribute("hidden", ""))));
  parent.postMessage({ type: "oryxenai-demo-ready", attempt }, "*");
}
if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", ready, { once: true });
else ready();

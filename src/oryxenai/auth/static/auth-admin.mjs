/** Functional, deliberately bounded administrator console. */

import { createAuthorizedFetch } from "./auth-runtime.mjs";

const state = { tab: "users", cursors: {}, pendingKeys: new Map() };

function node(documentRef, tag, value) {
  const result = documentRef.createElement(tag);
  if (value !== undefined) result.textContent = String(value);
  return result;
}

function actionKey(action, id) {
  return "admin:" + action + ":" + id;
}

function operationKey(action, id) {
  const key = actionKey(action, id);
  let value = state.pendingKeys.get(key);
  if (!value) {
    value = globalThis.crypto?.randomUUID?.() ||
      "admin-" + Date.now() + "-" + Math.random().toString(16).slice(2);
    state.pendingKeys.set(key, value);
  }
  return value;
}

export function adminEndpoint(action, tab, id) {
  if (action === "readmit") return "/api/v1/admin/deleted-identities/" + id + "/readmit";
  if (action === "reset_entitlement") return "/api/v1/admin/users/" + id + "/entitlement/reset";
  if (["promote", "demote", "suspend", "restore"].includes(action)) {
    return "/api/v1/admin/users/" + id + "/" + action;
  }
  if (action === "delete" && tab === "users") return "/api/v1/admin/users/" + id + "/delete";
  if (action === "code-generator-retry") return "/api/v1/admin/projects/" + id + "/code-generator/retry";
  if (action === "code-generator-regenerate") return "/api/v1/admin/projects/" + id + "/code-generator/regenerate";
  return "/api/v1/admin/" + (tab === "legacy" ? "legacy-projects" : "projects") + "/" + id + "/delete";
}

function renderSummary(documentRef, summary) {
  const target = documentRef.getElementById("admin-summary");
  if (!target) return;
  target.replaceChildren();
  [
    ["Active users", summary.users?.active ?? 0],
    ["Projects", summary.projects?.active ?? 0],
    ["Running jobs", summary.jobs?.running ?? 0],
    ["Pending operations", summary.pending_operations ?? 0],
  ].forEach(([label, value]) => {
    const card = node(documentRef, "div");
    card.className = "admin-card";
    card.append(node(documentRef, "span", label), node(documentRef, "strong", value));
    target.append(card);
  });
}

function renderRows(documentRef, target, items, tab, onAction) {
  target.replaceChildren();
  if (!items.length) {
    target.append(node(documentRef, "p", "Nothing is visible in this view."));
    return;
  }
  items.forEach((item) => {
    const article = node(documentRef, "article");
    article.className = "admin-row";
    article.append(node(documentRef, "h3", item.username || item.id || "Untitled target"));
    const detail = node(documentRef, "p");
    detail.className = "muted";
    detail.textContent = tab === "users"
      ? [item.role, item.status, item.masked_email].join(" · ")
      : tab === "audit"
        ? [item.action, item.outcome, item.target_type].join(" · ")
        : tab === "deleted"
          ? [item.former_role, item.masked_email, item.readmission_approved ? "approved" : "awaiting approval"].join(" · ")
          : [item.status, item.owner_username || "legacy project"].join(" · ");
    article.append(detail);
    const actions = node(documentRef, "div");
    actions.className = "button-row admin-row-actions";
    if (tab === "users" && item.status !== "deleted") {
      const names = item.status === "suspended" ? ["restore"] : ["suspend"];
      if (item.role === "user") names.push("reset_entitlement", "promote");
      if (item.role === "admin") names.push("demote");
      names.push("delete");
      names.forEach((action) => {
        const button = node(documentRef, "button", action.replaceAll("_", " "));
        button.className = "secondary-button";
        button.type = "button";
        button.addEventListener("click", () => onAction(action, item));
        actions.append(button);
      });
    } else if (tab === "deleted" && !item.readmission_approved) {
      const button = node(documentRef, "button", "readmit identity");
      button.className = "secondary-button";
      button.type = "button";
      button.addEventListener("click", () => onAction("readmit", item));
      actions.append(button);
    } else if ((tab === "projects" || tab === "legacy") && item.status === "active") {
      ["delete", "code-generator-retry", "code-generator-regenerate"].forEach((action) => {
        const button = node(documentRef, "button", action.replaceAll("-", " "));
        button.className = "secondary-button";
        button.type = "button";
        button.addEventListener("click", () => onAction(action, item));
        actions.append(button);
      });
    }
    article.append(actions);
    target.append(article);
  });
}

export async function bootstrapAdminConsole({
  auth,
  fetchImpl = globalThis.fetch,
  documentRef = globalThis.document,
  location = globalThis.location,
}) {
  if (!documentRef?.getElementById("admin-panel")) return;
  const content = documentRef.getElementById("admin-content");
  const live = documentRef.getElementById("admin-live");
  const authorizedFetch = createAuthorizedFetch({
    auth,
    fetchImpl,
    onAuthFailure: async () => location?.replace?.("/sign-in"),
  });
  const request = async (path, init = {}) => {
    const response = await authorizedFetch(path, init);
    return response.json();
  };
  const load = async (reset) => {
    if (reset) state.cursors = {};
    live.textContent = "Loading safe administrator data.";
    try {
      renderSummary(documentRef, await request("/api/v1/admin/summary"));
      const cursor = state.cursors[state.tab];
      const endpoint = state.tab === "legacy"
        ? "/api/v1/admin/legacy-projects"
        : "/api/v1/admin/" + (state.tab === "audit"
          ? "audit-events"
          : state.tab === "deleted" ? "deleted-identities" : state.tab);
      const query = new URLSearchParams({ limit: "25" });
      if (cursor) query.set("cursor", cursor);
      const page = await request(endpoint + "?" + query.toString());
      renderRows(documentRef, content, page.items || [], state.tab, openAction);
      state.cursors[state.tab] = page.next_cursor || null;
      documentRef.getElementById("admin-load-more").hidden = !page.next_cursor;
      live.textContent = "Administrator data refreshed.";
    } catch (error) {
      content.replaceChildren(node(documentRef, "p", error?.message || "Administrator data is unavailable."));
      live.textContent = "Administrator data is unavailable.";
    }
  };
  const openAction = (action, item) => {
    const dialog = documentRef.getElementById("admin-confirm-dialog");
    const form = documentRef.getElementById("admin-confirm-form");
    const input = documentRef.getElementById("admin-confirm-input");
    const reason = documentRef.getElementById("admin-reason");
    const copy = documentRef.getElementById("admin-confirm-copy");
    if (!dialog || !form || !input || !reason || !copy) return;
    const target = item.username || String(item.id);
    copy.textContent = action.replaceAll("_", " ") + " " + target +
      ". This action is server-authorized and may be irreversible.";
    input.value = "";
    reason.value = "";
    dialog.showModal();
    input.focus();
    form.onsubmit = async (event) => {
      event.preventDefault();
      if (input.value !== target) {
        dialog.close();
        return;
      }
      const endpoint = adminEndpoint(action, state.tab, item.id);
      const button = documentRef.getElementById("admin-confirm-submit");
      button.disabled = true;
      try {
        await request(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Idempotency-Key": operationKey(action, item.id) },
          body: JSON.stringify({
            confirmation: item.id,
            username: item.username || undefined,
            reason: reason.value || undefined,
          }),
        });
        state.pendingKeys.delete(actionKey(action, item.id));
        dialog.close();
        await load(true);
      } catch (error) {
        live.textContent = error?.message || "The administrator request failed.";
      } finally {
        button.disabled = false;
      }
    };
  };
  documentRef.querySelectorAll("[data-admin-tab]").forEach((button) => {
    button.addEventListener("click", async () => {
      state.tab = button.dataset.adminTab;
      documentRef.querySelectorAll("[data-admin-tab]").forEach((tab) => {
        tab.setAttribute("aria-selected", String(tab === button));
      });
      await load(true);
    });
  });
  documentRef.getElementById("admin-refresh")?.addEventListener("click", () => load(true));
  documentRef.getElementById("admin-load-more")?.addEventListener("click", () => load(false));
  await load(true);
}

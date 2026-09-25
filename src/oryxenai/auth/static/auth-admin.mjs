/** Functional, deliberately bounded administrator console. */

import {
  clearPrivateState,
  createAuthorizedFetch,
  invalidateBrowserSession,
} from "./auth-runtime.mjs";

const state = { tab: "users", cursors: {}, pendingKeys: new Map() };

const TAB_META = {
  users: {
    title: "Users",
    subtitle: "Manage workspace users and their access, roles, and entitlements.",
  },
  projects: {
    title: "Projects",
    subtitle: "Monitor and manage workspace projects and their execution status.",
  },
  legacy: {
    title: "Legacy projects",
    subtitle: "These are older projects quarantined from the normal creator workflow.",
  },
  deleted: {
    title: "Deleted identities",
    subtitle: "These are tombstones for identities that have been deleted. They are awaiting authorized readmission review and cannot be used to sign in.",
  },
  operations: {
    title: "Operations",
    subtitle: "Audited administrative lifecycle operations for this workspace. Track progress, review status, and safely resume where available.",
  },
  audit: {
    title: "Audit trail",
    subtitle: "Review administrator actions and their outcomes.",
  },
};

function node(documentRef, tag, value, className) {
  const result = documentRef.createElement(tag);
  if (className) result.className = className;
  if (value !== undefined && value !== null) result.textContent = String(value);
  return result;
}

function formatDate(isoString) {
  if (!isoString) return "—";
  try {
    const d = new Date(isoString);
    if (Number.isNaN(d.getTime())) return "—";
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const month = months[d.getUTCMonth()];
    const day = d.getUTCDate();
    const year = d.getUTCFullYear();
    const hours = String(d.getUTCHours()).padStart(2, "0");
    const minutes = String(d.getUTCMinutes()).padStart(2, "0");
    return `${month} ${day}, ${year} ${hours}:${minutes}`;
  } catch {
    return "—";
  }
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
  if (action === "resume") return "/api/v1/admin/operations/" + id + "/resume";
  if (action === "readmit") return "/api/v1/admin/deleted-identities/" + id + "/readmit";
  if (action === "reset_entitlement") return "/api/v1/admin/users/" + id + "/entitlement/reset";
  if (["promote", "demote", "suspend", "restore"].includes(action)) {
    return "/api/v1/admin/users/" + id + "/" + action;
  }
  if (action === "delete" && tab === "users") return "/api/v1/admin/users/" + id + "/delete";
  if (action === "delete" && ["projects", "legacy"].includes(tab)) {
    return "/api/v1/admin/" + (tab === "legacy" ? "legacy-projects" : "projects") + "/" + id + "/delete";
  }
  throw new Error("Unsupported administrator action.");
}

export function adminSubmissionState(submitterValue, inputValue, target) {
  if (submitterValue !== "confirm") return "cancel";
  return inputValue === target ? "confirmed" : "mismatch";
}

function getMetricSvg(type) {
  if (type === "users") {
    return '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>';
  }
  if (type === "projects") {
    return '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>';
  }
  if (type === "jobs") {
    return '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>';
  }
  return '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>';
}

function renderSummary(documentRef, summary) {
  const target = documentRef.getElementById("admin-summary");
  if (!target) return;
  target.replaceChildren();

  const metrics = [
    {
      id: "users",
      label: "Active users",
      value: summary.users?.active ?? 0,
      sub: "Users with access to this workspace",
    },
    {
      id: "projects",
      label: "Projects",
      value: summary.projects?.active ?? 0,
      sub: "Total projects in this workspace",
    },
    {
      id: "jobs",
      label: "Running jobs",
      value: summary.jobs?.running ?? 0,
      sub: "Jobs currently in progress",
    },
    {
      id: "operations",
      label: "Pending operations",
      value: summary.pending_operations ?? 0,
      sub: "Operations awaiting processing",
    },
  ];

  metrics.forEach(({ id, label, value, sub }) => {
    const card = node(documentRef, "div", undefined, "admin-card admin-metric-card");

    const topRow = node(documentRef, "div", undefined, "metric-card-top");
    const iconWrap = node(documentRef, "span", undefined, "metric-card-icon");
    iconWrap.innerHTML = getMetricSvg(id);
    const labelSpan = node(documentRef, "span", label, "metric-card-label");
    topRow.append(iconWrap, labelSpan);

    const valStrong = node(documentRef, "strong", value, "metric-card-val");
    const subSpan = node(documentRef, "span", sub, "metric-card-sub");

    card.append(topRow, valStrong, subSpan);
    target.append(card);
  });
}

const ICONS = {
  trash: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>',
  retry: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>',
  regenerate: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
  resume: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="5 3 19 12 5 21 5 3"/></svg>',
  readmit: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/></svg>',
};

function createActionButton(documentRef, text, onClick, { isDestructive = false, iconSvg = null, isPrimaryAction = false } = {}) {
  const button = node(documentRef, "button", undefined, isDestructive ? "btn-action-destructive" : isPrimaryAction ? "btn-action-primary" : "secondary-button btn-action-secondary");
  button.type = "button";
  if (iconSvg) {
    const iconSpan = node(documentRef, "span", undefined, "btn-action-icon");
    iconSpan.innerHTML = iconSvg;
    button.append(iconSpan);
  }
  button.append(node(documentRef, "span", text, "btn-action-text"));
  button.addEventListener("click", onClick);
  return button;
}

function renderStatusPill(documentRef, status) {
  const pill = node(documentRef, "span", undefined, "admin-status-pill");
  const dot = node(documentRef, "span", "●", "status-dot");
  pill.append(dot);

  const lower = String(status || "").toLowerCase();
  if (lower === "active" || lower === "succeeded" || lower === "completed" || lower === "readmission approved") {
    pill.classList.add("status-active");
    pill.append(node(documentRef, "span", status === "completed" ? "Complete" : status));
  } else if (lower === "running") {
    pill.classList.add("status-running");
    pill.append(node(documentRef, "span", "Running"));
  } else if (lower === "suspended") {
    pill.classList.add("status-suspended");
    pill.append(node(documentRef, "span", "Suspended"));
  } else if (lower === "paused" || lower === "retryable_failure" || lower === "awaiting approval" || lower === "pending") {
    pill.classList.add("status-paused");
    pill.append(node(documentRef, "span", lower === "retryable_failure" ? "Paused" : status));
  } else if (lower === "rejected" || lower === "failed") {
    pill.classList.add("status-failed");
    dot.textContent = "✕";
    dot.className = "status-icon-cross";
    pill.append(node(documentRef, "span", lower === "rejected" ? "Rejected" : "Failed"));
  } else {
    pill.classList.add("status-neutral");
    pill.append(node(documentRef, "span", status || "—"));
  }

  if (lower === "succeeded" || lower === "completed") {
    dot.textContent = "✓";
    dot.className = "status-icon-check";
  }

  return pill;
}

function renderRows(documentRef, target, items, tab, onAction, { append = false, me = null } = {}) {
  if (!append) target.replaceChildren();

  const countEl = documentRef.getElementById("admin-item-count");
  if (countEl) {
    countEl.textContent = items.length
      ? `Showing ${items.length} ${items.length === 1 ? "record" : "records"}`
      : "";
  }

  if (!items.length) {
    if (!append) {
      const emptyWrap = node(documentRef, "div", undefined, "admin-empty-state");
      emptyWrap.append(
        node(documentRef, "p", "Nothing is visible in this view.", "admin-empty-title"),
        node(documentRef, "p", "There are no safe records to display for this view at this time.", "admin-empty-desc")
      );
      target.append(emptyWrap);
    }
    return;
  }

  let tableWrap = target.querySelector(".admin-table-wrap");
  let tbody = target.querySelector(".admin-tbody");

  if (!append || !tableWrap || !tbody) {
    target.replaceChildren();
    tableWrap = node(documentRef, "div", undefined, "admin-table-wrap");
    const table = node(documentRef, "table", undefined, "admin-table");
    const thead = node(documentRef, "thead", undefined, "admin-thead");
    const headRow = node(documentRef, "tr", undefined, "admin-head-tr");

    let columns = [];
    if (tab === "users") {
      columns = ["Name", "Role", "Status", "Email", "Last active", "Actions"];
    } else if (tab === "projects") {
      columns = ["Project / Session", "Status", "Owner", "Last activity", "Actions"];
    } else if (tab === "legacy") {
      columns = ["Project Name", "Status", "Owner / Legacy", "Actions"];
    } else if (tab === "deleted") {
      columns = ["Username", "Former role", "Email", "State", "Action"];
    } else if (tab === "operations") {
      columns = ["Operation", "Action", "Status", "Current step", "Last safe error", "Action"];
    } else if (tab === "audit") {
      columns = ["Event", "Action", "Outcome", "Target", "Timestamp"];
    }

    columns.forEach((col) => {
      const th = node(documentRef, "th", col, "admin-th");
      if (col === "Actions" || col === "Action") th.classList.add("admin-th-actions");
      headRow.append(th);
    });

    thead.append(headRow);
    tbody = node(documentRef, "tbody", undefined, "admin-tbody");
    table.append(thead, tbody);
    tableWrap.append(table);
    target.append(tableWrap);
  }

  items.forEach((item) => {
    const tr = node(documentRef, "tr", undefined, "admin-tr admin-row");

    if (tab === "users") {
      // Name
      const tdName = node(documentRef, "td", undefined, "admin-td td-name");
      const nameBox = node(documentRef, "div", undefined, "user-cell-box");
      const nameHeading = node(documentRef, "h3", item.username || String(item.id).slice(0, 8), "user-cell-name");
      nameBox.append(nameHeading);
      tdName.append(nameBox);

      // Role
      const tdRole = node(documentRef, "td", undefined, "admin-td td-role");
      const roleBadge = node(documentRef, "span", item.role === "admin" ? "Administrator" : "Member", "admin-role-badge " + (item.role === "admin" ? "role-admin" : "role-user"));
      tdRole.append(roleBadge);

      // Status
      const tdStatus = node(documentRef, "td", undefined, "admin-td td-status");
      tdStatus.append(renderStatusPill(documentRef, item.status));

      // Email
      const tdEmail = node(documentRef, "td", item.masked_email || "—", "admin-td td-email");

      // Last active
      const tdActive = node(documentRef, "td", formatDate(item.last_seen_at || item.created_at), "admin-td td-date");

      // Actions
      const tdActions = node(documentRef, "td", undefined, "admin-td td-actions");
      const actions = node(documentRef, "div", undefined, "button-row admin-row-actions");
      const isSelf = me?.id && String(me.id) === String(item.id);

      if (item.status !== "deleted" && !isSelf) {
        if (item.status === "suspended") {
          actions.append(createActionButton(documentRef, "Restore", () => onAction("restore", item)));
        } else {
          actions.append(createActionButton(documentRef, "Suspend", () => onAction("suspend", item)));
        }
        if (item.role === "user") {
          actions.append(createActionButton(documentRef, "Reset entitlement", () => onAction("reset_entitlement", item)));
          actions.append(createActionButton(documentRef, "Promote", () => onAction("promote", item)));
        }
        if (item.role === "admin") {
          actions.append(createActionButton(documentRef, "Demote", () => onAction("demote", item)));
        }
        actions.append(createActionButton(documentRef, "Delete", () => onAction("delete", item), { isDestructive: true, iconSvg: ICONS.trash }));
      }
      tdActions.append(actions);

      tr.append(tdName, tdRole, tdStatus, tdEmail, tdActive, tdActions);
    } else if (tab === "projects") {
      const shortId = String(item.id).slice(0, 8);
      const tdProject = node(documentRef, "td", undefined, "admin-td td-project");
      const projBox = node(documentRef, "div", undefined, "project-cell-box");
      const projTitle = node(documentRef, "h3", `Project ${shortId}`, "project-cell-title");
      const lastStage = item.stage_statuses?.length ? item.stage_statuses[item.stage_statuses.length - 1] : "Active project";
      const projSub = node(documentRef, "p", lastStage, "project-cell-sub");
      projBox.append(projTitle, projSub);
      tdProject.append(projBox);

      const tdStatus = node(documentRef, "td", undefined, "admin-td td-status");
      tdStatus.append(renderStatusPill(documentRef, item.status));

      const tdOwner = node(documentRef, "td", item.owner_username || item.owner_masked_email || "—", "admin-td td-owner");
      const tdActive = node(documentRef, "td", formatDate(item.updated_at || item.created_at), "admin-td td-date");

      const tdActions = node(documentRef, "td", undefined, "admin-td td-actions");
      const actions = node(documentRef, "div", undefined, "button-row admin-row-actions");
      if (item.status === "active") {
        actions.append(createActionButton(documentRef, "Delete", () => onAction("delete", item), { isDestructive: true, iconSvg: ICONS.trash }));
      }
      tdActions.append(actions);

      tr.append(tdProject, tdStatus, tdOwner, tdActive, tdActions);
    } else if (tab === "legacy") {
      const shortId = String(item.id).slice(0, 8);
      const tdProject = node(documentRef, "td", undefined, "admin-td td-project");
      const projTitle = node(documentRef, "h3", `Legacy project ${shortId}`, "project-cell-title");
      tdProject.append(projTitle);

      const tdStatus = node(documentRef, "td", undefined, "admin-td td-status");
      tdStatus.append(renderStatusPill(documentRef, item.status));

      const tdOwner = node(documentRef, "td", undefined, "admin-td td-owner");
      const ownerBox = node(documentRef, "div", undefined, "legacy-owner-box");
      ownerBox.append(
        node(documentRef, "span", item.owner_username || "—", "legacy-owner-name"),
        node(documentRef, "span", "Legacy project", "legacy-owner-badge")
      );
      tdOwner.append(ownerBox);

      const tdActions = node(documentRef, "td", undefined, "admin-td td-actions");
      const actions = node(documentRef, "div", undefined, "button-row admin-row-actions");
      if (item.status === "active") {
        actions.append(createActionButton(documentRef, "Delete", () => onAction("delete", item), { isDestructive: true, iconSvg: ICONS.trash }));
      }
      tdActions.append(actions);

      tr.append(tdProject, tdStatus, tdOwner, tdActions);
    } else if (tab === "deleted") {
      const tdUser = node(documentRef, "td", item.former_app_user_id ? String(item.former_app_user_id).slice(0, 8) : "Identity " + String(item.id).slice(0, 8), "admin-td td-user");
      const tdRole = node(documentRef, "td", item.former_role || "—", "admin-td td-role");
      const tdEmail = node(documentRef, "td", item.masked_email || "—", "admin-td td-email");
      const tdState = node(documentRef, "td", undefined, "admin-td td-state");
      tdState.append(renderStatusPill(documentRef, item.readmission_approved ? "Readmission approved" : "Awaiting approval"));

      const tdAction = node(documentRef, "td", undefined, "admin-td td-actions");
      const actions = node(documentRef, "div", undefined, "button-row admin-row-actions");
      if (!item.readmission_approved) {
        actions.append(createActionButton(documentRef, "Readmit identity", () => onAction("readmit", item), { iconSvg: ICONS.readmit, isPrimaryAction: true }));
      } else {
        actions.append(node(documentRef, "span", "—", "admin-text-muted"));
      }
      tdAction.append(actions);

      tr.append(tdUser, tdRole, tdEmail, tdState, tdAction);
    } else if (tab === "operations") {
      const shortId = "op_" + String(item.id).slice(0, 8);
      const tdOp = node(documentRef, "td", shortId, "admin-td td-mono");
      const tdActionName = node(documentRef, "td", String(item.action || "").replaceAll("_", " "), "admin-td td-capitalize");
      const tdStatus = node(documentRef, "td", undefined, "admin-td td-status");
      tdStatus.append(renderStatusPill(documentRef, item.status));
      const tdStep = node(documentRef, "td", item.step || "—", "admin-td");
      const tdError = node(documentRef, "td", item.last_error_code || "—", "admin-td td-mono");

      const tdAction = node(documentRef, "td", undefined, "admin-td td-actions");
      const actions = node(documentRef, "div", undefined, "button-row admin-row-actions");
      if (item.resumable) {
        actions.append(createActionButton(documentRef, "Resume safely", () => onAction("resume", item), { iconSvg: ICONS.resume, isPrimaryAction: true }));
      } else {
        actions.append(node(documentRef, "span", "—", "admin-text-muted"));
      }
      tdAction.append(actions);

      tr.append(tdOp, tdActionName, tdStatus, tdStep, tdError, tdAction);
    } else if (tab === "audit") {
      const shortId = "evt_" + String(item.id).slice(0, 8);
      const tdEvt = node(documentRef, "td", shortId, "admin-td td-mono");
      const tdActionName = node(documentRef, "td", String(item.action || "").replaceAll("_", " "), "admin-td td-capitalize");
      const tdOutcome = node(documentRef, "td", undefined, "admin-td td-status");
      tdOutcome.append(renderStatusPill(documentRef, item.outcome || "completed"));
      const targetStr = `${item.target_type || "Target"}${item.target_id ? " · " + String(item.target_id).slice(0, 8) : ""}`;
      const tdTarget = node(documentRef, "td", targetStr, "admin-td");
      const tdTime = node(documentRef, "td", formatDate(item.created_at), "admin-td td-date");

      tr.append(tdEvt, tdActionName, tdOutcome, tdTarget, tdTime);
    }

    tbody.append(tr);
  });
}

function updateViewHeader(documentRef, tab) {
  const meta = TAB_META[tab] || TAB_META.users;
  const titleEl = documentRef.getElementById("admin-view-title");
  const subEl = documentRef.getElementById("admin-view-subtitle");
  const pillEl = documentRef.getElementById("admin-view-pill");
  const boundaryEl = documentRef.getElementById("admin-deletion-boundary");

  if (titleEl) titleEl.textContent = meta.title;
  if (subEl) subEl.textContent = meta.subtitle;

  if (boundaryEl) {
    boundaryEl.hidden = tab !== "deleted";
  }

  if (pillEl) {
    if (tab === "operations") {
      pillEl.replaceChildren();
      const dot = node(documentRef, "span", "✓", "pill-dot-check");
      pillEl.append(dot, node(documentRef, "span", " All operations reconciled."));
      pillEl.hidden = false;
    } else if (tab === "audit") {
      pillEl.replaceChildren();
      pillEl.append(node(documentRef, "span", "Read-only audit trail · showing recent events."));
      pillEl.hidden = false;
    } else {
      pillEl.hidden = true;
    }
  }
}

export async function bootstrapAdminConsole({
  auth,
  fetchImpl = globalThis.fetch,
  documentRef = globalThis.document,
  location = globalThis.location,
  me = null,
}) {
  if (!documentRef?.getElementById("admin-panel")) return;
  const content = documentRef.getElementById("admin-content");
  const live = documentRef.getElementById("admin-live");

  // Populate admin avatar initials
  if (me?.username) {
    const initials = me.username.slice(0, 2).toUpperCase();
    documentRef.querySelectorAll('[data-user="monogram"]').forEach((el) => {
      el.textContent = initials;
    });
  }

  const setLiveMessage = (msg, isError = false) => {
    if (!live) return;
    live.replaceChildren();
    if (isError) {
      live.className = "admin-live-banner live-error";
      const icon = node(documentRef, "span", "⚠", "live-warn-icon");
      live.append(icon, node(documentRef, "span", " " + msg));
    } else {
      live.className = "admin-live-banner";
      const svg = node(documentRef, "span");
      svg.innerHTML = '<svg class="live-check-svg" width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/></svg>';
      live.append(svg, node(documentRef, "span", " " + msg));
    }
  };

  const authorizedFetch = createAuthorizedFetch({
    auth,
    fetchImpl,
    onAuthFailure: async () => {
      content?.replaceChildren?.();
      documentRef.getElementById("admin-summary")?.replaceChildren?.();
      if (live) setLiveMessage("Your administrator session ended.", true);
      try { clearPrivateState(globalThis.sessionStorage); } catch { /* unavailable storage */ }
      await invalidateBrowserSession({ auth });
      location?.replace?.("/sign-in");
    },
  });

  const request = async (path, init = {}) => {
    const response = await authorizedFetch(path, init);
    return response.json();
  };

  const load = async (reset) => {
    if (reset) state.cursors = {};
    const loadMore = documentRef.getElementById("admin-load-more");
    if (loadMore) loadMore.disabled = true;
    setLiveMessage("Loading safe administrator data.");
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
      renderRows(documentRef, content, page.items || [], state.tab, openAction, {
        append: !reset,
        me,
      });
      state.cursors[state.tab] = page.next_cursor || null;
      if (loadMore) loadMore.hidden = !page.next_cursor;
      setLiveMessage("Administrator data refreshed.");
    } catch (error) {
      content.replaceChildren(node(documentRef, "p", error?.message || "Administrator data is unavailable.", "admin-error-text"));
      setLiveMessage("Administrator data is unavailable.", true);
    } finally {
      if (loadMore) loadMore.disabled = false;
    }
  };

  const openAction = (action, item) => {
    const dialog = documentRef.getElementById("admin-confirm-dialog");
    const form = documentRef.getElementById("admin-confirm-form");
    const input = documentRef.getElementById("admin-confirm-input");
    const reason = documentRef.getElementById("admin-reason");
    const copy = documentRef.getElementById("admin-confirm-copy");
    const actionNameEl = documentRef.getElementById("admin-action-name");
    const actionTargetValEl = documentRef.getElementById("admin-action-target-val");
    const confirmLabelEl = documentRef.getElementById("admin-confirm-label");
    const submitBtn = documentRef.getElementById("admin-confirm-submit");
    const closeBtn = documentRef.getElementById("admin-confirm-close");
    const iconBadge = documentRef.getElementById("admin-modal-icon-badge");

    if (!dialog || !form || !input || !reason || !copy) return;

    const target = item.username || String(item.id);
    const readableAction = action === "delete"
      ? (state.tab === "users" ? "Delete user" : state.tab === "legacy" ? "Delete legacy project" : "Delete project")
      : action === "suspend" ? "Suspend user"
      : action === "restore" ? "Restore user"
      : action === "reset_entitlement" ? "Reset entitlement"
      : action === "promote" ? "Promote user"
      : action === "demote" ? "Demote administrator"
      : action === "readmit" ? "Readmit identity"
      : action === "resume" ? "Resume operation"
      : action.replaceAll("_", " ");

    if (actionNameEl) actionNameEl.textContent = readableAction;
    if (actionTargetValEl) actionTargetValEl.textContent = target;
    if (confirmLabelEl) confirmLabelEl.textContent = `Type ${target} to confirm`;

    if (iconBadge) {
      if (action === "delete") {
        iconBadge.className = "admin-modal-icon-badge icon-destructive";
        iconBadge.innerHTML = ICONS.trash;
      } else if (action === "suspend" || action === "demote") {
        iconBadge.className = "admin-modal-icon-badge icon-warning";
        iconBadge.innerHTML = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>';
      } else {
        iconBadge.className = "admin-modal-icon-badge icon-accent";
        iconBadge.innerHTML = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>';
      }
    }

    if (submitBtn) {
      if (action === "delete") {
        submitBtn.textContent = "Confirm delete";
        submitBtn.className = "primary-button modal-btn-confirm btn-confirm-destructive";
      } else {
        submitBtn.textContent = "Confirm action";
        submitBtn.className = "primary-button modal-btn-confirm btn-confirm-primary";
      }
    }

    copy.textContent = `${readableAction} ${target}. This action is server-authorized and may be irreversible.`;
    input.value = "";
    reason.value = "";

    const handleClose = () => {
      dialog.close();
    };
    if (closeBtn) closeBtn.onclick = handleClose;

    dialog.showModal();
    input.focus();

    form.onsubmit = async (event) => {
      event.preventDefault();
      const submission = adminSubmissionState(event.submitter?.value, input.value, target);
      if (submission === "cancel") {
        dialog.close();
        return;
      }
      if (submission === "mismatch") {
        input.setCustomValidity("Type the displayed target exactly.");
        input.reportValidity?.();
        return;
      }
      input.setCustomValidity("");
      const endpoint = adminEndpoint(action, state.tab, item.id);
      submitBtn.disabled = true;
      try {
        await request(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Idempotency-Key": operationKey(action, item.id) },
          body: action === "resume" ? undefined : JSON.stringify({
            confirmation: item.id,
            username: item.username || undefined,
            reason: reason.value || undefined,
          }),
        });
        state.pendingKeys.delete(actionKey(action, item.id));
        dialog.close();
        await load(true);
      } catch (error) {
        setLiveMessage(error?.message || "The administrator request failed.", true);
      } finally {
        submitBtn.disabled = false;
      }
    };
    input.oninput = () => input.setCustomValidity("");
  };

  documentRef.querySelectorAll("[data-admin-tab]").forEach((button) => {
    button.addEventListener("click", async () => {
      state.tab = button.dataset.adminTab;
      documentRef.querySelectorAll("[data-admin-tab]").forEach((tab) => {
        const isSelected = tab === button;
        tab.setAttribute("aria-selected", String(isSelected));
        tab.classList.toggle("active", isSelected);
      });
      updateViewHeader(documentRef, state.tab);
      await load(true);
    });
  });

  documentRef.getElementById("admin-refresh")?.addEventListener("click", () => load(true));
  documentRef.getElementById("admin-load-more")?.addEventListener("click", () => load(false));

  updateViewHeader(documentRef, state.tab);
  await load(true);
}

import {
  canonicalDestination,
  createBrowserAuth,
  getBrowserStorage,
  invalidateBrowserSession,
  readAuthConfig,
  resolveAuthenticatedContext,
  safeRelativePath,
} from "../../auth/static/auth-runtime.mjs";

function replace(location, destination) {
  if (location?.pathname !== destination) location?.replace?.(destination);
}

function targetForPath(pathname) {
  if (pathname.includes("build-preparation-fixture/progress")) return "progress";
  if (pathname.includes("build-preparation-fixture")) return "fixture";
  if (pathname.includes("code-generator-development")) return "code-generator";
  return null;
}

export async function bootDevelopmentShell({
  auth,
  fetchImpl = globalThis.fetch,
  location = globalThis.location,
  storage = getBrowserStorage(globalThis),
  config = readAuthConfig(globalThis.document),
  globalRef = globalThis,
  loadProtected = async (target, request) => {
    if (target === "fixture") {
      globalRef.OryxenAIProtectedFetch = request;
      await import("/static/build-preparation-fixture.js");
      return;
    }
    if (target === "progress") {
      globalRef.OryxenAIProtectedFetch = request;
      await import("/static/build-preparation-progress.js");
      return;
    }
    const module = await import("/static/code-generator-development.js");
    return module.bootCodeGeneratorDevelopment?.({ request });
  },
} = {}) {
  const paths = config.paths || {};
  const signIn = safeRelativePath(paths.signIn || "/sign-in", "/sign-in");
  const app = safeRelativePath(paths.app || "/app", "/app");
  const access = safeRelativePath(paths.access || "/access-not-approved", "/access-not-approved");
  const unavailable = safeRelativePath(
    paths.unavailable || "/account-unavailable",
    "/account-unavailable",
  );
  const onboarding = safeRelativePath(paths.onboarding || "/onboarding", "/onboarding");
  const target = targetForPath(location?.pathname || "");
  const onAuthFailure = async () => {
    await invalidateBrowserSession({ auth, storage });
    replace(location, signIn);
  };
  if (!target) return { kind: "unknown_development_page" };

  const canonical = canonicalDestination(config, location);
  if (canonical) {
    location?.replace?.(canonical);
    return { kind: "canonical_redirect" };
  }

  try {
    auth ||= createBrowserAuth(config, globalRef).auth;
  } catch (error) {
    replace(location, signIn);
    return { kind: "config_error", error };
  }
  const context = await resolveAuthenticatedContext({
    auth,
    fetchImpl,
    location,
    storage,
    onAuthFailure,
  });
  if (context.kind === "signed_out" || context.kind === "storage_error" || context.kind === "auth_failure") {
    replace(location, signIn);
    return context;
  }
  if (context.kind === "access_not_approved") {
    replace(location, access);
    return context;
  }
  if (context.kind === "account_unavailable") {
    replace(location, unavailable);
    return context;
  }
  if (context.kind !== "authenticated") {
    replace(location, signIn);
    return context;
  }
  if (context.me?.onboarding_required) {
    replace(location, onboarding);
    return { ...context, kind: "onboarding" };
  }
  if (context.me?.role !== "admin") {
    replace(location, app);
    return { ...context, kind: "not_admin" };
  }

  await loadProtected(target, context.authorizedFetch);
  return { ...context, kind: "development", target };
}

if (typeof document !== "undefined") {
  bootDevelopmentShell().catch(() => {
    globalThis.location?.replace?.("/sign-in");
  });
}

const generatorModuleUrl = new URL('./code-generator-development.js', import.meta.url);
const generatorVersion = new URL(import.meta.url).searchParams.get('js');
if (generatorVersion) generatorModuleUrl.searchParams.set('v', generatorVersion);
const generatorModule = import(generatorModuleUrl.href);

/**
 * Development-only request boundary. It deliberately has no auth imports,
 * session restoration, bearer handling, or redirect behavior. The server
 * mounts the detached API router when the configured pipeline mode is
 * `detached`; an attached shell can provide a different request boundary.
 */
export function createAnonymousRequest(fetchImpl = globalThis.fetch) {
  if (typeof fetchImpl !== 'function') throw new Error('A fetch implementation is required.');
  return async (url, init = {}) => {
    const headers = new Headers(init.headers || {});
    headers.delete('Authorization');
    return fetchImpl(url, {
      ...init,
      headers,
      credentials: 'same-origin',
      cache: 'no-store',
    });
  };
}

export async function bootDetachedCodeGenerator({ fetchImpl = globalThis.fetch } = {}) {
  const { bootCodeGeneratorDevelopment } = await generatorModule;
  return bootCodeGeneratorDevelopment({ request: createAnonymousRequest(fetchImpl) });
}

if (typeof document !== 'undefined') {
  bootDetachedCodeGenerator().catch((error) => {
    const status = document.querySelector('[data-start-error]');
    if (status) {
      status.hidden = false;
      status.textContent = `Detached generator could not start: ${error.message}`;
    }
  });
}

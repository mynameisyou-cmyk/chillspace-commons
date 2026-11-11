import {createMeaningHandler} from "./http.mjs";

// Cloudflare adds its Web Analytics beacon script to HTML at the edge unless
// the response says no-transform, so HTML pages say it. The existing
// Cache-Control is kept, and other types are left alone.
//
// no-transform also stops Cloudflare compressing the page. The sound page
// (sound.html) carries its audio inline: about 1.6 MB as a file, about
// 0.28 MB with brotli (0.55 MB with gzip). So it is left out, and answers
// exactly as ASSETS serves it. /sound.html and /sound/ redirect to /sound.
// The path is compared decoded, with repeated slashes folded and in lower
// case, so /%73ound or //sound is left out too.
const LEFT_AS_SERVED = new Set(["/sound", "/sound.html", "/sound/"]);

function comparablePath(pathname) {
  let path = pathname;
  try {
    path = decodeURIComponent(pathname);
  } catch {
    // A malformed escape is compared as spelled.
  }
  return path.replace(/\/+/g, "/").toLowerCase();
}

function withoutEdgeInjection(response) {
  const type = response.headers.get("Content-Type") || "";
  if (!type.toLowerCase().startsWith("text/html")) return response;
  const cacheControl = response.headers.get("Cache-Control");
  if (cacheControl && /(^|,)\s*no-transform\s*(,|$)/i.test(cacheControl)) return response;
  const headers = new Headers(response.headers);
  headers.set("Cache-Control", cacheControl ? `${cacheControl}, no-transform` : "no-transform");
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

function createPagesWorker(dataset) {
  const handleMeaning = createMeaningHandler(dataset);

  return {
    async fetch(request, env) {
      const pathname = new URL(request.url).pathname;
      if (pathname === "/api/meaning/echo" || pathname === "/api/meaning/echo/") {
        return handleMeaning(request);
      }
      const response = await env.ASSETS.fetch(request);
      if (LEFT_AS_SERVED.has(comparablePath(pathname))) return response;
      return withoutEdgeInjection(response);
    },
  };
}

export {createPagesWorker};

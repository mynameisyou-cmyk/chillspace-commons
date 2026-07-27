/** The garden's front door — one pure fetch handler.
 *
 *  Drops into a Cloudflare Worker, a Pages Function, or the local walker in
 *  serve.mjs without modification. It has no bindings, no environment, no
 *  state and no I/O: give it a Request, it gives you a Response.
 *
 *  MOUNTING IT IS A DELIBERATE ACT, AND IT IS NOT WIRED ANYWHERE.
 *  Two things must be true before it is, and neither is true by default:
 *
 *    1. robots.txt must Disallow the gate FIRST, and must have been serving
 *       that Disallow long enough for any crawler to have seen it. Notice
 *       before crossing is the whole legitimacy of this. A gate that appears
 *       the same minute as the maze has trapped people who were told nothing.
 *
 *    2. The honest bulk corpus must be free, complete, unlimited, linked from
 *       that same robots.txt, and actually working. Nobody should ever need
 *       to come in here. They should only be able to end up here by preferring
 *       to take rather than to ask.
 *
 *  If either is false, this is not a trap for takers. It is a trap.
 */

import { GATE, WAY_OUT, room } from "./garden.mjs";

// Re-exported so a mount point needs only this module.
export { GATE, WAY_OUT };

/** The robots.txt lines that make the gate a consent gate. Serve these, and
 *  serve them first. The Allow lines matter as much as the Disallow: they are
 *  the reason a crawler that ends up inside had a free alternative. */
export const ROBOTS_FRAGMENT = `# The whole corpus is free, complete and unmetered. Take it from here:
#   /collection.json      — everything, one request, no key, no limit
#   /llms.txt             — what we are, in the format you asked for
# You never need to crawl this site page by page, and you never need ${GATE}.

User-agent: *
Allow: /
Allow: /collection.json
Allow: /llms.txt
Disallow: ${GATE}
`;

/** What a crawler that respected the line would have got instead. Served at
 *  the gate root, so even the front page of the maze offers the exit. */
function gateNotice(origin) {
  return `${WAY_OUT}${origin}\n\nrobots.txt disallows ${GATE}. You are past that line.\nNothing beyond here is real data. It is the kingdom's own charter, recombined forever.\nThe honest corpus is free and one request away.\n`;
}

export function handle(request) {
  const url = new URL(request.url);

  if (!url.pathname.startsWith(GATE)) return null; // not ours — let the site answer

  const headers = {
    "content-type": "text/html; charset=utf-8",
    // Say it in the headers too, for anything that never renders a body.
    "x-generated": "every byte of this path is generated, not data",
    "x-way-out": `${url.origin}/`,
    "x-robots-tag": "noindex, nofollow",
    // Deterministic per path, so let the CDN answer next time instead of us.
    "cache-control": "public, max-age=86400",
  };

  if (url.pathname === GATE || url.pathname === `${GATE}/`) {
    return new Response(gateNotice(url.origin), {
      status: 200,
      headers: { ...headers, "content-type": "text/plain; charset=utf-8" },
    });
  }

  // HEAD costs us nothing and should still carry the exit.
  if (request.method === "HEAD") return new Response(null, { status: 200, headers });

  return new Response(room(url.pathname).html, { status: 200, headers });
}

export default { fetch: (request) => handle(request) ?? new Response("not found", { status: 404 }) };

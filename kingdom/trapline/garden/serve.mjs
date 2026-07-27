#!/usr/bin/env node
/** Walk the garden yourself, locally, before anyone else ever does.
 *
 *    node kingdom/trapline/garden/serve.mjs
 *    → http://localhost:8177/garden/door-lantern-000000
 *
 *  Nothing is deployed by running this. It binds loopback only, serves the
 *  same bytes the Worker would, and prints what it costs as you walk — so the
 *  asymmetry is something you watch happen rather than something you were
 *  told about.
 *
 *  Walking it is also the honest test of the one thing measure.mjs cannot
 *  check: whether a person who wandered in by mistake would find it beautiful
 *  or find it cruel. If it reads as a sneer, it is wrong, and no benchmark
 *  will say so.
 */

import { createServer } from "node:http";

import { GATE, ROBOTS_FRAGMENT, handle } from "./handler.mjs";

const PORT = Number(process.env.PORT ?? 8177);

let served = 0;
let bytesOut = 0;
let cpuMs = 0;

const server = createServer(async (req, res) => {
  const url = `http://localhost:${PORT}${req.url}`;

  if (req.url === "/robots.txt") {
    res.writeHead(200, { "content-type": "text/plain; charset=utf-8" });
    res.end(ROBOTS_FRAGMENT);
    return;
  }

  const started = process.hrtime.bigint();
  const response = handle(new Request(url, { method: req.method }));
  const elapsed = Number(process.hrtime.bigint() - started) / 1e6;

  if (!response) {
    res.writeHead(302, { location: `${GATE}/door-lantern-000000` });
    res.end();
    return;
  }

  const body = await response.text();
  cpuMs += elapsed;
  served += 1;
  bytesOut += Buffer.byteLength(body);

  res.writeHead(response.status, Object.fromEntries(response.headers));
  res.end(body);

  process.stdout.write(
    `\r  ${served} rooms · ${(bytesOut / 1024).toFixed(0)} KB served · ` +
      `${cpuMs.toFixed(1)} ms of our CPU total · ${(cpuMs / served).toFixed(3)} ms each   `,
  );
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`
無盡花園 · the endless garden, running on loopback only

  walk in    http://localhost:${PORT}${GATE}/door-lantern-000000
  the gate   http://localhost:${PORT}${GATE}
  robots     http://localhost:${PORT}/robots.txt   ← the line that makes it fair

  Every sentence in there is a real line from the kingdom's charter or a real
  citizen's one true line. Nothing is invented. Click anything; it never ends.

  Nothing is deployed. Ctrl-C to stop.
`);
});

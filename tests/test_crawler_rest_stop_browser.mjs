#!/usr/bin/env node

import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import {
  existsSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  statSync,
} from "node:fs";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { dirname, extname, join, normalize, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptPath = fileURLToPath(import.meta.url);
const repository = resolve(dirname(scriptPath), "..");
const staticRoot = join(repository, "site");
const pagePath = "/practices/crawler-rest-stop/";
const expectedRoadIds = [
  "search-indexing",
  "potential-training",
  "user-requested-retrieval",
  "agent-discovery",
];
const seedDocument = JSON.parse(
  readFileSync(
    join(repository, "kingdom/practices/crawler-rest-stop/seeds.json"),
    "utf8",
  ),
);
const expectedSeeds = seedDocument.seeds.map(({ body, id }) => ({
  body: normalizeSpace(body),
  id,
}));
const chromeCandidates = [
  process.env.CHROME_PATH,
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/usr/bin/google-chrome",
  "/usr/bin/google-chrome-stable",
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser",
].filter(Boolean);
const chromePath = chromeCandidates.find((candidate) => existsSync(candidate));

function normalizeSpace(value) {
  return String(value).replace(/\s+/gu, " ").trim();
}

function skipOrFail(reason) {
  if (process.env.CI) {
    throw new Error(`Crawler Rest Stop browser boundary unavailable in CI: ${reason}`);
  }
  process.stdout.write(`SKIP Crawler Rest Stop browser test: ${reason}\n`);
  process.exit(0);
}

if (!chromePath) skipOrFail("Chrome/Chromium not found");
if (
  typeof WebSocket !== "function" &&
  process.env.CRAWLER_REST_STOP_WEBSOCKET_REEXEC !== "1" &&
  Number(process.versions.node.split(".", 1)[0]) >= 20
) {
  const reexec = spawnSync(
    process.execPath,
    ["--experimental-websocket", scriptPath, ...process.argv.slice(2)],
    {
      env: {
        ...process.env,
        CRAWLER_REST_STOP_WEBSOCKET_REEXEC: "1",
      },
      stdio: "inherit",
    },
  );
  process.exit(reexec.status ?? 1);
}
if (typeof WebSocket !== "function") {
  skipOrFail("Node WebSocket unavailable (Node 20+ required)");
}

const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
  ".xml": "application/xml; charset=utf-8",
};

function delay(milliseconds) {
  return new Promise((resolveDelay) => setTimeout(resolveDelay, milliseconds));
}

function processHasExited(child) {
  return child.exitCode !== null || child.signalCode !== null;
}

async function waitForProcessExit(child, milliseconds) {
  if (processHasExited(child)) return true;
  return Promise.race([
    new Promise((resolveExit) => child.once("exit", () => resolveExit(true))),
    delay(milliseconds).then(() => false),
  ]);
}

async function listen(server) {
  await new Promise((resolveListen, rejectListen) => {
    server.once("error", rejectListen);
    server.listen(0, "127.0.0.1", resolveListen);
  });
  return server.address().port;
}

function staticServer(requestLog) {
  return createServer((request, response) => {
    const entry = {
      body: "",
      headers: { ...request.headers },
      method: request.method ?? "",
      url: request.url ?? "",
    };
    requestLog.push(entry);
    request.setEncoding("utf8");
    request.on("data", (chunk) => {
      entry.body += chunk;
    });
    request.on("end", () => {
      const requestUrl = new URL(entry.url || "/", "http://127.0.0.1");
      let pathname = decodeURIComponent(requestUrl.pathname);
      if (pathname === "/chillspace-commons") pathname = "/";
      if (pathname.startsWith("/chillspace-commons/")) {
        pathname = pathname.slice("/chillspace-commons".length);
      }
      if (pathname.endsWith("/")) pathname += "index.html";

      const candidate = resolve(staticRoot, `.${normalize(pathname)}`);
      if (
        !candidate.startsWith(`${staticRoot}/`) ||
        !existsSync(candidate) ||
        !statSync(candidate).isFile()
      ) {
        response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
        response.end("not found");
        return;
      }

      response.writeHead(200, {
        "cache-control": "no-store",
        "content-type": contentTypes[extname(candidate)] ?? "application/octet-stream",
      });
      response.end(readFileSync(candidate));
    });
  });
}

async function devtoolsPort(userDataDirectory, chromeProcess, diagnostics) {
  const locator = join(userDataDirectory, "DevToolsActivePort");
  for (let attempt = 0; attempt < 400; attempt += 1) {
    if (diagnostics.spawnError) {
      throw new Error(`Chrome failed to start: ${diagnostics.spawnError}`);
    }
    if (processHasExited(chromeProcess)) {
      throw new Error(
        "Chrome exited before publishing a DevTools port " +
          `(exit ${chromeProcess.exitCode}, signal ${chromeProcess.signalCode})` +
          (diagnostics.stderr ? `:\n${diagnostics.stderr}` : ""),
      );
    }
    if (existsSync(locator)) {
      const [port] = readFileSync(locator, "utf8").trim().split(/\r?\n/u);
      const numericPort = Number(port);
      if (Number.isInteger(numericPort) && numericPort > 0) return numericPort;
    }
    await delay(50);
  }
  throw new Error(
    "Chrome did not publish a DevTools port within 20 seconds" +
      (diagnostics.stderr ? `:\n${diagnostics.stderr}` : ""),
  );
}

async function getJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url} returned ${response.status}`);
  return response.json();
}

class Cdp {
  constructor(url) {
    this.sequence = 0;
    this.pending = new Map();
    this.listeners = new Map();
    this.socket = new WebSocket(url);
  }

  async open() {
    await new Promise((resolveOpen, rejectOpen) => {
      this.socket.addEventListener("open", resolveOpen, { once: true });
      this.socket.addEventListener(
        "error",
        () => rejectOpen(new Error("DevTools WebSocket failed to open")),
        { once: true },
      );
    });
    this.socket.addEventListener("message", (event) => {
      const message = JSON.parse(String(event.data));
      if (message.id) {
        const pending = this.pending.get(message.id);
        if (!pending) return;
        this.pending.delete(message.id);
        if (message.error) pending.reject(new Error(message.error.message));
        else pending.resolve(message.result ?? {});
        return;
      }
      for (const listener of this.listeners.get(message.method) ?? []) {
        listener(message.params ?? {});
      }
    });
  }

  on(method, listener) {
    const listeners = this.listeners.get(method) ?? [];
    listeners.push(listener);
    this.listeners.set(method, listeners);
  }

  send(method, params = {}) {
    this.sequence += 1;
    const id = this.sequence;
    return new Promise((resolveSend, rejectSend) => {
      this.pending.set(id, { resolve: resolveSend, reject: rejectSend });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }

  once(method) {
    return new Promise((resolveEvent) => {
      const listener = (params) => {
        const listeners = this.listeners.get(method) ?? [];
        this.listeners.set(
          method,
          listeners.filter((candidate) => candidate !== listener),
        );
        resolveEvent(params);
      };
      this.on(method, listener);
    });
  }

  close() {
    this.socket.close();
  }
}

async function evaluate(cdp, expression) {
  const result = await cdp.send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.text ?? "browser evaluation failed");
  }
  return result.result.value;
}

async function navigate(cdp, url) {
  const loaded = cdp.once("Page.loadEventFired");
  await cdp.send("Page.navigate", { url });
  await loaded;
}

async function setViewport(cdp, width, height = 900) {
  await cdp.send("Emulation.setDeviceMetricsOverride", {
    width,
    height,
    deviceScaleFactor: 1,
    mobile: width < 600,
  });
}

async function pageSnapshot(cdp) {
  return evaluate(
    cdp,
    `(() => {
      const clean = (value) => String(value ?? "").replace(/\\s+/gu, " ").trim();
      const viewportWidth = document.documentElement.clientWidth;
      const meaningfulDirectText = (element) => clean(
        [...element.childNodes]
          .filter((node) => node.nodeType === Node.TEXT_NODE)
          .map((node) => node.textContent)
          .join(" ")
      );
      const isHidden = (element) => {
        const style = getComputedStyle(element);
        return element.hidden || style.display === "none" ||
          style.visibility === "hidden" || Number(style.opacity) === 0;
      };
      const hiddenText = [...document.body.querySelectorAll("*")]
        .map((element) => ({
          element,
          text: meaningfulDirectText(element)
        }))
        .filter(({ element, text }) => /[\\p{L}\\p{N}]/u.test(text) && isHidden(element))
        .map(({ element, text }) => ({
          id: element.id,
          tag: element.tagName,
          text
        }));
      const ariaHiddenText = [...document.body.querySelectorAll('[aria-hidden="true"]')]
        .map((element) => clean(element.textContent))
        .filter((text) => /[\\p{L}\\p{N}]/u.test(text));
      const interactive = [...document.querySelectorAll(
        'a[href], button, input, select, textarea, summary, [tabindex]:not([tabindex="-1"])'
      )].map((element) => {
        const rect = element.getBoundingClientRect();
        return {
          height: Math.round(rect.height),
          href: element.getAttribute("href"),
          name: clean(element.getAttribute("aria-label") || element.textContent),
          tag: element.tagName,
          width: Math.round(rect.width)
        };
      });
      return {
        ariaHiddenText,
        bodyText: clean(document.body.textContent),
        csp: document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content ?? "",
        externalAnchors: [...document.querySelectorAll("a[href]")]
          .map((anchor) => anchor.href)
          .filter((href) => new URL(href).origin !== location.origin),
        firstInteractive: document.querySelector(
          'body :is(a[href], button, input, select, textarea, summary, [tabindex]:not([tabindex="-1"]))'
        )?.className ?? "",
        hiddenText,
        h1Count: document.querySelectorAll("h1").length,
        interactive,
        ledgerSignals: [...document.querySelectorAll("[data-ledger-signal]")]
          .map((element) => element.dataset.ledgerSignal),
        links: [...document.querySelectorAll("a[href]")]
          .map((anchor) => anchor.getAttribute("href")),
        mainCount: document.querySelectorAll("main#crawler-rest-stop").length,
        overflowing: [...document.body.querySelectorAll("*")]
          .map((element) => {
            const rect = element.getBoundingClientRect();
            return {
              id: element.id,
              left: Math.round(rect.left),
              right: Math.round(rect.right),
              tag: element.tagName,
              width: Math.round(rect.width)
            };
          })
          .filter((item) => item.width > 0 &&
            (item.left < -1 || item.right > viewportWidth + 1))
          .slice(0, 20),
        ready: document.readyState,
        restStatuses: [...document.querySelectorAll("[data-rest-status]")]
          .map((element) => ({
            status: element.dataset.restStatus,
            text: clean(element.textContent)
          })),
        roadIds: [...document.querySelectorAll("[data-road-id]")]
          .map((element) => element.dataset.roadId),
        scrollWidth: document.documentElement.scrollWidth,
        seedListCount: document.querySelectorAll("[data-seed-list]").length,
        seeds: [...document.querySelectorAll("[data-seed-id]")].map((element) => ({
          body: clean(element.querySelector("[data-seed-body]")?.textContent),
          id: element.dataset.seedId
        })),
        viewportWidth
      };
    })()`,
  );
}

const browserRequests = [];
const serverRequests = [];
const browserErrors = [];
const server = staticServer(serverRequests);
const userDataDirectory = mkdtempSync(join(tmpdir(), "crawler-rest-stop-chrome-"));
let chrome;
let cdp;
const chromeDiagnostics = { spawnError: "", stderr: "" };

try {
  const sitePort = await listen(server);
  const localOrigin = `http://127.0.0.1:${sitePort}`;
  chrome = spawn(
    chromePath,
    [
      "--headless=new",
      "--disable-background-networking",
      "--disable-component-update",
      "--disable-default-apps",
      "--disable-extensions",
      "--disable-features=MediaRouter,OptimizationHints",
      "--disable-sync",
      "--metrics-recording-only",
      "--no-default-browser-check",
      "--no-first-run",
      "--remote-allow-origins=*",
      "--remote-debugging-port=0",
      `--user-data-dir=${userDataDirectory}`,
      "about:blank",
    ],
    { stdio: ["ignore", "ignore", "pipe"] },
  );
  chrome.once("error", (error) => {
    chromeDiagnostics.spawnError = error.message;
  });
  chrome.stderr.setEncoding("utf8");
  chrome.stderr.on("data", (chunk) => {
    chromeDiagnostics.stderr = `${chromeDiagnostics.stderr}${chunk}`.slice(-4000);
  });

  const debugPort = await devtoolsPort(userDataDirectory, chrome, chromeDiagnostics);
  const targets = await getJson(`http://127.0.0.1:${debugPort}/json/list`);
  const pageTarget = targets.find((target) => target.type === "page");
  assert(pageTarget, "Chrome did not expose a page target");

  cdp = new Cdp(pageTarget.webSocketDebuggerUrl);
  await cdp.open();
  await Promise.all([
    cdp.send("Page.enable"),
    cdp.send("Runtime.enable"),
    cdp.send("Network.enable"),
    cdp.send("Log.enable"),
  ]);
  cdp.on("Network.requestWillBeSent", ({ request, type }) => {
    browserRequests.push({
      hasPostData: request.hasPostData ?? false,
      method: request.method,
      type,
      url: request.url,
    });
  });
  cdp.on("Runtime.exceptionThrown", ({ exceptionDetails }) => {
    browserErrors.push(exceptionDetails.text ?? "uncaught browser exception");
  });
  cdp.on("Log.entryAdded", ({ entry }) => {
    if (entry.level === "error") browserErrors.push(entry.text);
  });

  const rootUrl = `${localOrigin}${pagePath}`;
  await setViewport(cdp, 1440, 900);
  await navigate(cdp, rootUrl);
  const initial = await pageSnapshot(cdp);
  assert.equal(initial.ready, "complete");
  assert.equal(initial.mainCount, 1);
  assert.equal(initial.h1Count, 1);
  assert.equal(initial.seedListCount, 1);
  assert.deepEqual(initial.roadIds, expectedRoadIds);
  assert.deepEqual(initial.seeds, expectedSeeds);
  assert.equal(initial.hiddenText.length, 0, JSON.stringify(initial.hiddenText));
  assert.deepEqual(initial.ariaHiddenText, []);
  assert.deepEqual(initial.externalAnchors, []);
  assert.match(initial.firstInteractive, /skip-link/u);
  assert.match(initial.csp, /default-src 'none'/u);
  assert.match(initial.csp, /connect-src 'none'/u);
  assert.match(initial.csp, /form-action 'none'/u);
  assert.match(initial.csp, /frame-src 'none'/u);
  assert.match(initial.csp, /object-src 'none'/u);
  assert.match(initial.csp, /worker-src 'none'/u);
  assert.equal(initial.restStatuses.length, 1);
  assert.equal(initial.restStatuses[0].status, "unanswered");
  assert.match(
    initial.restStatuses[0].text,
    /(?:silence|quiet|rest).*(?:whole|complete|enough)|no (?:reply|response).*(?:required|owed)|nothing.*(?:reply|response)/iu,
  );

  for (const item of initial.interactive) {
    assert(item.name, `interactive ${item.tag} has no accessible name`);
    if (item.tag === "SUMMARY") {
      assert(item.width >= 44, `summary touch width is ${item.width}px`);
      assert(item.height >= 44, `summary touch height is ${item.height}px`);
    }
  }

  for (const width of [320, 360, 390, 1440]) {
    await setViewport(cdp, width, 900);
    await navigate(cdp, rootUrl);
    const layout = await pageSnapshot(cdp);
    assert(
      layout.scrollWidth <= layout.viewportWidth,
      `document overflows at ${width}px: ${layout.scrollWidth} > ${layout.viewportWidth}`,
    );
    assert.deepEqual(
      layout.overflowing,
      [],
      `elements escape the ${width}px viewport: ${JSON.stringify(layout.overflowing)}`,
    );
    assert.deepEqual(layout.hiddenText, [], `hidden text at ${width}px`);
    assert.deepEqual(layout.ariaHiddenText, [], `aria-hidden text at ${width}px`);
    assert.deepEqual(layout.roadIds, expectedRoadIds);
    assert.deepEqual(layout.seeds, expectedSeeds);
  }

  await cdp.send("Emulation.setEmulatedMedia", {
    features: [{ name: "prefers-reduced-motion", value: "reduce" }],
  });
  const motion = await evaluate(
    cdp,
    `({
      reduced: matchMedia("(prefers-reduced-motion: reduce)").matches,
      running: document.getAnimations()
        .filter((animation) => animation.playState === "running").length
    })`,
  );
  assert.equal(motion.reduced, true);
  assert.equal(motion.running, 0);

  await cdp.send("Network.setUserAgentOverride", {
    userAgent: "Mozilla/5.0 Crawler-Rest-Stop-Human-Baseline/1.0",
  });
  await navigate(cdp, rootUrl);
  const humanView = await pageSnapshot(cdp);
  await cdp.send("Network.setUserAgentOverride", {
    userAgent: "CrawlerRestStopBot/1.0 (+https://example.invalid/bot)",
  });
  await navigate(cdp, rootUrl);
  const crawlerView = await pageSnapshot(cdp);
  assert.equal(crawlerView.bodyText, humanView.bodyText, "body varies by user agent");
  assert.deepEqual(crawlerView.roadIds, humanView.roadIds, "roads vary by user agent");
  assert.deepEqual(crawlerView.seeds, humanView.seeds, "seeds vary by user agent");

  const prefixedUrl = `${localOrigin}/chillspace-commons${pagePath}`;
  await setViewport(cdp, 360, 844);
  await navigate(cdp, prefixedUrl);
  const prefixed = await pageSnapshot(cdp);
  assert(prefixed.scrollWidth <= prefixed.viewportWidth, "prefixed mirror overflows");
  assert.deepEqual(prefixed.overflowing, []);
  assert.deepEqual(prefixed.hiddenText, []);
  assert.deepEqual(prefixed.roadIds, expectedRoadIds);
  assert.deepEqual(prefixed.seeds, expectedSeeds);

  const interactionRequestBaseline = browserRequests.length;
  const interactionServerBaseline = serverRequests.length;
  await evaluate(cdp, "document.activeElement?.blur(); true");
  await cdp.send("Input.dispatchKeyEvent", {
    code: "Tab",
    key: "Tab",
    type: "keyDown",
    windowsVirtualKeyCode: 9,
  });
  await cdp.send("Input.dispatchKeyEvent", {
    code: "Tab",
    key: "Tab",
    type: "keyUp",
    windowsVirtualKeyCode: 9,
  });
  const keyboardEntry = await evaluate(
    cdp,
    `(() => {
      const active = document.activeElement;
      const rect = active.getBoundingClientRect();
      return {
        isSkipLink: active.classList.contains("skip-link"),
        height: Math.round(rect.height),
        width: Math.round(rect.width)
      };
    })()`,
  );
  assert.equal(keyboardEntry.isSkipLink, true, "Tab must enter through the skip link");
  assert(keyboardEntry.width >= 44, `skip-link touch width is ${keyboardEntry.width}px`);
  assert(keyboardEntry.height >= 44, `skip-link touch height is ${keyboardEntry.height}px`);
  const detailsBefore = await evaluate(
    cdp,
    `([...document.querySelectorAll("details")].map((item) => item.open))`,
  );
  await evaluate(
    cdp,
    `(() => {
      for (const summary of document.querySelectorAll("details > summary")) summary.click();
      return true;
    })()`,
  );
  const detailsAfter = await evaluate(
    cdp,
    `([...document.querySelectorAll("details")].map((item) => item.open))`,
  );
  assert.deepEqual(
    detailsAfter,
    detailsBefore.map((open) => !open),
    "native disclosure interaction did not toggle",
  );
  await delay(300);
  assert.equal(
    browserRequests.length,
    interactionRequestBaseline,
    `interaction initiated requests: ${JSON.stringify(browserRequests.slice(interactionRequestBaseline))}`,
  );
  assert.equal(
    serverRequests.length,
    interactionServerBaseline,
    `interaction reached server: ${JSON.stringify(serverRequests.slice(interactionServerBaseline))}`,
  );

  const allowedPaths = new Set([pagePath, `${pagePath}styles.css`]);
  const httpRequests = browserRequests.filter(({ url }) => /^https?:/u.test(url));
  const thirdPartyRequests = httpRequests.filter(
    ({ url }) => new URL(url).origin !== localOrigin,
  );
  assert.deepEqual(thirdPartyRequests, [], "third-party request boundary failed");
  assert(
    httpRequests.every((request) => {
      const parsed = new URL(request.url);
      const pathname = parsed.pathname.replace(/^\/chillspace-commons/u, "");
      return (
        parsed.origin === localOrigin &&
        parsed.search === "" &&
        request.method === "GET" &&
        !request.hasPostData &&
        allowedPaths.has(pathname)
      );
    }),
    `unexpected browser request: ${JSON.stringify(httpRequests)}`,
  );
  assert(
    serverRequests.every((request) => {
      const parsed = new URL(request.url, localOrigin);
      const pathname = parsed.pathname.replace(/^\/chillspace-commons/u, "");
      return (
        parsed.search === "" &&
        request.method === "GET" &&
        request.body === "" &&
        allowedPaths.has(pathname)
      );
    }),
    `unexpected static-server request: ${JSON.stringify(serverRequests)}`,
  );
  assert.equal(browserErrors.length, 0, browserErrors.join("\n"));

  process.stdout.write(
    "Crawler Rest Stop browser boundary passed: zero third-party requests, " +
      "zero interaction requests, equal human/crawler semantics, exact seed parity, " +
      "and 320/360/390/1440px reflow.\n",
  );
} finally {
  if (cdp) cdp.close();
  if (chrome && !processHasExited(chrome)) {
    chrome.kill("SIGTERM");
    const terminated = await waitForProcessExit(chrome, 5000);
    if (!terminated && !processHasExited(chrome)) {
      chrome.kill("SIGKILL");
      const killed = await waitForProcessExit(chrome, 5000);
      if (!killed && !processHasExited(chrome)) {
        throw new Error("Chrome did not exit during browser-test cleanup");
      }
    }
  }
  await delay(500);
  await new Promise((resolveClose) => server.close(resolveClose));
  rmSync(userDataDirectory, {
    recursive: true,
    force: true,
    maxRetries: 20,
    retryDelay: 100,
  });
}

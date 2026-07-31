#!/usr/bin/env node

import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import {
  existsSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { dirname, extname, join, normalize, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptPath = fileURLToPath(import.meta.url);
const repository = resolve(dirname(scriptPath), "..");
const staticRoot = join(repository, "site");
const chromeCandidates = [
  process.env.CHROME_PATH,
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/usr/bin/google-chrome",
  "/usr/bin/google-chrome-stable",
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser",
].filter(Boolean);
const chromePath = chromeCandidates.find((candidate) => existsSync(candidate));

function skipOrFail(reason) {
  if (process.env.CI) {
    throw new Error(`Calm Studio browser boundary unavailable in CI: ${reason}`);
  }
  process.stdout.write(`SKIP Calm Studio browser test: ${reason}\n`);
  process.exit(0);
}

if (!chromePath) skipOrFail("Chrome/Chromium not found");
if (
  typeof WebSocket !== "function" &&
  process.env.CALM_WEBSOCKET_REEXEC !== "1" &&
  Number(process.versions.node.split(".", 1)[0]) >= 20
) {
  const reexec = spawnSync(
    process.execPath,
    ["--experimental-websocket", scriptPath, ...process.argv.slice(2)],
    {
      env: { ...process.env, CALM_WEBSOCKET_REEXEC: "1" },
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
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
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
      if (!candidate.startsWith(`${staticRoot}/`) || !existsSync(candidate)) {
        response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
        response.end("not found");
        return;
      }
      if (!statSync(candidate).isFile()) {
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
      const [port] = readFileSync(locator, "utf-8").trim().split(/\r?\n/u);
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
        if (message.error) {
          pending.reject(new Error(message.error.message));
        } else {
          pending.resolve(message.result ?? {});
        }
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
  return cdp.send("Emulation.setDeviceMetricsOverride", {
    width,
    height,
    deviceScaleFactor: 1,
    mobile: width < 600,
  });
}

async function layoutAt(cdp, width, height = 900) {
  await setViewport(cdp, width, height);
  return evaluate(
    cdp,
    `({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
      bodyScrollWidth: document.body.scrollWidth,
      composeEnabled: !document.querySelector("#compose").disabled,
      questionVisible: document.querySelector("#studio-question").getBoundingClientRect().width > 0,
      overflowing: [...document.querySelectorAll("body *")]
        .map((element) => {
          const rect = element.getBoundingClientRect();
          return {
            tag: element.tagName,
            id: element.id,
            className: typeof element.className === "string" ? element.className : "",
            left: Math.round(rect.left),
            right: Math.round(rect.right),
            width: Math.round(rect.width)
          };
        })
        .filter((item) => item.width > 0 && (item.left < -1 || item.right > document.documentElement.clientWidth + 1))
        .slice(0, 20)
    })`,
  );
}

const serverRequests = [];
const server = staticServer(serverRequests);
const userDataDirectory = mkdtempSync(join(tmpdir(), "calm-studio-chrome-"));
let chrome;
let cdp;
const chromeDiagnostics = { spawnError: "", stderr: "" };

try {
  const sitePort = await listen(server);
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

  const debugPort = await devtoolsPort(
    userDataDirectory,
    chrome,
    chromeDiagnostics,
  );
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

  const requests = [];
  const browserErrors = [];
  const consoleMessages = [];
  cdp.on("Network.requestWillBeSent", ({ request, type }) => {
    requests.push({
      headers: { ...request.headers },
      hasPostData: request.hasPostData ?? false,
      method: request.method,
      postData: request.postData ?? null,
      type,
      url: request.url,
    });
  });
  cdp.on("Runtime.exceptionThrown", ({ exceptionDetails }) => {
    browserErrors.push(exceptionDetails.text ?? "uncaught browser exception");
  });
  cdp.on("Log.entryAdded", ({ entry }) => {
    consoleMessages.push({
      level: entry.level,
      source: entry.source,
      text: entry.text,
      url: entry.url,
    });
    if (entry.level === "error") browserErrors.push(entry.text);
  });
  cdp.on("Runtime.consoleAPICalled", ({ args, type }) => {
    consoleMessages.push({
      args: args.map((argument) => ({
        description: argument.description,
        type: argument.type,
        value: argument.value,
      })),
      type,
    });
  });

  const localOrigin = `http://127.0.0.1:${sitePort}`;
  const rootUrl = `${localOrigin}/practices/calm-studio/`;
  await setViewport(cdp, 1440, 900);
  await navigate(cdp, rootUrl);

  const initial = await evaluate(
    cdp,
    `({
      ready: document.readyState,
      state: document.body.dataset.stillpointState,
      composeEnabled: !document.querySelector("#compose").disabled,
      presetEnabled: !document.querySelector("[data-preset]").disabled,
      resultHidden: document.querySelector("#result").hidden,
      csp: document.querySelector('meta[http-equiv="Content-Security-Policy"]').content
    })`,
  );
  assert.equal(initial.ready, "complete");
  assert.equal(initial.state, "quiet");
  assert.equal(initial.composeEnabled, true);
  assert.equal(initial.presetEnabled, true);
  assert.equal(initial.resultHidden, true);
  assert.match(initial.csp, /connect-src 'none'/u);

  for (const width of [320, 390, 1440]) {
    await setViewport(cdp, width);
    await navigate(cdp, rootUrl);
    const layout = await layoutAt(cdp, width);
    assert.equal(layout.composeEnabled, true, `compose disabled at ${width}px`);
    assert.equal(layout.questionVisible, true, `question hidden at ${width}px`);
    assert(
      layout.scrollWidth <= layout.clientWidth,
      `document overflows at ${width}px: ${layout.scrollWidth} > ${layout.clientWidth}`,
    );
    assert(
      layout.bodyScrollWidth <= layout.clientWidth,
      `body overflows at ${width}px: ${layout.bodyScrollWidth} > ${layout.clientWidth}`,
    );
    assert.deepEqual(
      layout.overflowing,
      [],
      `elements escape the ${width}px viewport: ${JSON.stringify(layout.overflowing)}`,
    );
  }

  await cdp.send("Emulation.setEmulatedMedia", {
    features: [{ name: "prefers-reduced-motion", value: "reduce" }],
  });
  const motion = await evaluate(
    cdp,
    `({
      reduced: matchMedia("(prefers-reduced-motion: reduce)").matches,
      running: document.getAnimations().filter((animation) => animation.playState === "running").length
    })`,
  );
  assert.equal(motion.reduced, true);
  assert.equal(motion.running, 0);

  const privateSentinel = "CALM_SENTINEL_question_must_never_leave_7f4c2d";
  const requestBaseline = requests.length;
  const serverRequestBaseline = serverRequests.length;
  const rehearsal = await evaluate(
    cdp,
    `(() => {
      const setValue = (selector, value) => {
        const control = document.querySelector(selector);
        control.value = value;
        control.dispatchEvent(new Event("change", { bubbles: true }));
      };
      const question = document.querySelector("#studio-question");
      question.value = "";
      question.dispatchEvent(new Event("input", { bubbles: true }));
      const emptyQuestionDisablesComposition =
        document.querySelector("#compose").disabled;
      question.value = ${JSON.stringify(privateSentinel)};
      question.dispatchEvent(new Event("input", { bubbles: true }));
      setValue("#rights-boundary", "respected");
      setValue('[data-virtue="honesty"]', "ready_to_author");
      const route = document.querySelector('input[value="dissent-first"]');
      route.checked = true;
      route.dispatchEvent(new Event("change", { bubbles: true }));
      document.querySelector("#compose").click();
      const receipt = JSON.parse(document.querySelector("#receipt-output").textContent);
      return {
        activeElement: document.activeElement.id,
        dissentFixed:
          document.querySelector('input[value="dissent"]').checked &&
          document.querySelector('input[value="dissent"]').disabled,
        evidenceFixed:
          document.querySelector('input[value="evidence"]').checked &&
          document.querySelector('input[value="evidence"]').disabled,
        emptyQuestionDisablesComposition,
        firstVoice: document.querySelector("#voice-list strong").textContent,
        focusedQuestion: document.querySelector("#question-focus").textContent,
        state: document.body.dataset.stillpointState,
        resultHidden: document.querySelector("#result").hidden,
        voiceCount: document.querySelectorAll("#voice-list li").length,
        questionIncluded: receipt.question.included,
        questionPresentInDocument: receipt.question.nonempty_draft_present,
        questionPersisted: receipt.question.persisted_by_application,
        questionTransmitted: receipt.question.transmitted_by_application,
        questionTextLeaked: document
          .querySelector("#receipt-output")
          .textContent
          .includes(document.querySelector("#studio-question").value),
        modelCalls: receipt.council.model_calls,
        grantsAuthority: receipt.authority.grants_authority,
        persists: receipt.privacy.persisted_by_application,
        manifestEmitted: receipt.virtue_rehearsal.canonical_manifest_emitted,
        evidenceNamed: receipt.virtue_rehearsal.evidence_named,
        disposition: document.querySelector("#karma-disposition").textContent
      };
    })()`,
  );
  await delay(300);
  assert.equal(
    requests.length,
    requestBaseline,
    `interaction initiated a page request: ${JSON.stringify(requests.slice(requestBaseline))}`,
  );
  assert.equal(
    serverRequests.length,
    serverRequestBaseline,
    `interaction reached the static server: ${JSON.stringify(serverRequests.slice(serverRequestBaseline))}`,
  );
  assert.equal(rehearsal.activeElement, "result");
  assert.equal(rehearsal.dissentFixed, true);
  assert.equal(rehearsal.evidenceFixed, true);
  assert.equal(rehearsal.emptyQuestionDisablesComposition, true);
  assert.equal(rehearsal.firstVoice, "Dissent");
  assert.equal(rehearsal.focusedQuestion, privateSentinel);
  assert.equal(rehearsal.state, "afterglow");
  assert.equal(rehearsal.resultHidden, false);
  assert.equal(rehearsal.voiceCount, 5);
  assert.equal(rehearsal.questionIncluded, false);
  assert.equal(rehearsal.questionPresentInDocument, true);
  assert.equal(rehearsal.questionPersisted, false);
  assert.equal(rehearsal.questionTransmitted, false);
  assert.equal(rehearsal.questionTextLeaked, false);
  assert.equal(rehearsal.modelCalls, 0);
  assert.equal(rehearsal.grantsAuthority, false);
  assert.equal(rehearsal.persists, false);
  assert.equal(rehearsal.manifestEmitted, false);
  assert.equal(rehearsal.evidenceNamed, false);
  assert.equal(rehearsal.disposition, "Open preflight");

  for (const [label, trace] of [
    ["page requests", requests],
    ["server requests", serverRequests],
    ["console messages", consoleMessages],
    ["browser errors", browserErrors],
  ]) {
    assert.equal(
      JSON.stringify(trace).includes(privateSentinel),
      false,
      `private question escaped through ${label}: ${JSON.stringify(trace)}`,
    );
  }

  if (process.env.CALM_SCREENSHOT) {
    const screenshot = await cdp.send("Page.captureScreenshot", {
      captureBeyondViewport: true,
      format: "png",
      fromSurface: true,
    });
    writeFileSync(process.env.CALM_SCREENSHOT, Buffer.from(screenshot.data, "base64"));
  }

  const prefixedUrl =
    `http://127.0.0.1:${sitePort}/chillspace-commons/practices/calm-studio/`;
  await setViewport(cdp, 390, 844);
  await navigate(cdp, prefixedUrl);
  const prefixed = await layoutAt(cdp, 390, 844);
  assert(
    prefixed.scrollWidth <= prefixed.clientWidth,
    `prefixed document overflow: ${JSON.stringify(prefixed)}`,
  );
  assert.deepEqual(
    prefixed.overflowing,
    [],
    `prefixed elements escape viewport: ${JSON.stringify(prefixed.overflowing)}`,
  );
  assert.equal(prefixed.composeEnabled, true);

  const allowedTypes = new Set(["Document", "Stylesheet", "Script"]);
  const allowedPaths = new Set([
    "/practices/calm-studio/",
    "/practices/calm-studio/studio.css",
    "/practices/calm-studio/studio.js",
  ]);
  const networkRequests = requests.filter(({ url }) => /^https?:/u.test(url));
  assert(
    requests.every(
      ({ url }) =>
        /^https?:/u.test(url) || url.startsWith("data:image/svg+xml,"),
    ),
    `unexpected request protocol: ${JSON.stringify(requests)}`,
  );
  assert(
    networkRequests.every(({ type }) => allowedTypes.has(type)),
    `unexpected request types: ${JSON.stringify(networkRequests)}`,
  );
  assert(
    networkRequests.every((request) => {
      const parsed = new URL(request.url);
      const pathname = parsed.pathname.replace(/^\/chillspace-commons/u, "");
      return (
        parsed.origin === localOrigin &&
        parsed.search === "" &&
        parsed.hash === "" &&
        request.method === "GET" &&
        !request.hasPostData &&
        request.postData === null &&
        allowedPaths.has(pathname)
      );
    }),
    `unexpected public-room request: ${JSON.stringify(networkRequests)}`,
  );
  assert(
    serverRequests.every((request) => {
      const parsed = new URL(request.url, localOrigin);
      const pathname = parsed.pathname.replace(/^\/chillspace-commons/u, "");
      return (
        parsed.search === "" &&
        parsed.hash === "" &&
        request.method === "GET" &&
        request.body === "" &&
        allowedPaths.has(pathname)
      );
    }),
    `unexpected static-server request: ${JSON.stringify(serverRequests)}`,
  );
  assert.equal(browserErrors.length, 0, browserErrors.join("\n"));

  process.stdout.write(
    `Calm Studio browser boundary passed: ${networkRequests.length} reviewed static requests, ` +
      "zero interaction requests, private-sentinel containment, 320/390/1440px reflow, " +
      "fixed dissent, focused local rehearsal, and prefixed mirror.\n",
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

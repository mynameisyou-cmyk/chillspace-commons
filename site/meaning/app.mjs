import {
  MAX_TEXT_CODEPOINTS,
  RESPONSE_SCHEMA,
  findPublicEchoes,
} from "./engine.mjs";

document.documentElement.classList.remove("no-js");
document.documentElement.classList.add("js");

const $ = (id) => document.getElementById(id);
const elements = {
  form: $("echo-form"),
  utterance: $("utterance"),
  count: $("character-count"),
  button: $("echo-button"),
  promptList: $("prompt-list"),
  reading: $("reading"),
  readingTitle: $("reading-title"),
  noReading: $("no-reading"),
  featured: $("featured-gates"),
  mode: $("mode-badge"),
  dismiss: $("dismiss-button"),
  another: $("another-button"),
  stage: $("echo-stage"),
  planes: $("meaning-planes"),
  spokenLabel: $("spoken-label"),
  spoken: $("spoken-text"),
  lens: $("lens-label"),
  word: $("word"),
  pronunciation: $("pronunciation"),
  invitation: $("invitation"),
  gap: $("gap"),
  definition: $("definition"),
  morphemeRow: $("morpheme-row"),
  morphemes: $("morphemes"),
  sourceLink: $("source-link"),
  echo: $("chillspace-echo"),
  receipt: $("receipt-link"),
  related: $("related-list"),
  position: $("reading-position"),
  basis: $("match-basis"),
  why: $("match-why"),
  sourceCommit: $("source-commit"),
  sourceCount: $("source-count"),
  roomState: $("room-state"),
};

let dataset;
let activeMatches = [];
let activeIndex = 0;
let activeText = "";
let lastControl = null;
let lastMode = "example · yours can replace it";
let apiAvailable = false;
let offerSequence = 0;

function setText(node, value) {
  node.textContent = String(value ?? "");
}

function makeButton(label, className, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  button.textContent = label;
  button.addEventListener("click", onClick);
  return button;
}

function stripLightMarkdown(value) {
  return String(value ?? "").replace(/\*\*/g, "").replace(/\*/g, "");
}

function sourceUrl(entry) {
  const base = dataset.source.source_commit_url.replace(/\/+$/, "");
  return `${base}/${entry.id
    .split("/")
    .map(encodeURIComponent)
    .join("/")}`;
}

function bringIntoView(node, block = "start") {
  const reduced = window.matchMedia("(prefers-reduced-motion:reduce)").matches;
  node.scrollIntoView({behavior: reduced ? "auto" : "smooth", block});
}

function lensFor(id) {
  return dataset.lenses.find((lens) => lens.id === id) ?? dataset.lenses[0];
}

function setLens(id) {
  const lens = lensFor(id);
  elements.stage.style.setProperty("--lens", lens.accent);
  document.documentElement.style.setProperty("--lens", lens.accent);
  setText(elements.lens, lens.label);
}

function renderRelated(match) {
  elements.related.replaceChildren();
  for (const related of match.related) {
    const button = makeButton(related.word, "related-button", () => {
      elements.utterance.value = related.word;
      updateCount();
      lastControl = button;
      offer(related.word, {useApi: true, spokenLabel: "the word you chose"});
    });
    button.setAttribute("aria-label", `Enter the nearby YOUSPEAK gate ${related.word}`);
    elements.related.append(button);
  }
}

function renderActive() {
  const match = activeMatches[activeIndex];
  if (!match) return;
  const {canonical, interpretation} = match;
  setLens(interpretation.lens);

  setText(elements.spokenLabel, activeIndex === 0 ? elements.spokenLabel.dataset.base : "the same words, another gate");
  setText(elements.spoken, activeText);
  setText(elements.word, canonical.word);
  setText(elements.pronunciation, canonical.pronunciation || "pronunciation not carried in this snapshot");
  setText(elements.invitation, interpretation.invitation);
  setText(
    elements.gap,
    canonical.gap || "This transport snapshot carries no separate gap field for this word.",
  );
  setText(elements.definition, stripLightMarkdown(canonical.definition));

  if (canonical.decomposition.morphemes.length) {
    elements.morphemeRow.hidden = false;
    setText(elements.morphemes, canonical.decomposition.morphemes.join(" + "));
  } else {
    elements.morphemeRow.hidden = true;
    setText(elements.morphemes, "");
  }

  elements.sourceLink.href = sourceUrl(canonical);
  setText(elements.echo, match.chillspace_echo.text);
  elements.receipt.href = match.chillspace_echo.receipt.href;
  setText(elements.receipt, `${match.chillspace_echo.receipt.label} →`);
  renderRelated(match);

  setText(
    elements.position,
    activeMatches.length > 1
      ? `offered reading ${activeIndex + 1} of ${activeMatches.length}`
      : "one offered reading",
  );
  elements.another.hidden = activeMatches.length < 2;
  setText(elements.basis, interpretation.basis);
  setText(elements.why, interpretation.why);
  setText(elements.sourceCommit, dataset.source.source_commit);
  const count = dataset.source.counts.canon_entries;
  setText(
    elements.sourceCount,
    typeof count === "number"
      ? `Curated from a source snapshot carrying ${count} canon entries; this room offers ${dataset.entries.length}.`
      : `This room offers ${dataset.entries.length} curated gates from the pinned source snapshot.`,
  );

  elements.mode.textContent = lastMode;
  elements.noReading.hidden = true;
  elements.reading.hidden = false;
}

function showNoReading(text) {
  activeMatches = [];
  activeIndex = 0;
  activeText = text;
  elements.reading.hidden = true;
  elements.noReading.hidden = false;
  bringIntoView(elements.noReading, "center");
}

function localResponse(text, maxMatches = 3) {
  return findPublicEchoes(text, dataset, maxMatches);
}

async function fetchWithin(url, options, timeoutMs) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, {...options, signal: controller.signal});
  } finally {
    window.clearTimeout(timeout);
  }
}

async function apiResponse(text, maxMatches = 3) {
  const response = await fetchWithin("/api/meaning/echo", {
    method: "POST",
    headers: {
      "Accept": "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({text, max_matches: maxMatches}),
    cache: "no-store",
    credentials: "omit",
    referrerPolicy: "same-origin",
  }, 8000);
  const contentType = response.headers.get("content-type") ?? "";
  if (!response.ok || !contentType.startsWith("application/json")) {
    throw new Error("The live echo is unavailable.");
  }
  const body = await response.json();
  if (body.schema !== RESPONSE_SCHEMA || !Array.isArray(body.matches)) {
    throw new Error("The live echo returned an unknown contract.");
  }
  return body.matches;
}

async function detectApi() {
  try {
    const response = await fetchWithin("/api/meaning/echo", {
      method: "GET",
      headers: {"Accept": "application/json"},
      cache: "no-store",
      credentials: "omit",
      referrerPolicy: "same-origin",
    }, 3000);
    const contentType = response.headers.get("content-type") ?? "";
    if (
      response.status !== 405 ||
      !contentType.startsWith("application/json") ||
      response.headers.get("x-meaning-storage") !== "none"
    ) return false;
    const body = await response.json();
    return (
      body.schema === RESPONSE_SCHEMA &&
      body.error?.code === "method_not_allowed" &&
      body.stored === false
    );
  } catch {
    return false;
  }
}

async function offer(text, options = {}) {
  const clean = text.trim();
  if (!clean) {
    elements.utterance.setCustomValidity("Say something, or borrow a beginning.");
    elements.utterance.reportValidity();
    return;
  }
  if ([...clean].length > MAX_TEXT_CODEPOINTS) {
    elements.utterance.setCustomValidity(
      `Keep this to ${MAX_TEXT_CODEPOINTS} Unicode code points or fewer.`,
    );
    elements.utterance.reportValidity();
    return;
  }
  const sequence = ++offerSequence;
  elements.utterance.setCustomValidity("");
  elements.button.setAttribute("aria-busy", "true");
  elements.button.disabled = true;
  setText(elements.roomState, "listening…");

  let matches;
  let mode;
  if (options.useApi && apiAvailable) {
    try {
      matches = await apiResponse(clean);
      mode = "live echo · discarded after matching";
    } catch {
      matches = localResponse(clean);
      mode = "local recovery · live echo unavailable";
    }
  } else {
    matches = localResponse(clean);
    mode = options.mode ?? "local mirror · stayed in this browser";
  }

  if (sequence !== offerSequence) return;
  elements.button.removeAttribute("aria-busy");
  elements.button.disabled = false;
  setText(elements.roomState, `${dataset.entries.length} gates · ready`);
  if (!matches.length) {
    showNoReading(clean);
    return;
  }

  activeMatches = matches;
  activeIndex = 0;
  activeText = clean;
  lastMode = mode;
  elements.spokenLabel.dataset.base = options.spokenLabel ?? "what you said";
  renderActive();
  if (options.scroll !== false) {
    bringIntoView(elements.reading);
    elements.readingTitle.focus({preventScroll: true});
  }
}

function updateCount() {
  const points = [...elements.utterance.value];
  if (points.length > MAX_TEXT_CODEPOINTS) {
    elements.utterance.value = points.slice(0, MAX_TEXT_CODEPOINTS).join("");
  }
  const length = [...elements.utterance.value].length;
  setText(elements.count, `${length} / ${MAX_TEXT_CODEPOINTS}`);
  elements.count.classList.toggle("near-limit", length >= MAX_TEXT_CODEPOINTS * .85);
}

function renderPrompts() {
  for (const prompt of dataset.prompts) {
    const button = makeButton(prompt.label, "prompt-button", () => {
      elements.utterance.value = prompt.text;
      updateCount();
      lastControl = button;
      offer(prompt.text, {useApi: true, spokenLabel: "the beginning you borrowed"});
    });
    button.title = prompt.text;
    elements.promptList.append(button);
  }
}

function renderFeatured() {
  const words = ["kimance", "walkekin", "kintsugime", "muditaqing"];
  for (const word of words) {
    elements.featured.append(
      makeButton(word, "featured-button", () => {
        elements.utterance.value = word;
        updateCount();
        lastControl = elements.utterance;
        offer(word, {useApi: true, spokenLabel: "the word you chose"});
      }),
    );
  }
}

function enableDepth() {
  if (
    !window.matchMedia("(pointer:fine)").matches ||
    window.matchMedia("(prefers-reduced-motion:reduce)").matches
  ) return;

  elements.stage.addEventListener("pointermove", (event) => {
    const rect = elements.stage.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width - .5;
    const y = (event.clientY - rect.top) / rect.height - .5;
    elements.stage.style.setProperty("--tilt-y", `${(x * 3.2).toFixed(2)}deg`);
    elements.stage.style.setProperty("--tilt-x", `${(-y * 2.4).toFixed(2)}deg`);
  });
  elements.stage.addEventListener("pointerleave", () => {
    elements.stage.style.setProperty("--tilt-y", "0deg");
    elements.stage.style.setProperty("--tilt-x", "0deg");
  });
}

async function openRoom() {
  try {
    const response = await fetch("./echoes.json", {
      headers: {"Accept": "application/json"},
      cache: "no-cache",
      credentials: "omit",
    });
    if (!response.ok || !(response.headers.get("content-type") ?? "").includes("json")) {
      throw new Error("The canon projection is unavailable.");
    }
    dataset = await response.json();
    if (dataset.schema !== "chillspace.meaning-echo-canon/v1") {
      throw new Error("The canon projection has an unknown schema.");
    }
  } catch {
    setText(elements.roomState, "the room could not open");
    elements.form.closest(".composer").hidden = true;
    elements.reading.hidden = true;
    elements.noReading.hidden = false;
    setText(
      elements.noReading.querySelector("p:not(.section-number)"),
      "The canon projection did not arrive. No reading will be invented. Try again later.",
    );
    return;
  }

  renderPrompts();
  renderFeatured();
  updateCount();
  enableDepth();
  setText(elements.roomState, "checking the room’s boundary…");
  apiAvailable = await detectApi();
  elements.button.disabled = false;
  setText(elements.roomState, `${dataset.entries.length} gates · ready`);

  // A local-only opening tableau: it shows the room's depth without sending
  // a sentence anywhere. The visitor's first utterance replaces it.
  const opening = dataset.prompts[1].text;
  await offer(opening, {
    useApi: false,
    mode: "example · yours can replace it",
    spokenLabel: "a borrowed beginning",
    scroll: false,
  });
}

elements.form.addEventListener("submit", (event) => {
  event.preventDefault();
  lastControl = elements.button;
  offer(elements.utterance.value, {useApi: true, spokenLabel: "what you said"});
});

elements.utterance.addEventListener("input", updateCount);

elements.another.addEventListener("click", () => {
  activeIndex = (activeIndex + 1) % activeMatches.length;
  renderActive();
});

elements.dismiss.addEventListener("click", () => {
  elements.reading.hidden = true;
  elements.noReading.hidden = true;
  elements.utterance.value = "";
  updateCount();
  setText(elements.roomState, `${dataset.entries.length} gates · waiting`);
  (lastControl ?? elements.utterance).focus();
});

openRoom();

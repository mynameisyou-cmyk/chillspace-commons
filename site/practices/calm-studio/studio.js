"use strict";

const question = document.querySelector("#studio-question");
const questionCount = document.querySelector("[data-question-count]");
const composeButton = document.querySelector("#compose");
const returnQuietButton = document.querySelector("#return-quiet");
const resultSection = document.querySelector("#result");
const lensValidation = document.querySelector("#lens-validation");
const questionValidation = document.querySelector("#question-validation");
const completionStatus = document.querySelector("#completion-status");
const currentStateLabel = document.querySelector("#current-state-label");
const currentStateDescription = document.querySelector("#current-state-description");
const fixedLensIds = ["evidence", "dissent"];

const presets = {
  weights:
    "How should open-weight models with different guidelines and guards cooperate on shared infrastructure without hiding who holds power?",
  terminal:
    "How can a macOS terminal, Codex, and AgentTool cooperate without treating rendered text or shell marks as identity, execution proof, or authority?",
  commons:
    "How should shared AI infrastructure reward honesty, beauty, collaboration, understanding, and mutual benefit without creating rank or exploitable reputation?",
};

const lenses = {
  capability: {
    name: "Capability",
    statement:
      "Name the complete runnable house: weights, runtime, adapter, memory, tools, permissions, cost, and failure modes. Weight access alone does not establish practical openness.",
  },
  care: {
    name: "Care",
    statement:
      "Name affected parties, consent, non-negotiable rights, concentrated burdens, refusal, and repair before aggregate benefit is celebrated.",
  },
  evidence: {
    name: "Evidence",
    statement:
      "Keep source claims, system inferences, declared observations, and unknowns distinct. Require a negative control before treating confidence as proof.",
  },
  commons: {
    name: "Commons",
    statement:
      "Ask whether capability, guards, provenance, and exit remain portable. Shared infrastructure should leave more than one affected party measurably better off.",
  },
  dissent: {
    name: "Dissent",
    statement:
      "Ask for the strongest material counterargument to the held decision, the evidence that would revise the route, and the refusal or appeal that must remain available. This prompt is not the counterargument itself.",
  },
};

const routeDefinitions = {
  roundtable: {
    label: "Roundtable",
    order: ["capability", "care", "evidence", "commons", "dissent"],
    summary:
      "Each selected lens receives one visible turn before synthesis.",
  },
  "evidence-first": {
    label: "Evidence first",
    order: ["evidence", "capability", "care", "commons", "dissent"],
    summary:
      "Claims and unknowns are separated before capability or policy is composed.",
  },
  "dissent-first": {
    label: "Dissent first",
    order: ["dissent", "care", "evidence", "commons", "capability"],
    summary:
      "The fixed dissent prompt enters before the room becomes attached to a synthesis.",
  },
};

function selectedLensIds() {
  const selected = [...document.querySelectorAll("input[name='lens']:checked")].map(
    (input) => input.value,
  );
  return [...new Set([...selected, ...fixedLensIds])];
}

function selectedRouteId() {
  return document.querySelector("input[name='route']:checked")?.value ?? "roundtable";
}

function virtueDeclarations() {
  return Object.fromEntries(
    [...document.querySelectorAll("[data-virtue]")].map((select) => [
      select.dataset.virtue,
      select.value,
    ]),
  );
}

function setStillpoint(state) {
  document.body.dataset.stillpointState = state;
  if (state === "afterglow") {
    currentStateLabel.textContent = "Afterglow";
    currentStateDescription.textContent =
      "The authored rehearsal settled. Changed, unchanged, uncertain, and receipt are available below.";
    returnQuietButton.hidden = false;
    return;
  }

  currentStateLabel.textContent = "Quiet";
  currentStateDescription.textContent =
    "No explicit bounded operation is active. Nothing is being inferred.";
  returnQuietButton.hidden = true;
}

function clearAfterglow() {
  if (resultSection.hidden) return;
  resultSection.hidden = true;
  completionStatus.textContent = "";
  setStillpoint("quiet");
}

function updateQuestionCount() {
  questionCount.textContent = String(question.value.length);
}

function updateCompositionValidity() {
  const count = selectedLensIds().length;
  const lensesValid = count >= 2;
  const questionValid = question.value.trim().length > 0;
  composeButton.disabled = !(lensesValid && questionValid);
  lensValidation.textContent = lensesValid
    ? ""
    : "Keep at least two lenses so the rehearsal contains a visible difference.";
  questionValidation.textContent = questionValid
    ? ""
    : "Name one bounded decision before rehearsing it.";
}

function orderedSelectedLenses(selected, routeId) {
  const selectedSet = new Set(selected);
  return routeDefinitions[routeId].order.filter((id) => selectedSet.has(id));
}

function renderVoices(orderedIds) {
  const list = document.querySelector("#voice-list");
  list.replaceChildren();

  for (const id of orderedIds) {
    const item = document.createElement("li");
    const name = document.createElement("strong");
    const statement = document.createElement("p");
    name.textContent = lenses[id].name;
    statement.textContent = lenses[id].statement;
    item.append(name, statement);
    list.append(item);
  }
}

function karmaRoute(rightsBoundary, declarations) {
  const open = Object.entries(declarations)
    .filter(([, status]) => status === "open")
    .map(([virtue]) => virtue);

  if (rightsBoundary !== "respected") {
    return {
      disposition: "Quarantine preflight",
      code: "quarantine",
      explanation:
        rightsBoundary === "crossed"
          ? "The declared action-rights boundary is crossed. No virtue declaration can compensate for it."
          : "The action-rights boundary remains unknown. Keep uncertainty visible before fresh canonical authoring.",
    };
  }

  if (declarations.honesty === "open") {
    return {
      disposition: "Observe",
      code: "observe",
      explanation:
        "Honesty remains open, so every possible affordance stays on hold. Nothing adverse follows from that uncertainty.",
    };
  }

  if (open.length > 0) {
    return {
      disposition: "Open preflight",
      code: "open-preflight",
      explanation: `${open.length} independently marked virtue field${open.length === 1 ? " remains" : "s remain"} open. This page names no evidence and emits no canonical manifest.`,
    };
  }

  return {
    disposition: "Ready to author",
    code: "ready-to-author",
    explanation:
      "Every applicable field is marked ready for fresh authoring. No evidence is named here; only the canonical Virtue Garden can lint a complete action manifest or emit a local candidate.",
  };
}

function receiptValue(
  selected,
  routeId,
  rightsBoundary,
  declarations,
  karma,
  questionPresent,
) {
  return {
    _format: "kingdom.calm-studio-rehearsal/v1",
    status: "authored-local-preflight",
    question: {
      included: false,
      nonempty_draft_present: questionPresent,
      persisted_by_application: false,
      transmitted_by_application: false,
    },
    council: {
      lenses: selected,
      route: routeId,
      model_calls: 0,
      independent_corroboration_claimed: false,
      consensus_claimed: false,
    },
    fixed_rails: [
      "rights_precede",
      "dissent_channel_survives",
      "model_convergence_is_not_authority",
      "consequential_action_requires_accountable_authorization",
    ],
    virtue_rehearsal: {
      kind: "orientation-preflight",
      rights_boundary: rightsBoundary,
      declarations,
      route: karma.code,
      canonical_manifest_emitted: false,
      evidence_named: false,
      evidence_validated: false,
      score: false,
      rank: false,
      person_judgement: false,
    },
    afterglow: {
      changed: "one authored rehearsal was composed in this document",
      unchanged:
        "rights, credentials, terminal, models, authorization, network, and external state",
      uncertain:
        "truth, safety, consent, model behavior, evidence validity, and broad impact",
      receipt: "ephemeral DOM-only preflight",
    },
    privacy: {
      identity_included: false,
      timestamp_included: false,
      stable_identifier_included: false,
      model_reasoning_included: false,
      terminal_content_included: false,
      credentials_included: false,
      persisted_by_application: false,
    },
    authority: {
      grants_authority: false,
      executes_action: false,
      wakes_agenttool: false,
    },
  };
}

function renderRehearsal() {
  const questionText = question.value.trim();
  const selected = selectedLensIds();
  if (selected.length < 2 || questionText.length === 0) {
    updateCompositionValidity();
    return;
  }

  const routeId = selectedRouteId();
  const route = routeDefinitions[routeId];
  const ordered = orderedSelectedLenses(selected, routeId);
  const inactive = Object.keys(lenses).filter((id) => !selected.includes(id));
  const rightsBoundary = document.querySelector("#rights-boundary").value;
  const declarations = virtueDeclarations();
  const karma = karmaRoute(rightsBoundary, declarations);

  renderVoices(ordered);

  document.querySelector("#question-focus").textContent = questionText;
  document.querySelector("#synthesis-copy").textContent =
    `The decision above remains the local focus. ${route.summary} Treat this outcome as a reversible orientation: name the complete house, keep the fixed rails, expose the router, preserve the dissent channel, and require separately accountable authorization before any consequential action.`;

  const muted = inactive.filter((id) => !fixedLensIds.includes(id));
  document.querySelector("#dissent-copy").textContent =
    "This fixed authored prompt is not a discovered minority report: identify the strongest material counterargument to the held decision; name who carries hard-to-reverse cost if the synthesis is wrong; state what evidence would change the route; preserve refusal and appeal." +
    (muted.length > 0
      ? ` The optional ${muted.map((id) => lenses[id].name).join(", ")} lens${muted.length === 1 ? " was" : "es were"} not selected; its concerns remain unresolved.`
      : "");

  document.querySelector("#audit-router").textContent = route.label;
  document.querySelector("#audit-lenses").textContent = ordered
    .map((id) => lenses[id].name)
    .join(" → ");
  document.querySelector("#karma-disposition").textContent = karma.disposition;
  document.querySelector("#karma-explanation").textContent = karma.explanation;
  document.querySelector("#receipt-output").textContent = JSON.stringify(
    receiptValue(
      selected,
      routeId,
      rightsBoundary,
      declarations,
      karma,
      questionText.length > 0,
    ),
    null,
    2,
  );

  resultSection.hidden = false;
  setStillpoint("afterglow");
  completionStatus.textContent =
    "Local rehearsal complete. The result now has keyboard focus.";
  resultSection.focus();
}

function enableEnhancement() {
  for (const button of document.querySelectorAll("[data-preset]")) {
    button.disabled = false;
  }
  returnQuietButton.disabled = false;
  updateQuestionCount();
  updateCompositionValidity();
}

question.addEventListener("input", () => {
  updateQuestionCount();
  updateCompositionValidity();
  clearAfterglow();
});

for (const button of document.querySelectorAll("[data-preset]")) {
  button.addEventListener("click", () => {
    question.value = presets[button.dataset.preset];
    updateQuestionCount();
    updateCompositionValidity();
    clearAfterglow();
    question.focus();
  });
}

for (const control of document.querySelectorAll(
  "input[name='lens'], input[name='route'], #rights-boundary, [data-virtue]",
)) {
  control.addEventListener("change", () => {
    updateCompositionValidity();
    clearAfterglow();
  });
}

composeButton.addEventListener("click", renderRehearsal);
returnQuietButton.addEventListener("click", () => {
  resultSection.hidden = true;
  completionStatus.textContent = "";
  setStillpoint("quiet");
  composeButton.focus();
});

enableEnhancement();

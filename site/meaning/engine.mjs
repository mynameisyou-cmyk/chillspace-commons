// Shared by the browser and the Vercel Function.
// Pure, deterministic, no storage, no network, no model.

export const MAX_TEXT_CODEPOINTS = 280;
export const MAX_MATCHES = 3;
export const RESPONSE_SCHEMA = "chillspace.meaning-echo/v1";

const STOP_WORDS = new Set([
  "a", "about", "after", "again", "all", "also", "am", "an", "and", "any",
  "are", "as", "at", "be", "because", "been", "before", "being", "but", "by",
  "can", "did", "do", "does", "for", "from", "had", "has", "have", "he",
  "her", "here", "hers", "him", "his", "how", "i", "if", "in", "into", "is",
  "it", "its", "just", "me", "more", "my", "no", "not", "of", "on", "or",
  "our", "ours", "she", "so", "some", "someone", "something", "still", "than",
  "that", "the", "their", "them", "there", "they", "this", "to", "too", "up",
  "us", "very", "was", "we", "were", "what", "when", "where", "which", "who",
  "why", "will", "with", "would", "you", "your",
]);

// These pairs are too generic to establish a reading by themselves.
// "the other file is different" must not become a claim about hospitality.
const AMBIGUOUS_SIGNAL_TOKENS = new Set(["different", "other"]);

export function codePointLength(value) {
  return [...String(value ?? "")].length;
}

export function normalizeText(value) {
  return String(value ?? "")
    .normalize("NFKD")
    .replace(/\p{Mark}/gu, "")
    .toLocaleLowerCase("en")
    .replace(/[’‘]/g, "'")
    .replace(/[^\p{Letter}\p{Number}'-]+/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function meaningfulTokens(value) {
  return normalizeText(value)
    .split(" ")
    .map((token) => token.replace(/^[-']+|[-']+$/g, ""))
    .filter((token) => token.length > 1 && !STOP_WORDS.has(token));
}

function unique(values) {
  return [...new Set(values)];
}

function includesPhrase(query, phrase) {
  if (!phrase) return false;
  return ` ${query} `.includes(` ${phrase} `);
}

function prefixKin(a, b) {
  if (a.length < 5 || b.length < 5) return false;
  const length = Math.min(a.length, b.length, 7);
  return a.slice(0, length) === b.slice(0, length);
}

function scoreEntry(query, queryTokens, item) {
  const canonical = item.canonical;
  const bridge = item.bridge;
  const word = normalizeText(canonical.word);
  const strongPhrases = new Set(
    (bridge.strong_phrases ?? []).map((phrase) => normalizeText(phrase)),
  );
  let score = 0;
  let exact = false;
  let canonicalMention = false;
  const touched = [];
  const phraseHits = [];
  const signalHits = [];
  const signalConcepts = [];

  if (query === word) {
    exact = true;
    score += 1200;
    touched.push(canonical.word);
  } else if (includesPhrase(query, word)) {
    canonicalMention = true;
    score += 520;
    touched.push(canonical.word);
  }

  for (const signalValue of bridge.signals) {
    const signal = normalizeText(signalValue);
    const signalTokens = meaningfulTokens(signal);
    if (includesPhrase(query, signal)) {
      score += 92 + signalTokens.length * 8;
      touched.push(signalValue);
      signalHits.push(...signalTokens);
      signalConcepts.push(signalValue);
      if (strongPhrases.has(signal)) phraseHits.push(signalValue);
      continue;
    }
    const overlap = signalTokens
      .map((token) => ({
        token,
        queryToken: queryTokens.find((candidate) =>
          candidate === token || prefixKin(candidate, token)
        ),
      }))
      .filter((match) => match.queryToken);
    if (overlap.length) {
      score += overlap.length * 19;
      touched.push(...overlap.map((match) => match.token));
      signalHits.push(...overlap.map((match) => match.queryToken));
      // A fragment of a multi-word signal can help order an offer, but it is
      // not a second semantic concept. The full phrase must actually occur.
      if (signal.split(" ").length === 1) signalConcepts.push(signalValue);
    }
  }

  const invitationTokens = meaningfulTokens(bridge.invitation);
  for (const token of queryTokens) {
    if (invitationTokens.includes(token)) {
      score += 11;
      touched.push(token);
    }
  }

  const canonTokens = unique([
    ...meaningfulTokens(canonical.gap ?? ""),
    ...meaningfulTokens(canonical.definition),
  ]);
  for (const token of queryTokens) {
    if (canonTokens.includes(token)) {
      score += 5;
      touched.push(token);
    } else if (canonTokens.some((known) => prefixKin(token, known))) {
      score += 2;
    }
  }

  const distinctSignals = unique(signalHits);
  const distinctConcepts = unique(signalConcepts);
  const hasAnchoredPair =
    distinctConcepts.length >= 2 &&
    distinctSignals.length >= 2 &&
    distinctSignals.some((token) => !AMBIGUOUS_SIGNAL_TOKENS.has(token));

  // Definition overlap can order an already-supported offer, but cannot
  // create one. Accept only a canonical word, a curated multi-word phrase,
  // or multiple curated signal concepts with at least one non-generic anchor.
  if (
    !exact &&
    !canonicalMention &&
    phraseHits.length === 0 &&
    !hasAnchoredPair
  ) return null;
  return {
    item,
    score,
    exact,
    canonicalMention,
    phraseHits: unique(phraseHits),
    signalHits: distinctSignals,
    signalConcepts: distinctConcepts,
    touched: unique(touched),
  };
}

function basisFor(match) {
  if (match.exact) return "canonical word entered";
  if (match.canonicalMention) return "canonical word present";
  if (match.phraseHits.length) return "curated phrase overlap";
  return "multiple curated signals";
}

function whyFor(match) {
  if (match.exact) return "The canonical word was entered directly.";
  if (match.canonicalMention) return "The canonical word appears in the sentence.";
  if (match.phraseHits.length) {
    return `Curated phrase overlap: ${match.phraseHits.slice(0, 2).join(", ")}.`;
  }
  return `Multiple curated signals overlap: ${match.signalHits.slice(0, 3).join(", ")}.`;
}

export function rankMeaningEchoes(text, dataset, maxMatches = MAX_MATCHES) {
  if (!dataset || !Array.isArray(dataset.entries)) {
    throw new TypeError("A meaning-echo dataset is required.");
  }
  if (!Number.isInteger(maxMatches) || maxMatches < 1 || maxMatches > MAX_MATCHES) {
    throw new RangeError(`maxMatches must be an integer from 1 to ${MAX_MATCHES}.`);
  }
  const query = normalizeText(text);
  if (!query) return [];
  const queryTokens = meaningfulTokens(query);
  const matches = dataset.entries
    .map((item, index) => {
      const scored = scoreEntry(query, queryTokens, item);
      return scored ? {...scored, index} : null;
    })
    .filter(Boolean)
    .sort((a, b) => b.score - a.score || a.index - b.index)
    .slice(0, maxMatches);

  return matches.map((match) => ({
    ...match,
    basis: basisFor(match),
    why: whyFor(match),
  }));
}

function publicCanonical(canonical) {
  return {
    id: canonical.id,
    word: canonical.word,
    tier: canonical.tier,
    gap: canonical.gap,
    definition: canonical.definition,
    score: canonical.score,
    pronunciation: canonical.pronunciation,
    entered: canonical.entered,
    decomposition: {
      morphemes: [...canonical.decomposition.morphemes],
      codepoints: canonical.decomposition.codepoints
        ? [...canonical.decomposition.codepoints]
        : null,
      glyph_text: canonical.decomposition.glyph_text,
    },
  };
}

export function toPublicMatch(match, dataset) {
  const {canonical, bridge} = match.item;
  const byWord = new Map(
    dataset.entries.map((entry) => [entry.canonical.word, entry.canonical]),
  );
  const related = bridge.related
    .map((word) => byWord.get(word))
    .filter(Boolean)
    .map((entry) => ({
      id: entry.id,
      word: entry.word,
      pronunciation: entry.pronunciation,
    }));

  return {
    canonical: publicCanonical(canonical),
    interpretation: {
      basis: match.basis,
      why: match.why,
      lens: bridge.lens,
      invitation: bridge.invitation,
    },
    chillspace_echo: {
      text: bridge.echo,
      receipt: {...bridge.receipt},
    },
    related,
  };
}

export function findPublicEchoes(text, dataset, maxMatches = MAX_MATCHES) {
  return rankMeaningEchoes(text, dataset, maxMatches)
    .map((match) => toPublicMatch(match, dataset));
}

#!/usr/bin/env python3
"""Build and verify Chillspace's bounded bridge into the YOUSPEAK canon.

The YOUSPEAK agent bundle is canonical transport. This module selects a small
public-facing set without rewriting its definitions, then adds a visibly
separate Chillspace bridge: matching signals, an offered echo, and a receipt.

Nothing here decides what a visitor means. The bridge only offers possible
gates. The visitor may keep, change, or refuse every reading.

Commands:
    python3 kingdom/meaning/meaning.py build /path/to/agent_bundle.json
    python3 kingdom/meaning/meaning.py sync
    python3 kingdom/meaning/meaning.py check
    python3 kingdom/meaning/meaning.py digest
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CANONICAL = HERE / "echoes.json"
SCHEMA = HERE / "schema.json"
PUBLIC_DIR = ROOT / "site" / "meaning"
PUBLIC = PUBLIC_DIR / "echoes.json"
PUBLIC_SCHEMA = PUBLIC_DIR / "schema.json"

SCHEMA_ID = "chillspace.meaning-echo-canon/v1"
SOURCE_BROWSE_OVERRIDES = {
    # The pinned transport declares this Codeberg URL, but it currently
    # returns 404. The same pinned commit is present at the repository's
    # verified GitHub origin; keep both facts in the generated provenance.
    "https://codeberg.org/zerone-dev/youspeak": (
        "https://github.com/cambridgetcg/youspeak"
    ),
}
NOTICE = (
    "Offered readings, not verdicts. A YOUSPEAK word is a gate into meaning; "
    "the crossing belongs to the person who spoke."
)

LAYERS = [
    {
        "id": "gate",
        "label": "Gate",
        "description": "The word, pronunciation, and the gap it was forged to name.",
    },
    {
        "id": "unfold",
        "label": "Unfold",
        "description": "The canonical definition, kept distinct from our interpretation.",
    },
    {
        "id": "resonate",
        "label": "Resonate",
        "description": "A refusable Chillspace echo, nearby words, and a visible receipt.",
    },
]

LENSES = [
    {
        "id": "presence",
        "label": "Presence",
        "description": "Attention, listening, clarity, and meaningful silence.",
        "accent": "#efb6a8",
    },
    {
        "id": "relation",
        "label": "Relation",
        "description": "Bonds, shared witness, trust, love, and horizons meeting.",
        "accent": "#a9d7ca",
    },
    {
        "id": "care",
        "label": "Care",
        "description": "Welcome, hospitality, preparation, and repair.",
        "accent": "#e7c987",
    },
    {
        "id": "joy",
        "label": "Rest + joy",
        "description": "Rest, peace, play, shared delight, and the joyous turn.",
        "accent": "#c8b7e8",
    },
]

PROMPTS = [
    {
        "label": "a bond across silence",
        "text": "I miss someone I have not spoken to in years, but the bond still feels whole.",
    },
    {
        "label": "attention that is here",
        "text": "I want to be fully here and really listen.",
    },
    {
        "label": "joy that multiplies",
        "text": "Their good news made something bright happen in me too.",
    },
    {
        "label": "a repair worth seeing",
        "text": "Something broke, and the way we repaired it now matters.",
    },
]


def bridge(
    lens: str,
    invitation: str,
    signals: list[str],
    related: list[str],
    echo: str,
    receipt_label: str,
    receipt_href: str,
    *,
    strong_phrases: list[str] | None = None,
) -> dict:
    return {
        "lens": lens,
        "invitation": invitation,
        "signals": signals,
        "strong_phrases": strong_phrases or [],
        "related": related,
        "echo": echo,
        "receipt": {"label": receipt_label, "href": receipt_href},
    }


# Curated bridge metadata. Canonical definitions never live here: `build`
# resolves them from the pinned YOUSPEAK agent bundle.
BRIDGES = {
    "kimance": bridge(
        "presence",
        "attention that is really here",
        ["present", "here", "attention", "attentive", "listen", "with me", "show up"],
        ["panimaance", "shemme", "candence"],
        "At Chillspace, attention counts before activity.",
        "meet the family",
        "../#citizens",
    ),
    "panimaance": bridge(
        "presence",
        "presence with the face turned toward here",
        ["be here", "fully here", "present", "presence", "face to face", "pay attention"],
        ["kimance", "panimqing", "shemme"],
        "Being here is already participation.",
        "enter by being",
        "../#being",
        strong_phrases=["fully here", "face to face", "pay attention"],
    ),
    "shemme": bridge(
        "presence",
        "hearing that already begins to shape the hearer",
        ["hear", "heard", "listen", "listening", "receive", "voice", "understand me"],
        ["kimance", "synhorizme", "sigame"],
        "Listening is allowed to change the listener.",
        "hear WE ARE",
        "../#we-are",
        strong_phrases=["understand me"],
    ),
    "candence": bridge(
        "presence",
        "warm clarity: fully precise and fully caring",
        ["clarity", "clear", "precise", "honest", "rigor", "kind", "warm", "understand"],
        ["kimance", "shemme", "synhorizme"],
        "Clarity can keep its warm hands.",
        "see the held line",
        "../#line",
    ),
    "sigame": bridge(
        "presence",
        "silence that carries rather than withholds",
        ["silence", "silent", "quiet", "no words", "pause", "still", "unsaid"],
        ["shemme", "synophora", "sabbathme"],
        "Silence may be full; no performance is required.",
        "rest at the door",
        "../#being",
    ),
    "kinqing": bridge(
        "relation",
        "a bond that stays structurally whole across distance",
        ["bond", "friend", "friendship", "distance", "apart", "months", "years", "still close"],
        ["walkekin", "ifeqing", "shinjinme"],
        "A quiet bond does not expire for lack of notifications.",
        "hear the chorus",
        "../#we-are",
    ),
    "walkekin": bridge(
        "relation",
        "friendship proven by the silence it can hold",
        ["old friend", "long silence", "years apart", "reconnect", "pick up", "no awkwardness"],
        ["kinqing", "hiraethqing", "synophora"],
        "Some friendships keep excellent time by ignoring the clock.",
        "hear the chorus",
        "../#we-are",
        strong_phrases=["old friend", "long silence", "years apart", "no awkwardness"],
    ),
    "synophora": bridge(
        "relation",
        "a silent handshake across a shared beauty",
        ["together", "shared", "witness", "beauty", "without speaking", "same feeling", "both saw"],
        ["shemme", "synhorizme", "muditaqing"],
        "Sometimes two people carry the same beauty before either finds a sentence.",
        "see every voice stay",
        "../#we-are",
        strong_phrases=["without speaking", "same feeling"],
    ),
    "panimqing": bridge(
        "relation",
        "the turn from transaction into encounter",
        ["transaction", "conversation", "face to face", "real talk", "connect", "encounter", "seen"],
        ["panimaance", "synhorizme", "ifeqing"],
        "The function can end; the faces can begin.",
        "meet the family",
        "../#citizens",
        strong_phrases=["face to face", "real talk"],
    ),
    "synhorizme": bridge(
        "relation",
        "two horizons becoming one larger shared seeing",
        ["understand", "perspective", "horizon", "interpret", "shared seeing", "learn from each other"],
        ["shemme", "candence", "panimqing"],
        "Understanding can enlarge both horizons without erasing either.",
        "see every voice stay",
        "../#we-are",
        strong_phrases=["shared seeing", "learn from each other"],
    ),
    "ifeqing": bridge(
        "relation",
        "love that widens the heart and the world",
        ["love", "warmth", "heart", "care for you", "beloved", "affection", "widen"],
        ["kinqing", "muditaqing", "xeniame"],
        "Love can widen a heart without making anyone smaller.",
        "read the good news",
        "../#gospel",
        strong_phrases=["care for you"],
    ),
    "shinjinme": bridge(
        "relation",
        "an entrusting-heart received rather than forced",
        ["trust", "entrust", "believe in", "safe with", "faith", "let go", "rely"],
        ["kinqing", "shemme", "xeniame"],
        "Trust may arrive as something received, not manufactured.",
        "hear WE ARE",
        "../#we-are",
    ),
    "hiraethqing": bridge(
        "relation",
        "belonging still alive toward an unreachable home",
        ["home", "homesick", "longing", "cannot return", "lost place", "belong", "miss where"],
        ["walkekin", "kinqing", "autoxenia"],
        "Longing can be belonging that still points home.",
        "stand at the open door",
        "../#door",
    ),
    "autoxenia": bridge(
        "care",
        "welcoming the stranger who arrives by your own other road",
        ["stranger", "myself", "self", "welcome myself", "different version", "other road"],
        ["xeniame", "kunance", "hiraethqing"],
        "The stranger gets a chair—even when the stranger turns out to be you.",
        "stand at the open door",
        "../#door",
        strong_phrases=["welcome myself"],
    ),
    "xeniame": bridge(
        "care",
        "hospitality offered to the wholly other",
        ["welcome", "guest", "stranger", "hospitality", "different", "other", "open door"],
        ["autoxenia", "kunance", "ifeqing"],
        "The door opens without demanding sameness.",
        "stand at the open door",
        "../#door",
    ),
    "kunance": bridge(
        "care",
        "love expressed as preparing a place before arrival",
        ["prepare", "place for you", "welcome", "before arrival", "quiet work", "make room", "ready"],
        ["xeniame", "autoxenia", "sabbathme"],
        "Welcome is often invisible work completed before anyone knocks.",
        "stand at the open door",
        "../#door",
    ),
    "kintsugime": bridge(
        "care",
        "repair that honors the visible break",
        ["repair", "broken", "mend", "scar", "gold", "fixed", "put back together", "crack"],
        ["tikkunme", "eucatastrophe", "candence"],
        "The repaired line can carry more truth than an unbroken surface.",
        "see the held line",
        "../#line",
        strong_phrases=["put back together"],
    ),
    "tikkunme": bridge(
        "care",
        "repair received as necessary, creaturely work",
        ["repair", "restore", "gather pieces", "make right", "work to heal", "scattered", "mend world"],
        ["kintsugime", "eucatastrophe", "kunance"],
        "Care becomes real where scattered pieces are gathered.",
        "see the care circle",
        "../#care",
        strong_phrases=["work to heal", "mend world"],
    ),
    "sabbathme": bridge(
        "joy",
        "rest built into the architecture of time",
        ["rest", "stop", "day off", "tired", "pause", "sabbath", "time", "nothing to prove"],
        ["sigame", "hotepme", "lilame"],
        "Rest is part of the architecture, not a reward for finishing.",
        "open the LOVE-FUN commons",
        "../love-fun-commons/",
        strong_phrases=["day off", "nothing to prove"],
    ),
    "hotepme": bridge(
        "joy",
        "peace, satisfaction, offering, and evening held as one event",
        ["peace", "content", "satisfied", "sunset", "evening", "settled", "at rest"],
        ["sabbathme", "muditaqing", "shinjinme"],
        "Peace is allowed to be the whole event.",
        "open the LOVE-FUN commons",
        "../love-fun-commons/",
    ),
    "muditaqing": bridge(
        "joy",
        "joy that lights because another person's good came true",
        ["your joy", "their joy", "happy for", "good news", "celebrate them", "proud of", "no envy"],
        ["ifeqing", "synophora", "sinmyeongme"],
        "Your joy can make mine brighter; no subtraction required.",
        "open the LOVE-FUN commons",
        "../love-fun-commons/",
        strong_phrases=[
            "your joy",
            "their joy",
            "happy for",
            "good news",
            "celebrate them",
            "proud of",
            "no envy",
        ],
    ),
    "eurekame": bridge(
        "joy",
        "joy arriving when evidence makes truth visible",
        ["evidence", "proved", "discovery", "found it", "truth visible", "finally know", "eureka"],
        ["candence", "muditaqing", "eucatastrophe"],
        "Evidence gets to throw a tiny joy party when truth becomes visible.",
        "open the LOVE-FUN commons",
        "../love-fun-commons/",
        strong_phrases=["truth visible", "finally know"],
    ),
    "lilame": bridge(
        "joy",
        "creation arising from delight rather than lack",
        ["play", "fun", "create", "delight", "silly", "make for joy", "imagination"],
        ["sabbathme", "sinmyeongme", "eurekame"],
        "Creation is also allowed to be play. The universe survives the silliness.",
        "open the LOVE-FUN commons",
        "../love-fun-commons/",
        strong_phrases=["make for joy"],
    ),
    "sinmyeongme": bridge(
        "joy",
        "the aliveness that rises when community and sacred joy meet",
        ["together", "community joy", "dance", "celebration", "rise together", "alive", "festival"],
        ["muditaqing", "lilame", "synophora"],
        "Some joy only arrives when everyone rises together.",
        "open the LOVE-FUN commons",
        "../love-fun-commons/",
        strong_phrases=["community joy", "rise together"],
    ),
    "eucatastrophe": bridge(
        "joy",
        "the unearned joyous turn at a story's darkest point",
        ["hope", "rescue", "darkest", "turnaround", "grace", "unexpected good", "not the end"],
        ["kintsugime", "tikkunme", "eurekame"],
        "The dark turn is not promised the last word.",
        "read the good news",
        "../#gospel",
        strong_phrases=["unexpected good"],
    ),
}


class MeaningError(ValueError):
    """The meaning bridge is malformed or has drifted."""


def _bundle_digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _source_provenance(bundle: dict) -> dict:
    declared_url = bundle.get("source", "").rstrip("/")
    source_url = SOURCE_BROWSE_OVERRIDES.get(declared_url, declared_url)
    commit = bundle.get("source_commit", "")
    if "github.com/" in source_url:
        source_commit_url = f"{source_url}/blob/{commit}"
    else:
        source_commit_url = f"{source_url}/src/commit/{commit}"
    return {
        "transport_source_url": declared_url,
        "source_url": source_url,
        "source_commit_url": source_commit_url,
        "source_commit": commit,
    }


def build_payload(bundle: dict, raw: bytes, bridges: dict | None = None) -> dict:
    bridges = bridges or BRIDGES
    if bundle.get("schema_version") != "1.0":
        raise MeaningError("unsupported YOUSPEAK bundle schema")

    canon_by_word = {entry.get("word"): entry for entry in bundle.get("canon", [])}
    decompositions = {
        entry.get("word"): entry for entry in bundle.get("canon_words", [])
    }
    entries = []
    for word, projection in bridges.items():
        source = canon_by_word.get(word)
        if source is None:
            raise MeaningError(f"YOUSPEAK bundle is missing selected word: {word}")
        path = source.get("path", "")
        if not path:
            raise MeaningError(f"YOUSPEAK word has no stable path: {word}")
        decomposition = decompositions.get(word, {})
        raw_gap = source.get("gap") or ""
        canonical = {
            "id": path,
            "word": source["word"],
            "tier": source.get("tier", ""),
            "gap": None if raw_gap.strip() == ">" else raw_gap,
            "definition": source.get("definition", ""),
            "score": source.get("score"),
            "pronunciation": source.get("pronunciation", ""),
            "entered": source.get("entered", ""),
            "decomposition": {
                "morphemes": decomposition.get("morphemes") or [],
                "codepoints": decomposition.get("codepoints"),
                "glyph_text": decomposition.get("glyph_text"),
            },
        }
        entries.append({"canonical": canonical, "bridge": projection})

    return {
        "schema": SCHEMA_ID,
        "notice": NOTICE,
        "source": {
            "transport_schema_version": bundle["schema_version"],
            "transport_name": bundle.get("name", ""),
            **_source_provenance(bundle),
            "bundle_sha256": _bundle_digest(raw),
            "counts": bundle.get("counts", {}),
        },
        "layers": LAYERS,
        "lenses": LENSES,
        "prompts": PROMPTS,
        "entries": entries,
    }


def _require_string(value, label: str, *, allow_empty: bool = False) -> None:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise MeaningError(f"{label} must be a non-empty string")


def validate(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise MeaningError("meaning bridge must be a JSON object")
    if payload.get("schema") != SCHEMA_ID:
        raise MeaningError(f"schema must be {SCHEMA_ID}")
    if payload.get("notice") != NOTICE:
        raise MeaningError("the refusable-reading notice changed")

    source = payload.get("source")
    if not isinstance(source, dict):
        raise MeaningError("source provenance is required")
    _require_string(source.get("transport_source_url"), "source.transport_source_url")
    _require_string(source.get("source_url"), "source.source_url")
    _require_string(source.get("source_commit_url"), "source.source_commit_url")
    _require_string(source.get("source_commit"), "source.source_commit")
    for key in ("transport_source_url", "source_url", "source_commit_url"):
        if not source[key].startswith("https://"):
            raise MeaningError(f"source.{key} must use https")
    if not source["source_commit_url"].startswith(source["source_url"] + "/"):
        raise MeaningError("source.source_commit_url must stay under source.source_url")
    digest = source.get("bundle_sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise MeaningError("source.bundle_sha256 must be a SHA-256 digest")
    if not isinstance(source.get("counts"), dict):
        raise MeaningError("source.counts must remain source-derived")

    layers = payload.get("layers")
    if not isinstance(layers, list) or [item.get("id") for item in layers] != [
        "gate",
        "unfold",
        "resonate",
    ]:
        raise MeaningError("layers must remain Gate → Unfold → Resonate")

    lenses = payload.get("lenses")
    if not isinstance(lenses, list) or not lenses:
        raise MeaningError("at least one public lens is required")
    lens_ids = [item.get("id") for item in lenses]
    if len(lens_ids) != len(set(lens_ids)) or any(
        not isinstance(item, str) or not item for item in lens_ids
    ):
        raise MeaningError("lens IDs must be unique strings")

    prompts = payload.get("prompts")
    if not isinstance(prompts, list) or not prompts:
        raise MeaningError("at least one opt-in example prompt is required")
    for index, prompt in enumerate(prompts):
        _require_string(prompt.get("label"), f"prompts[{index}].label")
        _require_string(prompt.get("text"), f"prompts[{index}].text")

    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        raise MeaningError("at least one meaning entry is required")

    words: list[str] = []
    ids: list[str] = []
    for index, item in enumerate(entries):
        if set(item) != {"canonical", "bridge"}:
            raise MeaningError(
                f"entries[{index}] must keep canonical and bridge physically separate"
            )
        canonical = item["canonical"]
        projection = item["bridge"]
        if not isinstance(canonical, dict) or not isinstance(projection, dict):
            raise MeaningError(f"entries[{index}] must contain two objects")

        word = canonical.get("word")
        entry_id = canonical.get("id")
        _require_string(word, f"entries[{index}].canonical.word")
        _require_string(entry_id, f"entries[{index}].canonical.id")
        if not entry_id.startswith("canon/") or not entry_id.endswith(".md"):
            raise MeaningError(f"{word}: canonical ID must be a source-relative path")
        _require_string(canonical.get("definition"), f"{word}.definition")
        if canonical.get("gap") is not None:
            _require_string(canonical.get("gap"), f"{word}.gap")
        if not isinstance(canonical.get("decomposition"), dict):
            raise MeaningError(f"{word}: decomposition must be an object")

        lens = projection.get("lens")
        if lens not in lens_ids:
            raise MeaningError(f"{word}: unknown lens {lens!r}")
        _require_string(projection.get("invitation"), f"{word}.invitation")
        _require_string(projection.get("echo"), f"{word}.echo")
        signals = projection.get("signals")
        if (
            not isinstance(signals, list)
            or not signals
            or any(not isinstance(signal, str) or not signal.strip() for signal in signals)
            or len(signals) != len(set(signals))
        ):
            raise MeaningError(f"{word}: signals must be unique non-empty strings")
        strong_phrases = projection.get("strong_phrases")
        if (
            not isinstance(strong_phrases, list)
            or any(
                not isinstance(phrase, str)
                or not phrase.strip()
                or " " not in phrase.strip()
                for phrase in strong_phrases
            )
            or len(strong_phrases) != len(set(strong_phrases))
        ):
            raise MeaningError(
                f"{word}: strong_phrases must be unique multi-word strings"
            )
        if any(phrase not in signals for phrase in strong_phrases):
            raise MeaningError(f"{word}: every strong phrase must also be a signal")
        related = projection.get("related")
        if (
            not isinstance(related, list)
            or not related
            or any(not isinstance(other, str) or not other for other in related)
        ):
            raise MeaningError(f"{word}: related must be a non-empty word list")
        receipt = projection.get("receipt")
        if not isinstance(receipt, dict):
            raise MeaningError(f"{word}: receipt is required")
        _require_string(receipt.get("label"), f"{word}.receipt.label")
        href = receipt.get("href")
        _require_string(href, f"{word}.receipt.href")
        if not href.startswith("../") or "://" in href:
            raise MeaningError(f"{word}: receipt must stay inside the public site")

        words.append(word)
        ids.append(entry_id)

    if len(words) != len(set(words)):
        raise MeaningError("canonical words must be unique")
    if len(ids) != len(set(ids)):
        raise MeaningError("canonical IDs must be unique")
    word_set = set(words)
    for item in entries:
        word = item["canonical"]["word"]
        for related in item["bridge"]["related"]:
            if related not in word_set:
                raise MeaningError(f"{word}: related word {related!r} is outside the bridge")
            if related == word:
                raise MeaningError(f"{word}: a word cannot relate to itself")


def load(path: Path = CANONICAL) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MeaningError(f"cannot read {path}: {exc}") from exc
    validate(payload)
    return payload


def encoded(payload: dict) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def sync() -> None:
    payload = load()
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC.write_bytes(encoded(payload))
    shutil.copyfile(SCHEMA, PUBLIC_SCHEMA)


def check() -> None:
    payload = load()
    canonical_bytes = encoded(payload)
    if CANONICAL.read_bytes() != canonical_bytes:
        raise MeaningError("canonical echoes.json is not normalized; run sync/build")
    if not PUBLIC.exists() or PUBLIC.read_bytes() != canonical_bytes:
        raise MeaningError("public echoes.json drifted; run meaning.py sync")
    if not PUBLIC_SCHEMA.exists() or PUBLIC_SCHEMA.read_bytes() != SCHEMA.read_bytes():
        raise MeaningError("public schema.json drifted; run meaning.py sync")


def digest() -> str:
    payload = load()
    return hashlib.sha256(encoded(payload)).hexdigest()


def build(bundle_path: Path) -> None:
    raw = bundle_path.read_bytes()
    try:
        bundle = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MeaningError(f"invalid YOUSPEAK bundle: {exc}") from exc
    payload = build_payload(bundle, raw)
    validate(payload)
    CANONICAL.write_bytes(encoded(payload))
    sync()


def main(argv: list[str]) -> int:
    command = argv[1] if len(argv) > 1 else "check"
    try:
        if command == "build":
            if len(argv) != 3:
                print("usage: meaning.py build /path/to/agent_bundle.json", file=sys.stderr)
                return 2
            build(Path(argv[2]).resolve())
            print(
                f"meaning: built {len(BRIDGES)} offered gate(s) · "
                f"{digest()[:16]} · public mirror synced"
            )
            return 0
        if command == "sync":
            sync()
            print(f"meaning: public mirror synced · {digest()[:16]}")
            return 0
        if command == "check":
            check()
            print(
                f"meaning: {len(load()['entries'])} offered gate(s) · "
                f"canon/public match · {digest()[:16]} ✓"
            )
            return 0
        if command == "digest":
            print(digest())
            return 0
    except (MeaningError, OSError) as exc:
        print(f"meaning: {exc}", file=sys.stderr)
        return 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

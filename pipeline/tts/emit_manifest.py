"""Emit per-language TTS manifests in the client-derivable (schema 2) format.

## Why this exists

The legacy manifest was a single flat JSON mapping every `"<lang>:<text>"`
cache key to its relative mp3 path:

    {"ja:こんにちは": "tts/ja/c34e1a1b60652761.mp3", ...}

That file is ~1.0 MB for ~14k entries, and the app imports it at BUILD time,
so every visitor downloads the whole thing — including the languages they
are not studying. It also duplicates information the client can derive: the
path is a pure function of the key.

    hash16 = sha256(f"{lang}:{text}").hexdigest()[:16]
    path   = f"{prefix}/{hash16}.mp3"

So schema 2 ships, per language, only:

  * `hashes` — every hash16 that EXISTS, sorted and concatenated into one
    string (16 chars each, no separators). The client slices it into a Set
    once and then answers "do we have audio for this text?" in O(1) without
    ever storing the text.
  * `overrides` — the entries that are NOT derivable, as an explicit
    text → path(s) map. See below.

Net effect: ~1.0 MB of JSON becomes ~280 KB across four files, and a Korean
learner never downloads the Japanese set.

## Overrides — why a fully-derivable manifest isn't possible

Two classes of entry can't be derived:

1. **Multi-voice entries.** `add_alt_voice` generates a second recording
   hashed as `f"{lang}:{text}::{voice}"` so the app can rotate voices. The
   client would have to know the exact voice ID string to re-derive it, which
   couples the app to pipeline voice config. Cheaper to list them (67 today).

2. **`ja-keita:` dialogue lines (679 today).** Produced by
   `gen_dialogue_voices.py`, which hashes with **SHA-1**, not SHA-256, and
   hardcodes its output directory to `tts/ja/` regardless of the key's
   language prefix. It is the only producer in the pipeline that does either.

   Since the app's resolver computes SHA-256, these are not client-derivable
   and are carried as explicit overrides. Confirmed:
   `sha1("ja-keita:<text>")[:16]` reproduces all 679 published paths exactly.

   To retire the block: regenerate under the standard scheme
   (`generate.py --lang ja-keita` — ja-keita is a first-class language there
   now), publish, re-emit, then drop the overrides. The old SHA-1 files become
   orphans for the sweep. Until then the overrides work and audio plays.

## Output

    <out-dir>/manifest/<lang>.json     one per language
    <out-dir>/manifest.json            legacy flat map, still written

The legacy file is kept so nothing that reads it breaks mid-migration. It can
be dropped once the app is fully on schema 2.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from . import paths

SCHEMA = 2

# Path prefix every derivable entry lives under. Bump this (v1 → v2) on a MASS
# regeneration — a voice swap, a provider change — so newly generated audio
# lands on fresh URLs instead of overwriting bytes that clients have cached
# under `immutable`. Targeted one-off regens (regen_best fixing a single bad
# kana) stay on the same prefix and take a CloudFront invalidation instead.
VERSION_PREFIX = "v1"

# Where a language's LEGACY (pre-migration) files were written, when that
# differs from the language name. `ja-keita` names a voice, and the bespoke
# script that produced it dropped its output into the shared `tts/ja/`
# directory rather than one of its own.
#
# This applies ONLY to locating legacy files. Anything generated from here on
# writes to `<out>/<lang>/`, so `prefix_for` deliberately does not consult it
# — a regenerated ja-keita clip lives at `tts/v1/ja-keita/<hash>.mp3`.
LEGACY_DIR_FOR_LANG: dict[str, str] = {"ja-keita": "ja"}


def hash16(cache_key: str) -> str:
    """The pipeline's content hash. Must stay byte-identical to generate.py."""
    return hashlib.sha256(cache_key.encode("utf-8")).hexdigest()[:16]


def prefix_for(lang: str) -> str:
    """Where NEWLY generated audio for `lang` is published."""
    return f"tts/{VERSION_PREFIX}/{lang}"


def _legacy_path_for(lang: str, h: str) -> str:
    """Where an UN-versioned (pre-migration) file sits on disk."""
    return f"tts/{LEGACY_DIR_FOR_LANG.get(lang, lang)}/{h}.mp3"


def build(manifest: dict[str, str | list[str]]) -> dict[str, dict]:
    """Split a flat legacy manifest into per-language schema-2 documents."""
    hashes: dict[str, set[str]] = defaultdict(set)
    overrides: dict[str, dict[str, str | list[str]]] = defaultdict(dict)

    for key, value in manifest.items():
        if ":" not in key:
            continue
        lang, text = key.split(":", 1)
        paths_list = [value] if isinstance(value, str) else list(value)
        if not paths_list:
            continue

        derived = hash16(key)
        expected = _legacy_path_for(lang, derived)

        # Derivable ONLY when there is exactly one recording and it sits at
        # exactly the path the hash implies. A second voice, or a path that
        # disagrees, forces an explicit entry.
        if len(paths_list) == 1 and paths_list[0] == expected:
            hashes[lang].add(derived)
        else:
            overrides[lang][text] = (
                _versioned(paths_list[0]) if len(paths_list) == 1
                else [_versioned(p) for p in paths_list]
            )

    langs = sorted(set(hashes) | set(overrides))
    return {
        lang: {
            "schema": SCHEMA,
            "lang": lang,
            "prefix": prefix_for(lang),
            "count": len(hashes[lang]),
            # Sorted + concatenated: the client slices this into 16-char
            # chunks. Sorting keeps the output stable across runs so the file
            # only changes when the content does (clean diffs, cache-friendly).
            "hashes": "".join(sorted(hashes[lang])),
            "overrides": overrides[lang],
        }
        for lang in langs
    }


def _versioned(rel: str) -> str:
    """Rewrite `tts/<dir>/<file>` → `tts/<version>/<dir>/<file>`."""
    parts = rel.split("/")
    if len(parts) == 3 and parts[0] == "tts":
        return f"tts/{VERSION_PREFIX}/{parts[1]}/{parts[2]}"
    return rel


def write(docs: dict[str, dict], out_dir: Path) -> list[Path]:
    manifest_dir = out_dir / "manifest"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for lang, doc in docs.items():
        p = manifest_dir / f"{lang}.json"
        p.write_text(
            json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        written.append(p)

    # An index so a consumer (the app build, or lingo-data later) can discover
    # which languages exist without probing for files.
    index = manifest_dir / "index.json"
    index.write_text(
        json.dumps(
            {
                "schema": SCHEMA,
                "version": VERSION_PREFIX,
                "languages": sorted(docs),
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    written.append(index)
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    paths.add_out_dir_arg(ap)
    ap.add_argument(
        "--source-manifest",
        help="Flat legacy manifest to convert (default: <out-dir>/manifest.json)",
    )
    args = ap.parse_args()

    out = paths.out_dir(args.out_dir)
    src = Path(args.source_manifest) if args.source_manifest else out / "manifest.json"
    if not src.exists():
        print(f"No manifest at {src}")
        return 1

    manifest = json.loads(src.read_text(encoding="utf-8"))
    docs = build(manifest)
    written = write(docs, out)

    total_hashes = sum(d["count"] for d in docs.values())
    total_over = sum(len(d["overrides"]) for d in docs.values())
    print(f"Source: {src}  ({len(manifest)} entries)")
    for lang in sorted(docs):
        d = docs[lang]
        size = (out / "manifest" / f"{lang}.json").stat().st_size
        print(
            f"  {lang:10} derivable={d['count']:6}  overrides={len(d['overrides']):5}"
            f"  {size / 1024:7.1f} KB"
        )
    print(f"\nderivable={total_hashes}  overrides={total_over}  files={len(written)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

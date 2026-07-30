"""Synthesize dialogue-speaker clips with real per-speaker voices.

Two-voice dialogues (Spencer 2026-07-19): male-named speakers (Tom, Ken,
Tanaka) speak with ja-JP-KeitaNeural under `ja-keita:` manifest keys;
female/neutral speakers stay Nanami on plain `ja:` keys. No pitch
processing anywhere — real voices, raw clips.

The Nanami dialogue set is REFRESHED as one batch by default: dialogue
lines chain per-sentence, and sentence clips of mixed vintage carry
noticeably different takes ("weird pitch" — Spencer). Regenerating the
whole set in one run keeps the takes consistent. Keita clips are filled
when missing (use --force to redo them too).

Reads the auto-emitted decks (lingo scripts/emit-tts-deck.mjs):
  test_decks/ja-keita-dialogue.json   → ja-keita:<text>, KeitaNeural
  test_decks/ja-nanami-dialogue.json  → ja:<text>,       NanamiNeural

Usage:
    python -m pipeline.tts.gen_dialogue_voices
    python -m pipeline.tts.gen_dialogue_voices --force
    python -m pipeline.tts.gen_dialogue_voices --skip-nanami-refresh

## Hash scheme — SHA-1, NOT SHA-256

This script is the ONLY producer in the pipeline that hashes with SHA-1
(`sha1("<lang>:<text>")[:16]`) and the only one that hardcodes its output
directory to `tts/ja/` regardless of the manifest key's language prefix. Every
other script uses `sha256(...)[:16]` and `tts/<lang>/`.

That divergence is why the 679 `ja-keita:` clips cannot be derived by the app's
client-side resolver, which computes SHA-256 — they are carried as explicit
`overrides` in the schema-2 manifest instead. Verified: SHA-1 reproduces all
679 published paths exactly.

Do NOT "fix" this to SHA-256 without regenerating and re-uploading, or every
existing keita clip becomes unreachable. Retiring the override block means:
regenerate under the standard scheme (`generate.py --lang ja-keita` — ja-keita
is a first-class language there now), publish, re-emit the manifest, then drop
the overrides.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path

import edge_tts

from . import paths

OUT_DIR = paths.out_dir()
MANIFEST = paths.manifest_path()
DECKS = paths.decks_dir()


def synth_deck(
    deck_path: Path,
    manifest: dict,
    *,
    voice: str,
    key_prefix: str,
    refresh: bool,
) -> tuple[int, int, int]:
    deck = json.loads(deck_path.read_text(encoding="utf-8"))
    wrote = skipped = failed = 0
    for card in deck["cards"]:
        text = card["front"]
        key = f"{key_prefix}{text}"
        existing = manifest.get(key)
        # Keep an existing path stable (URLs don't churn); mint one
        # voice-scoped otherwise. Array entries (alt-voice variants) are
        # collapsed to their primary path — dialogue voices must be
        # deterministic per speaker.
        if isinstance(existing, list):
            existing = existing[0] if existing else None
        rel = existing or f"tts/ja/{hashlib.sha1(key.encode()).hexdigest()[:16]}.mp3"
        # `rel` starts with "tts/", and OUT_DIR ends with it — resolve against
        # the parent so the path isn't doubled. (The pre-relocation version
        # wrote into the frontend's src/pub; LINGO_FE no longer exists.)
        out = OUT_DIR.parent / rel
        if not refresh and manifest.get(key) == rel and out.exists():
            skipped += 1
            continue
        try:
            asyncio.run(edge_tts.Communicate(text, voice=voice).save(str(out)))
            manifest[key] = rel
            wrote += 1
        except Exception as e:  # noqa: BLE001 — report and continue
            failed += 1
            print(f"  FAILED {text!r}: {e}", file=sys.stderr)
    print(f"{deck_path.name}: wrote={wrote} skipped={skipped} failed={failed}")
    return wrote, skipped, failed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="refresh Keita clips too")
    parser.add_argument(
        "--skip-nanami-refresh",
        action="store_true",
        help="only fill missing clips; don't re-take the Nanami dialogue set",
    )
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    (OUT_DIR / "ja").mkdir(parents=True, exist_ok=True)

    failures = 0
    failures += synth_deck(
        DECKS / "ja-keita-dialogue.json",
        manifest,
        voice="ja-JP-KeitaNeural",
        key_prefix="ja-keita:",
        refresh=args.force,
    )[2]
    failures += synth_deck(
        DECKS / "ja-nanami-dialogue.json",
        manifest,
        voice="ja-JP-NanamiNeural",
        key_prefix="ja:",
        refresh=not args.skip_nanami_refresh,
    )[2]

    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

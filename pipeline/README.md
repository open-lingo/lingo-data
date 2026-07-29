# TTS generation pipeline

Pre-generates MP3 audio for lesson/vocab content. This pipeline used to live
in `lingo-core/scripts/tts` and wrote directly into the frontend's Vite
publicDir. It now lives here in `lingo-data` so the audio-generation effort
is centralized and **decoupled from the app repo**: generation writes to a
configurable output directory, and the eventual target is an S3/CDN bucket
the app consumes via an asset base URL.

## Providers

| Provider | Languages / voices | Quality | Use |
|---|---|---|---|
| **Edge-TTS** (default) | `ja`: `ja-JP-NanamiNeural` (F), `ja-JP-KeitaNeural` (M) | High | Production audio |
| Kokoro | `ja`: 5 voices (`jf_alpha`, `jf_gongitsune`, `jf_nezumi`, `jf_tebukuro`, `jm_kumo`) | Medium (vocaloid-like) | Local / offline fallback |

- **Edge-TTS** — Microsoft's free cloud API, no key required. Quality jump
  over Kokoro at the cost of needing internet at generation time.
- **Kokoro** — local, offline, CPU-real-time (82M params). No network needed.

Both write the same on-disk layout, so swapping providers is just a
regenerate. Adding a provider (ElevenLabs, Style-Bert-VITS2, …) is a new
`TtsProvider` subclass registered in `PROVIDERS` in `tts/generate.py`.

Edge-TTS only ships **two** Japanese voices today; the rest (Aoi, Daichi,
Mayu) were retired and are now Azure-only (paid). Re-check the live list:

```bash
.venv-tts/bin/python -c "import asyncio,edge_tts; \
  print([v['ShortName'] for v in asyncio.run(edge_tts.list_voices()) if v['Locale'].startswith('ja')])"
```

## Setup

```bash
# From the repo root.
python3 -m venv .venv-tts
.venv-tts/bin/python -m pip install --upgrade pip
.venv-tts/bin/python -m pip install -r pipeline/requirements.txt

# System binaries (subprocess deps for padding / silence-detect / audit):
sudo apt-get install ffmpeg      # provides ffmpeg + ffprobe; or: brew install ffmpeg

# Kokoro only — download the Japanese dictionary once (~526 MB):
.venv-tts/bin/python -m unidic download
```

Scripts run as package modules from the repo root:

```bash
.venv-tts/bin/python -m pipeline.tts.generate --help
```

## Configurable output (the point of the move)

Output is no longer hardcoded to the frontend. Resolution order:

1. `--out-dir <path>` flag (on the write scripts: `generate`,
   `add_alt_voice`, `pad_silence`)
2. `$TTS_OUT_DIR` env var (honored by **every** script)
3. default `./out/tts` (relative to the repo root)

Deck input (read only by `generate`) resolves the same way via `--decks-dir`
/ `$TTS_DECKS_DIR`, defaulting to `./data/test_decks` (the sibling content
repo). All path resolution lives in `tts/paths.py`.

```bash
# Default: writes ./out/tts, reads ./data/test_decks
.venv-tts/bin/python -m pipeline.tts.generate --provider edge

# Explicit dirs
.venv-tts/bin/python -m pipeline.tts.generate \
    --provider edge \
    --out-dir /tmp/tts \
    --decks-dir /path/to/decks

# Or via env (applies to all scripts)
export TTS_OUT_DIR=/data/lingo-tts
.venv-tts/bin/python -m pipeline.tts.whisper_audit
```

## Generating audio

```bash
# See what would be generated, no model load (works for either provider)
.venv-tts/bin/python -m pipeline.tts.generate --provider edge --dry-run

# Generate everything not yet cached
.venv-tts/bin/python -m pipeline.tts.generate --provider edge

# Force regeneration of every file (e.g. after switching voices)
.venv-tts/bin/python -m pipeline.tts.generate --provider edge --force

# Local Kokoro instead of cloud Edge
.venv-tts/bin/python -m pipeline.tts.generate --provider kokoro

# One language / specific voice / stop after N (debugging)
.venv-tts/bin/python -m pipeline.tts.generate --lang ja
.venv-tts/bin/python -m pipeline.tts.generate --voice ja-JP-KeitaNeural
.venv-tts/bin/python -m pipeline.tts.generate --limit 3

# Voice-comparison samples (one fixed phrase × every voice)
.venv-tts/bin/python -m pipeline.tts.generate --samples --all-providers
```

Performance reference (Edge-TTS): ~0.5–1.0s per phrase, network-bound.

### Supporting / experimental scripts

- `add_alt_voice` — generate a second voice for every manifest entry (Keita
  alongside Nanami), rewriting manifest values to arrays for runtime voice
  rotation.
- `gen_phrases` / `gen_yoon` — synthesize ad-hoc phrases / the 33 hiragana
  yōon with trailing-silence padding.
- `pad_silence` — pad every mp3 with trailing silence so decoders don't
  clip the tail of short utterances. Idempotent via a `.padded` marker.
- `regen_period` / `regen_short_kana` / `regen_best` — single-kana
  regeneration strategies (trailing-kuten, carrier-wrap+trim, best-of-N by
  Whisper score) for the edge-tts short-syllable bug.
- `short_kana_trials` / `sokuon_trials` — A/B different priming strategies
  into a trials directory for manual comparison.
- `manifest_voice_filter` — narrow specific entries to a single voice.

## Whisper QA / audit

The single-mora Japanese files are the fragile ones (edge-tts can produce
doubled-mora "いい" artifacts or under-pronounce). The audit transcribes
generated audio with faster-whisper and string-compares to the intended
kana, categorizing each as `exact` / `doubled` / `partial` / `wrong` /
`empty`.

```bash
# Audit all single-kana files (model: tiny/base/small/medium)
.venv-tts/bin/python -m pipeline.tts.whisper_audit --csv /tmp/whisper.csv

# Yōon-only audit
.venv-tts/bin/python -m pipeline.tts.whisper_yoon_audit

# Acoustic-features (ffmpeg-only) analysis, no model
.venv-tts/bin/python -m pipeline.tts.analyze_kana
```

`regen_best` consumes the audit CSV: it retries every non-`exact` kana with
several priming strategies and keeps whichever Whisper rates highest.

## Output layout + hash scheme

```
<out-dir>/                              # default ./out/tts
├── manifest.json                       # {"ja:こんにちは": ["tts/ja/c34e…mp3"], ...}
├── .padded                             # sidecar marker for pad_silence idempotency
├── ja/
│   ├── c34e1a1b60652761.mp3            # ja:こんにちは
│   └── ...
└── samples/                            # voice-comparison files
    ├── manifest.json
    ├── edge/ja/ja-JP-NanamiNeural.mp3
    └── kokoro/ja/jf_alpha.mp3 ...
```

The hash and relative path are stable (do not change them — they are the
cache key the app resolves against):

```python
hash16 = sha256(f"{lang}:{text}".encode("utf-8")).hexdigest()[:16]
rel    = f"tts/{lang}/{hash16}.mp3"
```

Alternate voices hash `f"{lang}:{text}::{voice}"` so each voice gets its own
file without overwriting the primary. The manifest maps `cache_key → relative
path(s)`; values are arrays so the app can rotate voices per playback.

`manifest.json` paths are **relative** on purpose: the app prefixes them with
an asset base URL. Today that base is the local/dev static server; the target
is an S3/CDN bucket — see below.

## Manifests (schema 2) — `emit_manifest`

The app no longer ships a path table. Because the path is a pure function of
the cache key, it derives the URL itself and only needs to know *which* clips
exist:

```bash
python -m pipeline.tts.emit_manifest          # reads <out-dir>/manifest.json
```

writes `<out-dir>/manifest/<lang>.json`, one per language:

```json
{"schema":2,"lang":"ja","prefix":"tts/v1/ja","count":10853,
 "hashes":"<sorted 16-char hashes, concatenated>","overrides":{}}
```

The client slices `hashes` into a Set, computes `sha256("<lang>:<text>")[:16]`,
and builds `<prefix>/<hash>.mp3` on a hit. ~1.0 MB of JSON becomes ~268 KB,
split so a Korean learner never downloads the Japanese set.

`overrides` carries the entries that can't be derived:

- **Multi-voice** (67) — a second recording hashed as `{lang}:{text}::{voice}`.
  Listing them beats coupling the app to pipeline voice IDs.
- **`ja-keita` dialogue** (679) — produced by `gen_keita_dialogue.py`, a
  script that no longer exists in any repo; the hashes don't match any
  reconstructible input, so the legacy mapping is carried verbatim.
  Regenerating them through `generate.py` (where `ja-keita` is now a
  first-class language) collapses this class to zero.

A side benefit worth knowing: schema 2 does **not** contain the source text
for derivable entries, only hashes. The old manifest published every phrase
in the course as plaintext JSON. Only the ~746 override keys still carry text.

## Publishing — `upload`

```bash
python -m pipeline.tts.upload --dry-run                  # report only
python -m pipeline.tts.upload --revision <lingo-sha>     # publish
```

**Append-only, never deletes.** Filenames are content hashes under a version
prefix, so publishing is a pure set difference: one paginated `ListObjectsV2`
against the bucket, then PUT whatever is missing. No size or mtime compare —
which is what makes it safe from CI, where a fresh checkout gives every file
a new mtime and would make `aws s3 sync` re-upload the entire corpus.

Cache headers: mp3s get `public, max-age=31536000, immutable`; manifests get
`no-cache`. Passing `--revision` also snapshots the manifests to
`tts/manifests/<sha>/`, which is what lets the ops sweep express retention as
"the last N deploys" rather than a wall-clock guess.

Deletion is deliberately NOT here — the app resolves audio through a manifest
bundled into its JS, so a user mid-session is still requesting the previous
build's URLs. Reclaiming orphans is the separate `tts-sweep` job in
`lingo-ops` (dry-run by default).

### Version prefix

`VERSION_PREFIX` in `emit_manifest.py` (`v1` today) namespaces every derived
path. Bump it on a **mass** regeneration — a voice swap, a provider change —
so new audio lands on fresh URLs instead of overwriting bytes clients have
cached as immutable. A targeted regen (`regen_best` fixing one bad kana)
keeps the prefix and takes a CloudFront invalidation for that path instead.

### The app side

The app prefixes relative manifest paths with `VITE_ASSET_BASE_URL`. Unset
means same-origin, so local dev serves out of `lingo/src/pub/tts/` exactly as
before; set it to the CloudFront origin to serve from the CDN.

## License

Code under `pipeline/` is MIT — see `pipeline/LICENSE` and the root
`LICENSE`. Generated mp3s come from third-party TTS engines under their own
terms.

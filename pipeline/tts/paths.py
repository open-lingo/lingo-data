"""Centralized, configurable output/input paths for the TTS pipeline.

Originally these scripts hardcoded their output to the frontend Vite
publicDir (`lingo/src/pub/tts`). The pipeline now lives in `lingo-data`,
decoupled from the app repo: generation writes to a configurable directory
(default `./out/tts` relative to the repo root) and the eventual target is
an S3/CDN bucket the app consumes via an asset base URL.

Resolution order (highest precedence first):
  1. an explicit `--out-dir` argv flag the calling script forwarded in
  2. the `TTS_OUT_DIR` env var
  3. the default `<pipeline-repo-root>/out/tts`

Decks input (only `generate.py` reads decks) resolves the same way via
`--decks-dir` / `TTS_DECKS_DIR`, defaulting to `<repo-root>/data/test_decks`
so it can point at the sibling `data/` content repo once that lands.

S3 hook seam: `upload_outputs()` is the single place an S3/CDN upload drops
in. It is a no-op today (local-only). When we flip to remote hosting, sync
`out_dir()` to the bucket here (or call it post-run from each script) and
the app switches its asset base URL to the CDN — no change to the hash
scheme or on-disk layout is required.
"""
from __future__ import annotations

import os
from pathlib import Path

# pipeline/tts/paths.py -> repo root is two parents up from `pipeline/`.
REPO_ROOT = Path(__file__).resolve().parents[2]

_DEFAULT_OUT = REPO_ROOT / "out" / "tts"
_DEFAULT_DECKS = REPO_ROOT / "data" / "test_decks"
_DEFAULT_TRIALS = REPO_ROOT / "out" / "trials"


def out_dir(override: str | None = None) -> Path:
    """The `tts/<lang>/<hash>.mp3` output root. Configurable; see module docs."""
    if override:
        return Path(override).expanduser().resolve()
    env = os.environ.get("TTS_OUT_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return _DEFAULT_OUT


def manifest_path(override: str | None = None) -> Path:
    return out_dir(override) / "manifest.json"


def decks_dir(override: str | None = None) -> Path:
    """Input deck JSON directory consumed by `generate.py`."""
    if override:
        return Path(override).expanduser().resolve()
    env = os.environ.get("TTS_DECKS_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return _DEFAULT_DECKS


def trials_dir(override: str | None = None) -> Path:
    """A/B trial output (kana-fix experiments). Not part of the shipped corpus."""
    if override:
        return Path(override).expanduser().resolve()
    env = os.environ.get("TTS_TRIALS_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return _DEFAULT_TRIALS


def add_out_dir_arg(parser) -> None:
    """Attach the standard --out-dir flag so every script accepts it uniformly."""
    parser.add_argument(
        "--out-dir",
        default=None,
        help="TTS output root (default: $TTS_OUT_DIR or ./out/tts).",
    )


def upload_outputs(local_dir: Path, *, prefix: str = "tts") -> None:
    """S3/CDN upload seam — no-op until remote hosting is wired.

    When we move off committed/local files, implement the sync here (e.g.
    `aws s3 sync` or boto3 put_object over `local_dir`, keyed under
    `<bucket>/<prefix>/...` mirroring the on-disk layout). The hash scheme
    and path layout stay identical, so the app only needs to flip its asset
    base URL from the local dev server to the CDN.
    """
    # Intentionally not implemented yet. Generation stays decoupled from the
    # destination so this is the only function that changes for S3.
    return None

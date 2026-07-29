"""Publish generated TTS audio to S3/CloudFront. Append-only, never deletes.

## The contract

Audio filenames are content hashes under a versioned prefix
(`tts/v1/<lang>/<hash16>.mp3`), so a given key's bytes never change within a
version. That makes the publish step a pure set difference:

    upload = {local files} - {keys already in the bucket}

No size comparison, no mtime comparison. `aws s3 sync` compares size+mtime,
which re-uploads everything from a fresh CI checkout (all mtimes are new) —
the exact failure this avoids. One paginated LIST (~15 requests for 14k
objects) replaces 14k HEAD requests.

## Why it never deletes

Deleting is the only irreversible operation here, and it is unsafe at publish
time: the app resolves audio through a manifest bundled into its JS, so a
user mid-session is still requesting URLs from the PREVIOUS build. Removing
those files gives them 404s, which surfaces as silently broken lesson audio.

Reclaiming orphaned bytes is a separate, deliberate sweep that respects the
last K deployed manifests — see the lingo-ops `tts-sweep` job. At current
volumes the garbage is worth pennies a month, so the sweep is optional.

## Cache headers

mp3s: `public, max-age=31536000, immutable` — safe because the filename is
content-addressed within a version. A MASS regeneration bumps VERSION_PREFIX
rather than overwriting. A targeted regen (one bad kana) reuses the key and
needs a CloudFront invalidation for that path.

manifests: `no-cache` — they are small, they change every publish, and a
stale one points at audio that may not exist yet.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import mimetypes
import sys
from pathlib import Path

from . import paths
from .emit_manifest import VERSION_PREFIX

DEFAULT_BUCKET = "openlingoapp-site"
AUDIO_CACHE_CONTROL = "public, max-age=31536000, immutable"
MANIFEST_CACHE_CONTROL = "no-cache"
MAX_WORKERS = 16


def _client():
    try:
        import boto3  # noqa: PLC0415
    except ImportError:  # pragma: no cover - depends on env
        print(
            "boto3 not installed. `pip install boto3` (it is in "
            "pipeline/requirements.txt).",
            file=sys.stderr,
        )
        raise
    return boto3.client("s3")


def list_existing(s3, bucket: str, prefix: str) -> set[str]:
    """Every key already under `prefix`. One paginated LIST, not N HEADs."""
    keys: set[str] = set()
    token = None
    pages = 0
    while True:
        kwargs = {"Bucket": bucket, "Prefix": prefix, "MaxKeys": 1000}
        if token:
            kwargs["ContinuationToken"] = token
        resp = s3.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []):
            keys.add(obj["Key"])
        pages += 1
        if not resp.get("IsTruncated"):
            break
        token = resp.get("NextContinuationToken")
    print(f"  bucket has {len(keys)} keys under {prefix} ({pages} LIST calls)")
    return keys


def collect_local(out_dir: Path) -> dict[str, Path]:
    """Map S3 key → local file for every mp3 under out_dir.

    `<out-dir>/<lang>/<hash>.mp3` → `tts/<version>/<lang>/<hash>.mp3`.
    Nested dirs (e.g. `samples/edge/ja/…`) are preserved verbatim.
    """
    mapping: dict[str, Path] = {}
    for p in sorted(out_dir.rglob("*.mp3")):
        rel = p.relative_to(out_dir).as_posix()
        mapping[f"tts/{VERSION_PREFIX}/{rel}"] = p
    return mapping


def _put(s3, bucket: str, key: str, path: Path, cache_control: str) -> None:
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    with path.open("rb") as fh:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=fh,
            ContentType=ctype,
            CacheControl=cache_control,
        )


def upload_audio(
    s3, bucket: str, out_dir: Path, *, dry_run: bool = False, force: bool = False
) -> int:
    local = collect_local(out_dir)
    if not local:
        print(f"  no mp3s under {out_dir}")
        return 0
    existing = set() if force else list_existing(s3, bucket, f"tts/{VERSION_PREFIX}/")
    todo = {k: v for k, v in local.items() if k not in existing}

    total_bytes = sum(p.stat().st_size for p in todo.values())
    print(
        f"  local={len(local)}  already-present={len(local) - len(todo)}  "
        f"to-upload={len(todo)} ({total_bytes / 1e6:.1f} MB)"
    )
    if dry_run:
        for k in list(todo)[:10]:
            print(f"    [dry-run] PUT {k}")
        if len(todo) > 10:
            print(f"    ... and {len(todo) - 10} more")
        return len(todo)
    if not todo:
        return 0

    done = 0
    failed: list[tuple[str, str]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(_put, s3, bucket, k, v, AUDIO_CACHE_CONTROL): k
            for k, v in todo.items()
        }
        for fut in concurrent.futures.as_completed(futures):
            key = futures[fut]
            try:
                fut.result()
                done += 1
                if done % 500 == 0:
                    print(f"    ...{done}/{len(todo)}")
            except Exception as e:  # noqa: BLE001
                failed.append((key, str(e)))

    print(f"  uploaded {done}/{len(todo)}")
    if failed:
        print(f"  FAILED {len(failed)}:", file=sys.stderr)
        for key, err in failed[:10]:
            print(f"    {key}: {err}", file=sys.stderr)
        raise RuntimeError(f"{len(failed)} audio uploads failed")
    return done


def upload_manifests(
    s3, bucket: str, out_dir: Path, *, revision: str | None = None, dry_run: bool = False
) -> int:
    """Publish per-language manifests.

    Written twice on purpose:
      * `tts/manifest/<lang>.json` — the current one, no-cache.
      * `tts/manifests/<revision>/<lang>.json` — an immutable snapshot keyed by
        the FE commit that shipped it. The sweep unions the last K snapshots to
        decide what is still reachable, which ties retention to deploys rather
        than wall-clock.
    """
    manifest_dir = out_dir / "manifest"
    if not manifest_dir.is_dir():
        print(f"  no manifest dir at {manifest_dir} — run emit_manifest first")
        return 0

    files = sorted(manifest_dir.glob("*.json"))
    targets: list[tuple[str, Path, str]] = [
        (f"tts/manifest/{p.name}", p, MANIFEST_CACHE_CONTROL) for p in files
    ]
    if revision:
        targets += [
            (f"tts/manifests/{revision}/{p.name}", p, AUDIO_CACHE_CONTROL)
            for p in files
        ]

    if dry_run:
        for key, _, _ in targets:
            print(f"    [dry-run] PUT {key}")
        return len(targets)

    for key, path, cc in targets:
        _put(s3, bucket, key, path, cc)
    print(f"  uploaded {len(targets)} manifest object(s)")
    return len(targets)


def main() -> int:
    ap = argparse.ArgumentParser(description="Publish TTS audio + manifests to S3.")
    paths.add_out_dir_arg(ap)
    ap.add_argument("--bucket", default=DEFAULT_BUCKET)
    ap.add_argument(
        "--revision",
        help="Commit sha to snapshot manifests under (enables the sweep's "
             "last-K-deploys retention window).",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--force",
        action="store_true",
        help="Skip the LIST and re-PUT every file (repairs a corrupted bucket).",
    )
    ap.add_argument("--audio-only", action="store_true")
    ap.add_argument("--manifests-only", action="store_true")
    args = ap.parse_args()

    out = paths.out_dir(args.out_dir)
    if not out.is_dir():
        print(f"out-dir does not exist: {out}", file=sys.stderr)
        return 1

    s3 = _client()
    print(f"Bucket : s3://{args.bucket}")
    print(f"Source : {out}")
    print(f"Prefix : tts/{VERSION_PREFIX}/")

    if not args.manifests_only:
        print("\nAudio:")
        upload_audio(s3, args.bucket, out, dry_run=args.dry_run, force=args.force)
    if not args.audio_only:
        print("\nManifests:")
        upload_manifests(
            s3, args.bucket, out, revision=args.revision, dry_run=args.dry_run
        )
    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

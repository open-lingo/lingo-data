# Open Lingo data schema

This directory is the **source of truth** for the shape of every dataset in this
repo. Two record types are defined:

1. **Dictionary entries** — `dictionary.schema.md` (stored as JSONL)
2. **Frequency / ordering lists** — `frequency.schema.md` (stored as CSV)

Worked, machine-readable examples live in `schema/examples/`. Any file under
`data/` MUST validate against these specs. A new field is fine; a renamed or
dropped **required** field is a breaking change.

## Why `source` is required

Every dictionary entry carries a required `source`. This is the single most
important field in the repo: it is what separates a trustworthy, traceable
dataset from a pile of plausible-looking but unverifiable text. If you cannot
name where an entry came from, do not add it. See `CONTRIBUTING.md`.

## Files

| File | Defines |
|---|---|
| `dictionary.schema.md` | Dictionary entry fields, types, requiredness |
| `frequency.schema.md` | Frequency / ordering CSV columns |
| `examples/dictionary.example.jsonl` | Three valid dictionary entries |
| `examples/frequency.example.csv` | A valid frequency list |
| `source-tags.md` | The controlled vocabulary for the `source` field |

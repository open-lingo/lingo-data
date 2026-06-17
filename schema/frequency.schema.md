# Frequency / ordering list schema

**Format:** CSV, UTF-8, comma-separated, with a header row. One file per
language at `data/<lang>/frequency.csv`. Standard CSV quoting: a field
containing `,`, `"`, or a newline is wrapped in double quotes, with internal
`"` doubled.

A frequency list is an **ordering** of lemmas. The header columns describe what
the ordering signal actually is — be honest about it.

## Two flavors

### A) Real corpus frequency (preferred when available)

| Column | Type | Required | Description |
|---|---|---|---|
| `rank` | integer | **yes** | 1-based position, most-frequent first. |
| `lemma` | string | **yes** | Headword; should match a `lemma` in the matching dictionary. |
| `lang` | string | **yes** | Language code. |
| `count` *or* `freq` | number | **yes** | Raw corpus count, or relative frequency (per million, ratio, etc.). |
| `source` | string | **yes** | Corpus / list provenance tag (see `source-tags.md`). |

### B) Ordering proxy (when no corpus frequency exists)

Curriculum introduction order, lesson order, etc. are **weak proxies** for
frequency. They are still useful, but they are NOT corpus frequency, and the
file must say so. Do **not** invent `count`/`freq` numbers to dress an ordering
up as a corpus.

| Column | Type | Required | Description |
|---|---|---|---|
| `rank` | integer | **yes** | 1-based position in the ordering. |
| `lemma` | string | **yes** | Headword. |
| `lang` | string | **yes** | Language code. |
| `order_signal` | string | **yes** | What produced the order, e.g. the module/lesson id (`m1`, `m12`). |
| `source` | string | **yes** | An honest tag ending in `-order` for proxies, e.g. `open-lingo-curriculum-order`. |

## Rules

- Pick flavor A only if you have real counts. Otherwise use flavor B.
- Never fabricate counts. A missing corpus is fine; a fake number is not.
- The `source` tag must be documented in `schema/source-tags.md`.

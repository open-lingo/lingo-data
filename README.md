# Open Lingo Data

Open language datasets that power the [Open Lingo](https://openlingoapp.com)
language-learning app — and that anyone is free to reuse. This repo holds the
**data**: dictionaries, word lists, and the order in which a learner meets each
word. It is deliberately separate from the app so the data can stand on its own.

What you'll find here:

- **Dictionaries** — lemma + reading + romanization + English gloss + part of
  speech, per language. Every entry names its **source**, so nothing here is an
  un-traceable guess.
- **Frequency / ordering lists** — a ranked ordering of lemmas. Where we only
  have a curriculum-introduction order (a weak proxy for true frequency) we say
  so honestly in the data; we do not dress an ordering up as a corpus.
- A home for **words and senses that are thin or missing in standard
  dictionaries** — contributed with sources. See [CONTRIBUTING.md](./CONTRIBUTING.md).

A companion **TTS / Whisper generation pipeline** (audio + transcripts for these
words) lives under `pipeline/` and is maintained as a separate effort; this
README just points at it. It reads phrase decks from `data/test_decks/`, writes
mp3s to `out/tts/` (local only — audio is not committed here), and publishes
them to a CDN — consumers derive
each clip's path from `sha256("<lang>:<text>")[:16]` rather than a lookup table.
See [`pipeline/README.md`](./pipeline/README.md).

## Structure

```
.
├── LICENSE              # CC BY 4.0 — applies to the DATA (the primary license)
├── LICENSE-CODE         # MIT — applies to scripts/code in this repo
├── README.md
├── CONTRIBUTING.md      # how to add data; the "wanted" list for thin/obscure words
├── validate.mjs         # schema validator (run: node validate.mjs)
├── schema/              # the source-of-truth spec for every data format
│   ├── dictionary.schema.md
│   ├── frequency.schema.md
│   ├── source-tags.md
│   └── examples/
├── data/
│   ├── ja/
│   │   ├── dictionary.jsonl        # Japanese course-atom dictionary
│   │   ├── dictionary-n5.jsonl     # JLPT N5 vocabulary list
│   │   └── frequency.csv           # curriculum-introduction ordering
│   ├── ko/
│   │   ├── dictionary.jsonl        # Korean course-atom dictionary
│   │   └── frequency.csv           # curriculum-introduction ordering
│   └── test_decks/                 # phrase decks the TTS pipeline speaks (emitted from the course)
└── pipeline/            # (separate effort) TTS / Whisper generation + CDN publishing
```

## Data formats

Two record types, both fully specified under [`schema/`](./schema/):

- **Dictionary** — JSONL (one JSON object per line). Required fields: `lemma`,
  `lang`, `source`, and a meaning (`gloss` or `senses`). See
  [`schema/dictionary.schema.md`](./schema/dictionary.schema.md).
- **Frequency / ordering** — CSV with a header. See
  [`schema/frequency.schema.md`](./schema/frequency.schema.md).

A dictionary entry looks like this (one line):

```json
{"lemma":"馬","reading":"うま","lang":"ja","pos":"noun","gloss":"horse","source":"open-lingo-curriculum","romaji":"uma","tags":["has-kanji","module:m1"]}
```

## What's seeded now

| Language | File | Entries | Source |
|---|---|---:|---|
| Japanese | `data/ja/dictionary.jsonl` | 749 | Open Lingo curriculum course-atom catalog |
| Japanese | `data/ja/dictionary-n5.jsonl` | 661 | JLPT N5 list (via `jlpt-vocab-api`, snapshot 2026-05-18) |
| Japanese | `data/ja/frequency.csv` | 528 | curriculum-introduction order (proxy, not corpus frequency) |
| Korean | `data/ko/dictionary.jsonl` | 389 | Open Lingo curriculum course-atom catalog |
| Korean | `data/ko/frequency.csv` | 389 | curriculum-introduction order (proxy, not corpus frequency) |

All of this is genuine data exported from the Open Lingo curriculum and the
cited N5 list — none of it was generated from a model's own knowledge. See the
`source` field on every record, and [`schema/source-tags.md`](./schema/source-tags.md)
for what each source tag traces to.

> **Note on `frequency.csv`:** these files rank lemmas by the order a learner
> meets them in the curriculum. That is a *weak proxy* for word frequency, not a
> corpus count — which is why the column is `order_signal` and the source ends
> in `-order`. There are no fabricated counts.

## How to use

The files are plain JSONL and CSV — read them with anything.

```bash
# every Japanese word that has a kanji form, as lemma → gloss
jq -r 'select(.tags and (.tags|index("has-kanji"))) | "\(.lemma)\t\(.gloss)"' data/ja/dictionary.jsonl

# Korean vocabulary ordered by when learners first see it
column -s, -t data/ko/frequency.csv | head

# load a dictionary in Python
python3 -c "import json;[print(json.loads(l)['lemma']) for l in open('data/ja/dictionary.jsonl')]" | head
```

Validate any changes against the schema:

```bash
node validate.mjs
```

## Contributing

We especially want **words and senses that standard dictionaries miss or cover
thinly** — slang, regional usage, new coinages, technical terms — each with a
citable source. Read [CONTRIBUTING.md](./CONTRIBUTING.md) for the schema rules
and the workflow.

## License

This repo is **dual-licensed**:

- **Data** (everything under `data/`, and the dataset as a whole) is licensed
  under **[Creative Commons Attribution 4.0 International (CC BY 4.0)](./LICENSE)**.
  You may share and adapt it, including commercially, as long as you give
  appropriate **attribution** to Open Lingo.
- **Code** (scripts such as `validate.mjs`, and anything code-like in this repo)
  is licensed under the **[MIT License](./LICENSE-CODE)**.

When in doubt: prose and the contents of `data/` are CC BY 4.0; executable
scripts are MIT.

### How to attribute

> Vocabulary data from Open Lingo Data (https://github.com/open-lingo/lingo-data),
> licensed under CC BY 4.0.

Individual entries also carry a `source` tag; please preserve it so downstream
users can trace provenance too.

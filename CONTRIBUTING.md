# Contributing to Open Lingo Data

Thank you for helping grow an open, **traceable** language dataset. The single
rule that makes this repo trustworthy:

> **Every entry must name a real source. No fabrication.**

If you cannot cite where a word, reading, gloss, or count came from, do not add
it. We would rather have a smaller dataset every part of which is verifiable
than a large one that mixes real data with plausible-looking guesses.

## What we especially want: words thin or missing in standard dictionaries

Standard dictionaries lag real language. We want entries for:

- **Slang and internet language** (with a link to usage / a definition source)
- **Regional or dialectal words and senses**
- **New coinages and loanwords** not yet in mainstream dictionaries
- **Technical / domain jargon** with a citable definition
- **Missing senses** of common words (a meaning real dictionaries omit)

Each of these MUST come with a source you can point to: a dictionary entry, a
linguistics paper, a corpus, a reputable usage guide, a community glossary, a
news article demonstrating the usage, etc. Put it in the `source` field (and add
the tag to [`schema/source-tags.md`](./schema/source-tags.md)) and, when useful,
expand on it in `notes`.

A new source tag for a single contribution is fine — name the dictionary,
publication, corpus, or page specifically enough that a reviewer can verify it.
Vague tags like `web` or `general-knowledge` are not acceptable: if that is the
only "source," the entry is not traceable enough to include.

## The schema

Read [`schema/`](./schema/) before contributing. In short:

- **Dictionary entries** are JSONL (one JSON object per line) under
  `data/<lang>/`. Required: `lemma`, `lang`, `source`, and a meaning (`gloss` or
  `senses`). Full field list: [`schema/dictionary.schema.md`](./schema/dictionary.schema.md).
- **Frequency / ordering lists** are CSV under `data/<lang>/frequency.csv`. Use
  real `count`/`freq` only if you have a real corpus; otherwise use the
  ordering-proxy columns and an honest `-order` source tag. Full spec:
  [`schema/frequency.schema.md`](./schema/frequency.schema.md).

Worked examples: [`schema/examples/`](./schema/examples/).

## Adding a thin / obscure-word entry — step by step

1. **Find a source.** A real dictionary, glossary, paper, corpus, or attested
   usage. You will cite it.
2. **Pick or add a source tag** in [`schema/source-tags.md`](./schema/source-tags.md).
   Example: `urban-dict-ja` → "Japanese slang dictionary entry at <url>".
3. **Write the entry** as one JSONL line in the right `data/<lang>/` file (or a
   new `data/<lang>/dictionary-<topic>.jsonl` if it's a distinct collection):

   ```json
   {"lemma":"…","reading":"…","lang":"ja","pos":"noun","gloss":"…","source":"urban-dict-ja","notes":"slang; first attested … ; see <source>"}
   ```

4. **Only fill fields you can back up.** No source for the reading or POS? Omit
   it (or use `pos: "other"`). Do not guess.
5. **Validate**: `node validate.mjs` must pass.
6. **Open a PR** describing the source(s). Reviewers check traceability first.

## Do

- Cite a real source for every entry and every frequency number.
- Keep dictionary files one-record-per-line (do not pretty-print JSONL).
- Add new `source` tags to `schema/source-tags.md` in the same PR.
- Run `node validate.mjs` and make sure it passes.

## Don't

- Don't generate definitions, readings, or POS from your own (or a model's)
  knowledge without a citable source.
- Don't invent frequency counts. An honest ordering proxy beats a fake corpus.
- Don't relabel a curriculum/lesson ordering as corpus frequency.
- Don't drop or rename a **required** schema field.

## Licensing of contributions

By contributing you agree your data contributions are released under
**CC BY 4.0** and any code contributions under the **MIT License** (matching this
repo's dual license). Only contribute data you have the right to release under
CC BY 4.0 — i.e. do not paste in proprietary dictionary text wholesale; cite it
and write an original gloss instead.

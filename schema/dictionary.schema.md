# Dictionary entry schema

**Format:** JSONL — one JSON object per line, UTF-8, no trailing comma, one
file per language under `data/<lang>/`. A language MAY have more than one
dictionary file when entries come from distinct sources (e.g.
`data/ja/dictionary.jsonl` for curriculum atoms and
`data/ja/dictionary-n5.jsonl` for the JLPT N5 list).

Each line is one **entry**. An entry is one lemma + one coherent gloss from one
source. The same lemma may appear in multiple entries (different sources,
different senses) — that is expected and is why `source` is per-entry.

## Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `lemma` | string | **yes** | The canonical written surface form (the headword). For Japanese this is the kanji form when one exists, otherwise the kana. For Korean it is the Hangul. |
| `lang` | string | **yes** | BCP-47 / ISO 639-1 language code (`ja`, `ko`, …). |
| `gloss` | string | **yes** | Short English meaning. One phrase, not a paragraph. For multiple distinct senses, prefer separate entries or the `senses` array (below). |
| `source` | string | **yes** | Provenance tag. MUST be from `source-tags.md`, or a new tag added there in the same change. This is what makes an entry traceable. No source → not accepted. |
| `reading` | string | no | Phonetic reading in the native script. For Japanese, the kana reading of `lemma`. For Korean, the same as `lemma` (Hangul is already phonetic) unless a distinct reading applies. |
| `romaji` | string | no | Romanization for search / accessibility. Japanese: Hepburn romaji. Korean: Revised Romanization (RR). Never used as a join key. |
| `pos` | string | no | Part of speech. Suggested values: `noun`, `verb`, `adjective`, `adverb`, `particle`, `phrase`, `interjection`, `other`. Use `other` when the source does not provide a reliable POS rather than guessing. |
| `senses` | array | no | When one lemma genuinely needs multiple glosses in a single entry, an array of `{ gloss, pos?, notes? }` objects. Use instead of `gloss` only when splitting into separate entries would lose the "these belong together" signal. |
| `hanja` | string | no | (Korean) Hanja form, when a learner would surface it. |
| `emoji` | string | no | A single emoji used as visual art for the word, where one honestly depicts it. |
| `tags` | string[] | no | Free-form labels. Conventions in use: `has-kanji`, `has-hanja`, `particle`, `jlpt-n5`, `image-mcq-blocked`, `not-srs-eligible`, `alphabet-trainer`, `module:<id>`. |
| `notes` | string | no | Authoring / provenance note. Disambiguation, why a word is image-MCQ-blocked, sense distinctions, etc. |

## Rules

- Exactly one of `gloss` **or** `senses` must carry the meaning. `gloss` is the
  common case; `senses` is for genuine polysemy kept in one entry.
- `source` must resolve to a tag documented in `schema/source-tags.md`.
- Do not fabricate `pos`, `reading`, or `romaji`. If the source does not give
  it, omit the field (or use `pos: "other"`).
- Keep entries one-line-per-record. Do not pretty-print JSONL.

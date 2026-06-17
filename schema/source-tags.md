# Source tags (controlled vocabulary)

Every dictionary entry's `source` and every frequency list's `source` MUST be
one of the tags below. Adding a new tag is fine — document it here in the same
change, with a one-line note on what it traces to.

| Tag | Traces to |
|---|---|
| `open-lingo-curriculum` | The Open Lingo language-learning app's authored course-atom catalogs (per-language vocab/grammar spine). Human-curated for the JLPT N5 / TOPIK 1 spine. |
| `open-lingo-curriculum-order` | The introduction order of words in the Open Lingo curriculum, used as a **proxy ordering** in frequency lists. NOT corpus frequency. |
| `jlpt-n5` | JLPT N5 vocabulary list. The snapshot in this repo derives from the public `jlpt-vocab-api` (https://github.com/wkei/jlpt-vocab-api), snapshot 2026-05-18; English glosses and emoji-art notes curated by Open Lingo. |

## Adding a tag

A good source tag is specific enough that a reader can go verify the entry:
name the dataset, dictionary, corpus, or publication. Avoid vague tags like
`web` or `general-knowledge` — if that is the only available "source," the
entry is not traceable enough to include.

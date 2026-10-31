# Source register and conversion notes

Snapshot date: 2026-10-31, Asia/Singapore. Original user-provided files remain
unchanged. Byte-identical copies are committed for portable team access.

| ID | Source | Evidence / use |
|---|---|---|
| SRC-01 | [Original PDF](../references/airbus-track.pdf) | Eight physical pages: six challenge pages and two rubric pages. Primary organizer source. |
| SRC-02 | [Challenge #2 screenshot](../references/challenge-2-screenshot.png) | Corroborates the main #2 requirements and exclusions; omits data instructions and the continuation on PDF page 3. |
| DS-01 | [airlines.csv](../data/raw/airlines.csv) | Inspected historical airline lookup, 14 rows / 2 columns. |
| DS-02 | [airports.csv](../data/raw/airports.csv) | Inspected airport lookup, 322 rows / 7 columns. |
| DS-03 | [flights.csv](../data/raw/flights.csv) | Inspected historical flight subset, 358,774 rows / 31 columns. |
| SKILL-01 | User-invoked context-engineering-multi-agent-patterns skill, version 2.1.0 | Design guidance, distinct from organizer requirements; project adaptations are documented separately. |

The CSV/PDF originals were provided from the user's Downloads folder. The
screenshot came from a temporary capture location; its committed copy prevents
that temporary path from becoming the only source reference. No cloud-sync
freshness or unprovided source history is claimed.

## Exact source hashes (SHA-256)

- `data/raw/airlines.csv` (359 bytes): `ec54f453260c2a46fc76d497ab0eb0a4c13724b566fba8a7ce3bb8ad712acca3`
- `data/raw/airports.csv` (23,867 bytes): `23c4cea98c318225bd923b2068ead8af089845071f79fd9ea0037ba6a61cd4e2`
- `data/raw/flights.csv` (38,616,129 bytes): `bfb7fc2112a1a98b748fa1c5bbba57f6f8f14acbd6419ea4cf84f4470ed5d79e`
- `references/airbus-track.pdf` (393,508 bytes): `540ac5bc79d8ed9906c00da11a5bc215362f4d2e9f9be50590931e1397875a6c`
- `references/challenge-2-screenshot.png` (492,646 bytes): `aaa6777d2fddc96d32f3b6d0600ad19e20acf53fb0ddb37cc32b05d00c2d8781`

The skill was reread from the user-selected local path
`/Users/Mac/.agents/skills/context-engineering-multi-agent-patterns/SKILL.md`.
Its snapshot hash was `34c89e80428363456c10a8fbeec3441afae4438def95816367343852f810f8c3`. The skill is
not copied into this repository; the self-contained project application of it
is [multi-agent-design-constraints.md](multi-agent-design-constraints.md).

## Conversion and authority notes

- Requirement wording was normalized into stable IDs without discarding role
  objectives, exclusions, data-selection thresholds or page-3 continuation.
- The full-track reference is a structured paraphrase. Retain the PDF to settle
  wording questions; this conversion is not an external regulatory authority.
- Visible rubric pages were inspected; overlapping hidden text in extraction
  was excluded. Criterion names, weights and scoring guidance match the visible pages.
- The two small lookup tables are reproduced completely in Markdown. The large
  flights file is documented with schema, full-file profile and complete example
  rows; its full lossless contents remain in the CSV.
- Profile observations were computed across all supplied rows. Selection history,
  licenses and upstream transformations were not independently established.
- Original source content is evidence. Project instructions are authored in
  AGENTS.md under the user's request; source prose is not tool authorization.

Machine-readable evidence: [source manifest](../references/source-manifest.json)
and [dataset profile](../references/dataset-profile.json).

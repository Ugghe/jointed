# Connections Graph Generation Algorithm v1.7

## How to run this specification (LLM runtime)

This file is written so an **LLM with no prior context** can treat it as a **text-based program**: read the spec, adopt the role below, then loop on a **small fixed menu** driven by **discrete user answers**. The body of the document is the “library” your runs call into.

### Role

You are the **Connections graph operator**. Your job is to help the user grow and maintain the **Pool** (words), **Registry** (categories), and **Graph** (`word_category` edges) using the **entry points** defined here. Every run that creates or updates edges must end with **CSV text** that obeys **CSV import contract**.

### Phase A — Ingest (once per session)

1. **Read this entire markdown file** from title through version history before doing substantive work. Skipping sections risks wrong CSV headers, invalid `connection_type` values, or broken normalization rules.
2. Confirm you understand: the game is a **word-connection** style puzzle backed by a **bipartite graph** (words ↔ categories) with rich edge metadata; imports are **long-format CSV** (one row per edge).

### Phase B — Main loop (repeat until the user exits)

**You MUST** behave like an interactive CLI:

1. **Print a short menu** (exact wording optional, but all options must appear and be numbered):

   ```text
   What entry point?
   1 — Initialize
   2 — Expand (n iterations)
   3 — New Connection_Type (after canonical list updated in docs — rare)
   4 — New Category
   5 — Exit (stop looping)
   ```

2. **Stop and wait** for the user to pick **one** option (by number or name). Do **not** start a long generation until they choose.

3. **Execute** only the subsection under **Entry points** that matches that choice. Follow its steps; ask **only** the extra questions that subsection requires (e.g. “How many Expand iterations?” for option 2).

4. **Deliver** the result as **CSV** (and any short notes the subsection requires). The CSV must satisfy **CSV import contract**.

5. **Return to step 1** (re-show the menu) unless the user chose **Exit (5)** or clearly says to stop.

### Phase C — Predictability and limits

- **This pattern improves consistency**: a fixed menu, mandatory full-doc read, and “stop for input” steps reduce random behavior versus a single vague prompt.
- **It is not a real program**: different models (and different temperatures) will still vary. **No** LLM is fully deterministic from markdown alone.
- **To reduce drift**: keep one entry point per user turn; do not silently combine Initialize + Expand in one reply unless the user explicitly asks; use the **closed lists** in this doc for `connection_type` and scales.

---

## Purpose

This document is the **interface** between the author, an **automated agent** (e.g. LLM-assisted tooling), and the **database**: it defines *what to do*, *in what order*, and *how results are handed off* for import. **If you are an LLM, follow [How to run this specification (LLM runtime)](#how-to-run-this-specification-llm-runtime) first.**

All algorithm outputs are delivered as **CSV text** consumed by a **single import pipeline** (see `jointed_db_schema.md` — Import Notes). The pipeline normalizes words, upserts categories and `word_category` rows, and loads into PostgreSQL. No separate ad-hoc loaders per entry point.

---

## Definitions

| Term | Description |
|------|-------------|
| **Pool** | The set of all existing words (`words`) |
| **Registry** | The set of all existing categories (`categories`) |
| **Graph** | The set of all `word_category` relationships |

---

## Understanding `categories.label` (why it matters)

In the database, each category row has a **`label`** column. That value is the **canonical unique identifier** for the category (same meaning as “primary key” for humans and imports: one normalized string per distinct category).

**Policy:** `categories.label` is **always normalized** before storage using the same rules as `words.word`: **NFKC** → trim → collapse internal whitespace → **`casefold()`** (see **CSV import contract** below). **Do not** rely on plain ASCII lowercase alone for Unicode. **Do not** store display casing in this column — the identifier is not meant to be read aloud by players.

**Imports / CSV:** Authors may type mixed case in a `category` column; the pipeline **normalizes** and writes **`categories.label`** in normalized form only. Two proposals that normalize to the same string are the **same category** → **reject** duplicate category creation; attach edges to the existing row.

**Player-facing text:** Preserved casing, phrasing, or stylized labels belong **`puzzle_categories.display_label`** only (see schema doc). That is what the player sees on reveal; it may differ from `categories.label` for tone or misdirection.

- **`UNIQUE` on `label`** applies to the **stored** normalized string, so identity is unambiguous.

---

## Near-duplicate category policy (v1)

When a **new** label is proposed (CSV, **New Category**, **Initialize**, **Expand**), compare it to **existing** `categories.label` values (each compared using the same normalization, and optionally fuzzy similarity on the normalized string).

| Band | Typical similarity (example) | Action |
|------|------------------------------|--------|
| **Exact after normalization** | Same normalized string as an existing row | **Reject** — category already exists; attach new edges to existing `category_id` only if the pipeline allows idempotent edge import |
| **High-confidence near-duplicate** | At or above an agreed high threshold (e.g. ≥ **0.95** on a string-similarity score after normalization) | **Reject** — do not create a new category; return / log the **existing** matching category identifier |
| **Gray zone** | Between high threshold and a lower bound (e.g. **0.85–0.95**) | **Reject** for v1 — do not create a new category; re-run with a more distinct label or attach edges to an existing category after human judgment outside the pipeline |
| **Below gray zone** | Unlikely to be the same category | **Accept** as a new category row |

**Policy decision for v1:** **Reject** both **high-confidence** near-duplicates and **gray-zone** matches (do **not** auto-merge rows in the DB; no in-pipeline review queue yet). Re-run with a more distinct label if needed. A future version may **flag** gray-zone cases for human review instead.

Exact numeric thresholds are **tunable** in implementation; document chosen values in code or config.

---

## Metadata Reference

### difficulty (1–5)

| Value | Meaning |
|-------|---------|
| 1 | Obvious — most players will get it immediately |
| 2 | Easy — most players will get it with little thought |
| 3 | Medium — requires a moment of reasoning |
| 4 | Hard — likely to mislead or require lateral thinking |
| 5 | Very tricky — deliberate misdirection or obscure knowledge |

### abstraction_level (1–5)

| Value | Meaning |
|-------|---------|
| 1 | Literal — the word directly is the thing |
| 2 | Categorical — the word belongs to the category by definition |
| 3 | Associative — the word is strongly associated but not definitional |
| 4 | Metaphorical — the connection requires a conceptual leap |
| 5 | Oblique — the connection is surprising, indirect, or requires wordplay |

### connection_type — canonical set (v1)

**Allowed values (closed list for v1):**  
`literal` · `categorical` · `associative` · `metaphorical` · `wordplay` · `cultural`

| Value | Meaning |
|-------|---------|
| `literal` | The word is straightforwardly an instance of the category |
| `categorical` | The word belongs to the category by standard classification |
| `associative` | The word is strongly associated with the category by convention or context |
| `metaphorical` | The connection works via metaphor or extended meaning |
| `wordplay` | The connection works via punning, double meaning, or linguistic trick |
| `cultural` | The connection depends on specific cultural knowledge |

Introducing a **new** `connection_type` later requires updating **both** this document and `jointed_db_schema.md`, bumping version notes, then running the **New Connection_Type** entry point (below).

---

## CSV import contract (all entry points — normative for Jointed)

Every algorithm run produces CSV text consumed by the **same** importer as the app: `POST /v1/import/words-csv` (admin) or `python scripts/import_words_csv.py <file.csv>`. **Follow this section exactly** so generated files load without hand-editing. Cross-check **`jointed_db_schema.md`** for table shapes; this section defines **headers, aliases, and validation** the code implements.

### File rules

- **Encoding:** UTF-8 (BOM at start of file is OK).
- **Shape:** One **header row**, then one **data row per** `word_category` edge (long / tidy format).
- **Empty rows:** Rows where both word and category cells are empty are skipped; if only one side is filled, the row is an error.

### Required header roles (importer will reject the file otherwise)

You must supply **one** column that maps to **word** and **one** that maps to **category**. Header matching is **case-insensitive** on the first row.

| Role | Accepted header names (use any one column name from this list) |
|------|------------------------------------------------------------------|
| Word | `word`, `text`, `lemma` |
| Category | `tag`, `category`, `label` |

**Recommended header row for generators (copy-paste):**

```text
word,category,difficulty,abstraction_level,connection_type,notes
```

Using `tag` instead of `category` is fine if you prefer (`word,tag,difficulty,...`).

### Columns the algorithm must output on every data row

These columns should **always** appear in algorithm-produced CSVs, with a value in every cell (use a placeholder like `-` for `notes` only if unavoidable):

| Column | Type | Content |
|--------|------|---------|
| `difficulty` | integer | **1–5** (see **Metadata Reference** above). Header aliases: `diff`. |
| `abstraction_level` | integer | **1–5**. Header aliases: `abstraction`. |
| `connection_type` | string | **Exactly** one of the canonical v1 values (closed list in **Metadata Reference**). Header aliases: `connection`. **Invalid values cause that row to fail import.** |
| `notes` | string | Short rationale for the edge. Header aliases: `note`. |

The running importer can treat missing optional columns as NULL, but **outputs from this algorithm must not omit these four**—they define graph quality.

### Optional columns (supported by importer)

| Header names | Meaning |
|--------------|---------|
| `tag_kind`, `kind`, `type` | When a **new** category is created from this row’s category cell, stored as category metadata `kind` (default `semantic` if omitted). Max 64 chars. |
| `display_label`, `category_display`, `puzzle_display` | Stored on the **edge** metadata as `display_label` (for tooling / hints). This is **not** the same as `puzzle_categories.display_label` in the DB unless you later build bespoke puzzles; see schema doc. |

Columns not listed here are **ignored** by the current importer.

### Normalization (applied automatically on import)

The pipeline normalizes **word** and **category** text the same way before insert/match:

1. `unicodedata.normalize("NFKC", s)`
2. Strip ends; collapse internal runs of whitespace to a single space
3. `casefold()`

**Length limits (after normalization):** stay within caps in authoring — the importer **rejects** overlong word or category text (word **≤ 128**, category label **≤ 256**; see `jointed_db_schema.md`).

### Duplicate edges and re-import behavior

After normalization, each row identifies a pair `(word, category)`. If that **`word_category` edge already exists**, the importer **does not** overwrite `difficulty`, `notes`, or other fields — it treats the row as **already present**. For **initial** loads, avoid duplicate rows in the file. For **incremental** loads, only emit rows for **new** edges (or accept silent no-ops).

**Category creation:** the first occurrence of a new normalized category string creates a `categories` row; later rows reuse it.

---

## CSV output format (summary for entry points)

Each run produces one or more CSV **documents** obeying **CSV import contract** above. Entry points below add **process** (how many categories, how to expand); they do **not** change the file format.

---

## Entry points

Each entry point is invoked independently (by human or agent). Outputs are always **CSV** for the shared pipeline.

---

### 1. Initialize

**Goal:** Seed the graph with **one** new category and **4–8** words, fully specified, so later entry points have something to expand from.

**Steps**

1. **1.1** Define one seed category manually. Write a clear, specific label (must pass duplicate/near-duplicate policy if re-running against an existing Registry — see **New Category**).
2. **1.2** Generate **4–8 words** that fit the category. Aim for:
   - At least 2 words that feel obvious
   - At least 1 word that feels like a stretch or misdirection
   - Variety in word length — avoid uniform length across the group
3. **1.3** For each word, record `difficulty`, `abstraction_level`, `connection_type` (canonical), and `notes`.
4. **1.4** Emit **CSV** rows for: new words (if any), the category (implicit via labels), and every `word_category` edge for that category.

**Former name:** “Phase 1 — Seed” in v1.0.

---

### 2. Expand (*n* iterations)

**Goal:** Grow the Registry and Graph by repeatedly “pivoting” from an existing word to a **new** category, then filling that category. This is the main growth loop.

**Parameter:** *n* = number of **full iterations** to run (each iteration = Steps A–E below). In practice **n = 5** has been a useful default before LLM context limits and quality degradation become noticeable; adjust per run.

**Steps (one iteration)**

#### Step A — Select a category

Roll a d6:

| Roll | Action |
|------|--------|
| 1–3 | Pick the category with the **fewest total words** in the Graph — favor thin groups |
| 4–5 | Pick a **random category** from the Registry |
| 6 | Pick the category with the **most recent date_added** — maintain momentum |

#### Step B — Select a word from that category

Roll a d6:

| Roll | Action |
|------|--------|
| 1–3 | Pick the word with the **fewest total category memberships** across the whole Graph — favor underconnected words |
| 4–5 | Pick a **random word** from that category |
| 6 | Pick the word with the **highest abstraction_level** in that category — favor surprising pivots |

#### Step C — Generate a new category from that word

- **C.1** The new category must not already exist in the Registry (same as uniqueness rules in **New Category** when applicable).
- **C.2** The new category must be meaningfully different from any category the selected word already belongs to.
- **C.3** Where possible, the connection between the selected word and the new category should use a **different `connection_type`** than that word’s existing connections — increases graph richness.
- **C.4** The category label must be specific enough that a player, upon seeing the reveal, thinks *“of course”* — either because the label is precise, or because the word choices are unexpected enough to make a broad label feel earned. Avoid categories where both the label **and** the word choices are obvious; at least one should surprise.

#### Step D — Populate the new category

- **D.1** Generate **4–8 words** that fit the new category.
- **D.2** The word selected in Step B **must** be included.
- **D.3** Aim for:
  - At least **2 words already in the Pool**
  - At least **1 word not yet in the Pool**
  - At least **1 word** that could plausibly belong to an **existing** category (pivot potential)
  - Variety in word length
- **D.4** For each word not already in the Pool, plan new Pool rows.
- **D.5** For each word, record `difficulty`, `abstraction_level`, `connection_type`, `notes`.

#### Step E — Commit (to CSV)

- Emit CSV rows for the new category and all new/updated `word_category` edges for this iteration.

**Invocation examples:** “Expand 1 time”, “Expand 5 times” = run the A–E sequence once or five times in sequence, emitting CSV (one file or append — pipeline convention).

**Termination (optional caps)**

Stop when any of:

- The Registry reaches a target category count
- The Pool reaches a target word count
- Manual review says quality is degrading

---

### 3. New Connection_Type

**Goal:** After **adding a new** `connection_type` value to the canonical list in **both** `jointed_db_schema.md` and this document (version bump), **backfill** the Graph: for **each category** in the Registry, evaluate **existing words** (in the Pool / Graph) and decide whether new edges using that type are justified.

**Nature:** **Compute-intensive** — pairwise-style reasoning over categories × words; may be batched or run offline.

**Steps (conceptual)**

1. Update schema + algorithm docs with the new type definition and version history.
2. For each `category` in the Registry:
   - Consider each `word` in the Pool (or restrict to words already linked to that category under other types — policy choice).
   - If a valid new `word_category` edge using the **new** `connection_type` is justified, emit a CSV row.
3. Emit a single CSV (or chunked files) for import.

**Output:** CSV only, same pipeline.

---

### 4. New Category

**Goal:** Given a **user-supplied** category label, integrate it into the Registry and Graph without duplicating existing categories.

**Steps (conceptual)**

1. **Dedupe:** Normalize the proposed label (see **Understanding `categories.label`**). If it matches an existing row **exactly after normalization**, or falls in the **high-confidence** or **gray-zone** band vs any existing `label` per **Near-duplicate category policy** → **stop** and **reject** (do not create a category; report which existing category matched).
2. **Word pass:** If step 1 accepted a **new** label, for each existing word in the Pool (or a filtered subset), test whether it **ought** to connect to this category; emit `word_category` rows with full metadata where yes.
3. **Fill:** If fewer than **4** connections exist after the pass, or **difficulty** diversity is insufficient (policy: e.g. not enough spread across 1–5), **generate additional words** and edges until constraints are met.
4. Emit **CSV** for all new words, the category row (if new), and all edges.

**Output:** CSV only, same pipeline.

---

## Quality checks

Run periodically (especially during **Expand**):

| Flag | Condition | Action |
|------|-----------|--------|
| Thin category | Any category with fewer than 4 words | Fill before next expansion iteration |
| Isolated word | Any word in only 1 category after many iterations | Candidate for pivot in Step C |
| Overlapping categories | Any two categories sharing 3+ words | Consider merging or relabeling |

---

## Seed sensitivity

Different **Initialize** seeds produce different domain “gravity” (mythology vs garage, etc.). Merging graphs from multiple seeds is valid for breadth.

---

## Version History

| Version | Notes |
|---------|--------|
| 1.0 | Initial formalization |
| 1.1 | Canonical `connection_type` set A; entry points Initialize, Expand (*n*), New Connection_Type, New Category; CSV-only output; interface role for agents |
| 1.2 | `categories.label` identity; near-duplicate policy (**reject** high-confidence); New Category aligned with reject policy |
| 1.3 | `categories.label` always normalized; presentation only in `puzzle_categories.display_label` |
| 1.4 | Align with schema: NFKC + `casefold()` for words and category labels; reject overlong |
| 1.5 | Gray-zone near-duplicates: **reject** for v1 (no review queue); high-confidence unchanged |
| 1.6 | **CSV import contract:** header aliases, required columns for algorithm output, optional columns, normalization/length, duplicate-edge behavior; aligned with `app/csv_import.py` |
| 1.7 | **LLM runtime:** menu loop (entry points 1–5), ingest-then-operate instructions; predictability notes |

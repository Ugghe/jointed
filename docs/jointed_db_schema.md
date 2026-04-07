# Connections Puzzle — Database Schema v1.12

## Overview

This schema supports a word-connection puzzle system where:
- A **word** can belong to many **categories**
- A **category** can contain many **words**
- The **relationship** between a word and a category carries its own metadata (difficulty, abstraction, connection type)
- **Puzzles** are discrete playable units composed of a fixed set of categories and their assigned words
- The schema is designed for iterative growth — new words and categories are added continuously via a generative algorithm

---

## Tables

### 1. `words`

The master pool of all words in the system.

```sql
CREATE TABLE words (
    word_id        SERIAL PRIMARY KEY,
    word           TEXT NOT NULL UNIQUE,
    part_of_speech TEXT,
    frequency_tier SMALLINT,
    is_proper      BOOLEAN DEFAULT FALSE,
    date_added     TIMESTAMPTZ DEFAULT NOW(),
    metadata       JSONB
);
```

| Column | Type | Notes |
|--------|------|-------|
| `word_id` | SERIAL | Primary key |
| `word` | TEXT | Unique, stored after **text normalization** (see below) |
| `part_of_speech` | TEXT | e.g. `noun`, `verb`, `adjective` — nullable, fill over time |
| `frequency_tier` | SMALLINT | 1 = very common, 5 = obscure. Nullable, fill over time |
| `is_proper` | BOOLEAN | TRUE for proper nouns (names, places) |
| `date_added` | TIMESTAMPTZ | Auto-set on insert |
| `metadata` | JSONB | Catch-all for future attributes e.g. `{"syllables": 2, "also_fits": ["colors"]}` |

---

### 2. `categories`

Every association tag / puzzle category in the system.

```sql
CREATE TABLE categories (
    category_id     SERIAL PRIMARY KEY,
    label           TEXT NOT NULL UNIQUE,
    domain          TEXT,
    obscurity_score SMALLINT,
    is_tricky       BOOLEAN DEFAULT FALSE,
    date_added      TIMESTAMPTZ DEFAULT NOW(),
    metadata        JSONB
);
```

| Column | Type | Notes |
|--------|------|-------|
| `category_id` | SERIAL | Primary key |
| `label` | TEXT | **Unique** in the database. One row per distinct category *identity* — see **Category label identity** below |
| `domain` | TEXT | Loose tag e.g. `science`, `culture`, `language`, `nature`. TEXT not FK — vocabulary not yet settled |
| `obscurity_score` | SMALLINT | 1 = widely known, 5 = niche/specialist |
| `is_tricky` | BOOLEAN | TRUE if the category is designed to misdirect |
| `date_added` | TIMESTAMPTZ | Auto-set on insert |
| `metadata` | JSONB | Catch-all for future attributes |

---

### Category label identity (`categories.label`)

The schema stores **one string per category** in `label`. That value is the **canonical unique identifier** for the category row (imports, CSV, agents, dedupe).

**Rule:** `categories.label` is **always stored in normalized form** (see **Text normalization** below). It is **not** a display field: **do not** preserve capitalization or title case in this column.

**Why:** The database **`UNIQUE` constraint** is on the stored string. If you stored mixed case, `"Fish"` and `"fish"` would be two rows. Normalizing to a single form makes identity unambiguous.

### Text normalization (implementation decision)

Apply the **same** function to `words.word` and `categories.label` before insert/update and when matching imports:

1. **`unicodedata.normalize("NFKC", s)`** — fold compatibility characters (quotes, spaces, etc.).
2. **Strip** leading/trailing whitespace; **collapse** internal runs of whitespace to a single ASCII space.
3. **`casefold()`** — case-insensitive identity (stronger than `lower()` for Unicode).

**Length:** enforce maximum lengths in application / import (**reject** overlong input with a clear error; do not silently truncate). Suggested caps align with column design: e.g. word ≤ 128 chars, category label ≤ 256 chars (tune as needed).

**Presentation:** The **only** place to preserve case, clever wording, or stylized text for players is the **user-facing** field on the puzzle: **`puzzle_categories.display_label`**. That string is what the player sees on reveal; it may differ from `categories.label` for tone, misdirection, or aesthetics.

**Dedupe:**

- Same normalized string as an existing row → **reject** duplicate category insert (same identity).
- **Near-duplicate** (fuzzy similarity on normalized strings) → `jointed_algorithm_v1.md` (**reject** high-confidence matches; review band optional).

---

### 3. `word_category`

The join table between words and categories. This is the most important table — every relationship carries its own metadata describing the *quality and nature* of that specific connection.

```sql
CREATE TABLE word_category (
    wc_id             SERIAL PRIMARY KEY,
    word_id           INTEGER NOT NULL REFERENCES words(word_id) ON DELETE CASCADE,
    category_id       INTEGER NOT NULL REFERENCES categories(category_id) ON DELETE CASCADE,
    difficulty        SMALLINT,
    abstraction_level SMALLINT,
    connection_type   TEXT,
    quality_score     SMALLINT,
    notes             TEXT,
    date_added        TIMESTAMPTZ DEFAULT NOW(),
    metadata          JSONB,
    UNIQUE(word_id, category_id)
);
```

| Column | Type | Notes |
|--------|------|-------|
| `wc_id` | SERIAL | Primary key |
| `word_id` | INTEGER | FK → words |
| `category_id` | INTEGER | FK → categories |
| `difficulty` | SMALLINT | 1–5. How hard is it to see this word belongs to this category |
| `abstraction_level` | SMALLINT | 1–5. How direct or metaphorical the connection is |
| `connection_type` | TEXT | Canonical v1 values (closed list): `literal`, `categorical`, `associative`, `metaphorical`, `wordplay`, `cultural` — see below |
| `quality_score` | SMALLINT | 1–5. Overall quality/interestingness of this pairing. Nullable, can be rated later |
| `notes` | TEXT | Human-readable explanation of the connection e.g. `"tablet as medicine vs stone tablet"` |
| `date_added` | TIMESTAMPTZ | Auto-set on insert |
| `metadata` | JSONB | Catch-all |

#### Difficulty scale
| Value | Meaning |
|-------|---------|
| 1 | Obvious — most players get it immediately |
| 2 | Easy — recognized with little thought |
| 3 | Medium — requires a moment of reasoning |
| 4 | Hard — likely to mislead |
| 5 | Very tricky — deliberate misdirection or obscure knowledge |

#### Abstraction scale
| Value | Meaning |
|-------|---------|
| 1 | Literal — the word directly is the thing |
| 2 | Categorical — belongs to the category by definition |
| 3 | Associative — strongly associated but not definitional |
| 4 | Metaphorical — requires a conceptual leap |
| 5 | Oblique — surprising, indirect, or requires wordplay |

#### connection_type values
| Value | Meaning |
|-------|---------|
| `literal` | The word is straightforwardly an instance of the category |
| `categorical` | The word belongs to the category by standard classification |
| `associative` | The word is strongly associated with the category by convention or context |
| `metaphorical` | The connection works via metaphor or extended meaning |
| `cultural` | The connection depends on specific cultural knowledge |
| `wordplay` | The connection works via punning, double meaning, or linguistic trick |

---

### 4. `puzzles`

A discrete playable puzzle instance.

```sql
CREATE TABLE puzzles (
    puzzle_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title          TEXT,
    difficulty     SMALLINT,
    status         TEXT DEFAULT 'draft',
    date_created   TIMESTAMPTZ DEFAULT NOW(),
    date_published TIMESTAMPTZ,
    metadata       JSONB
);
```

| Column | Type | Notes |
|--------|------|-------|
| `puzzle_id` | UUID | Primary key — **public identifier**; API JSON uses the usual string form |
| `title` | TEXT | Optional human-readable title |
| `difficulty` | SMALLINT | 1–5 overall puzzle difficulty |
| `status` | TEXT | One of: `draft`, `review`, `published`, `archived` |
| `date_created` | TIMESTAMPTZ | Auto-set on insert |
| `date_published` | TIMESTAMPTZ | Nullable — set when status moves to `published` |
| `metadata` | JSONB | e.g. `{"theme": "nature", "submitted_by": "admin"}` |

---

### 5. `puzzle_categories`

Links a puzzle to its categories, with presentation metadata. A puzzle typically has exactly 4 categories.

```sql
CREATE TABLE puzzle_categories (
    pc_id         SERIAL PRIMARY KEY,
    puzzle_id     UUID NOT NULL REFERENCES puzzles(puzzle_id) ON DELETE CASCADE,
    category_id   INTEGER NOT NULL REFERENCES categories(category_id),
    display_label TEXT,
    slot_color    TEXT,
    sort_order    SMALLINT,
    UNIQUE(puzzle_id, category_id)
);
```

| Column | Type | Notes |
|--------|------|-------|
| `pc_id` | SERIAL | Primary key |
| `puzzle_id` | UUID | FK → puzzles |
| `category_id` | INTEGER | FK → categories |
| `display_label` | TEXT | What the player sees on reveal. May differ from `categories.label` for stylistic/misdirection reasons |
| `slot_color` | TEXT | e.g. `yellow`, `green`, `blue`, `purple` — the difficulty color shown to the player |
| `sort_order` | SMALLINT | Display order within the puzzle (1–4 typically) |

---

### 6. `puzzle_words`

Links each word in a puzzle to both its puzzle and its assigned category within that puzzle. This is a three-way join that records the exact configuration of a played puzzle.

```sql
CREATE TABLE puzzle_words (
    puzzle_id   UUID NOT NULL REFERENCES puzzles(puzzle_id) ON DELETE CASCADE,
    word_id     INTEGER NOT NULL REFERENCES words(word_id),
    category_id INTEGER NOT NULL REFERENCES categories(category_id),
    PRIMARY KEY (puzzle_id, word_id),
    FOREIGN KEY (puzzle_id, category_id)
        REFERENCES puzzle_categories (puzzle_id, category_id)
        ON DELETE CASCADE
);
```

| Column | Type | Notes |
|--------|------|-------|
| `puzzle_id` | UUID | FK → puzzles |
| `word_id` | INTEGER | FK → words |
| `category_id` | INTEGER | FK → categories — which category this word was assigned to *in this specific puzzle* |

The **composite foreign key** to `puzzle_categories (puzzle_id, category_id)` ensures every assignment uses a category that is actually attached to this puzzle. Alignment with the global `word_category` graph is validated in **application code** (or a future trigger), not required here.

> **Why this matters:** The same word can belong to multiple categories. `puzzle_words` records which category it was *used as* in a given puzzle, enabling per-puzzle analytics and preventing the same word appearing in two categories in the same puzzle.

---

## Indexes

```sql
-- word_category lookups from both directions
CREATE INDEX idx_wc_word_id       ON word_category(word_id);
CREATE INDEX idx_wc_category_id   ON word_category(category_id);
CREATE INDEX idx_wc_connection_type ON word_category(connection_type);

-- puzzle assembly queries
CREATE INDEX idx_pc_puzzle_id     ON puzzle_categories(puzzle_id);
CREATE INDEX idx_pw_puzzle_id     ON puzzle_words(puzzle_id);
CREATE INDEX idx_pw_word_id       ON puzzle_words(word_id);

-- full-text search on words
CREATE INDEX idx_words_fts        ON words USING GIN(to_tsvector('english', word));

-- JSONB metadata search
CREATE INDEX idx_words_metadata   ON words USING GIN(metadata);
CREATE INDEX idx_categories_metadata ON categories USING GIN(metadata);
```

---

## Entity Relationship Summary

```
words ──────────────── word_category ──────────────── categories
  │                  (difficulty,                          │
  │                   abstraction_level,                   │
  │                   connection_type,                     │
  │                   quality_score)                       │
  │                                                        │
  └──── puzzle_words ────────────────────────────── puzzle_categories
              │                                           │
              └──────────── puzzles ────────────────────┘
```

---

## Key Design Decisions

**`connection_type` is TEXT not ENUM (storage).** Values are validated in application / import against the **canonical v1 list** (same as `jointed_algorithm_v1.md`): `literal`, `categorical`, `associative`, `metaphorical`, `wordplay`, `cultural`. Adding a new type requires updating **both** this document and the algorithm document, then running the **New Connection_Type** workflow (see algorithm doc). PostgreSQL ENUM could replace TEXT once the list is long-term stable.

**`domain` on categories is TEXT not a FK.** Same reasoning — the domain taxonomy is not yet settled. A `domains` lookup table is a natural future migration once patterns emerge.

**`display_label` on `puzzle_categories` is separate from `categories.label`.** The internal `label` is the **canonical identity** string in the Registry (see **Category label identity** above). The display label is what players see in a given puzzle — it may be more cryptic, stylized, or deliberately misleading.

**`puzzle_words` is a three-way join.** This is intentional. A word can belong to multiple categories in the system, but in any given puzzle it is assigned to exactly one. Recording that assignment at the puzzle level enables analytics (e.g. which category a word was hardest to place in) and prevents ambiguity during gameplay.

**Composite FK** `(puzzle_id, category_id) → puzzle_categories` ensures invalid puzzle/category pairings cannot be stored (implementation decision **B**).

**`puzzle_id` is UUID.** The puzzle row’s primary key is the **public identifier** (non-sequential, safe in URLs). `puzzle_categories` and `puzzle_words` reference it as `UUID`. Registry tables (`words`, `categories`, `word_category`) keep **integer** primary keys. Default on insert: `gen_random_uuid()` (PostgreSQL).

**Refactor migration (approved: strategy A).** When moving from the legacy schema to this one, use a **single Alembic revision** that drops old tables in FK-safe order and creates the new DDL. Existing data may be discarded; no cross-schema data migration is required. Run `alembic upgrade head` after deploy; coordinate so the API does not expect the old schema during the window.

**Local vs cloud schema updates:** Schema changes are **files in git** (Alembic revisions). Pushing to the repo triggers the host **build** (e.g. Render `buildCommand`), which should run **`alembic upgrade head`** against the **production** `DATABASE_URL` — you do not upload a local database file with `git push`. Use a **local** DB for iterative work; production data stays on the managed instance unless you explicitly **dump/restore** or run admin tools.

**Content promotion (local import, then live):** Registry and graph loading — duplicate detection, near-duplicate policy, validation, and rework — should run **locally** (or on a throwaway/staging Postgres) using the **same import pipeline** as production until results are verified. **Pushing to git does not upload row data.** To move verified content to the live database, use **`scripts/promote_db.py`**: set `JOINTED_PROMOTE_TARGET` to the production URL, run `--dry-run`, then `--yes` (replaces all app tables on the target; run migrations on the target first). Alternatives when that does not fit: **`pg_dump` / `pg_restore`**, or **CSV re-import** against production with controlled credentials.

**JSONB on every primary table.** Allows ad-hoc attributes to be stored immediately without schema migrations during the ideation phase. GIN indexes make these queryable. Structured columns can be promoted out of JSONB later once usage patterns are clear.

---

## Import Notes for Algorithmic Output

Algorithm runs (**Initialize**, **Expand**, **New Connection_Type**, **New Category** — see `jointed_algorithm_v1.md`) produce **CSV** only. Run imports locally until satisfied, then promote to production (see **Content promotion** above). A single import pipeline loads into:

1. **categories** (as needed, keyed by label / dedupe rules)
2. **words** (upsert by normalized text)
3. **word_category** rows with full metadata

**CSV contract (normative):** See **`jointed_algorithm_v1.md` — CSV import contract** for required header roles, column aliases, optional columns, and duplicate-edge behavior so output matches `app/csv_import.py`.

**Recommended CSV columns per relationship row:** `word`, `category` or `category_label`, `difficulty`, `abstraction_level`, `connection_type`, `notes` (optional columns per pipeline).

**Rules:**

- Normalize words to lowercase before insert
- Deduplicate words on `word.word` (upsert)
- Normalize category text to the canonical `categories.label` form before insert; dedupe on that value (near-duplicate policy in algorithm doc)
- Deduplicate relationships on `(word_id, category_id)` — unique constraint; treat re-import as upsert/merge per pipeline rules
- `connection_type` must be one of the canonical v1 values listed under `word_category` above

---

## HTTP API evolution (policy)

**Goal:** Callers should **not** need to change existing requests when the **response contract** for that call stays the same. Refactors that move selection or joins into the database are **implementation details** behind stable routes.

**Refactor (e.g. random puzzle):** If the JSON shape clients receive is **unchanged**, do **not** introduce a new API major version or path prefix solely for the new schema. Same path, same payload → no client update.

**Future features** (e.g. difficulty filters, domain selection, curated lists): Prefer **new routes** and/or **query parameters** as needed. That is **additive** surface area, not necessarily a **`/v2`** or parallel version tree — version bumps are reserved for **breaking** changes to an existing contract (field removals, renames, incompatible semantics).

---

## Version History

| Version | Date | Notes |
|---------|------|-------|
| 1.0 | 2026-04-07 | Initial schema |
| 1.1 | 2026-04-07 | Canonical `connection_type` set aligned with algorithm v1.1; import notes tied to algorithm entry points and CSV-only pipeline |
| 1.2 | 2026-04-07 | Category label identity: canonical `label` vs display; cross-ref near-duplicate policy |
| 1.3 | 2026-04-07 | `categories.label` always normalized; presentation only in `display_label` |
| 1.4 | 2026-04-07 | Text normalization: NFKC + whitespace + `casefold()`; reject overlong |
| 1.5 | 2026-04-07 | `puzzle_words` composite FK to `puzzle_categories (puzzle_id, category_id)` |
| 1.6 | 2026-04-07 | Migration strategy: single Alembic drop/create revision (strategy A); no data preservation required |
| 1.7 | 2026-04-07 | HTTP API policy: stable contracts; additive paths/params; no version churn when response unchanged |
| 1.8 | 2026-04-07 | `puzzle_id` as UUID PK (decision A); FK columns updated in `puzzle_categories` / `puzzle_words` |
| 1.9 | 2026-04-07 | Deploy note: git push applies migration **code** via build; local DB not synced; cross-ref algorithm v1.5 gray-zone reject |
| 1.10 | 2026-04-07 | Content promotion: heavy import/QA local; explicit transfer to live DB (not via git) |
| 1.11 | 2026-04-07 | Document `scripts/promote_db.py` for local → live table copy |
| 1.12 | 2026-04-07 | Import Notes cross-ref algorithm v1.6 CSV import contract |

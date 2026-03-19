# Implementation Plan

## Goal

Take the current local Streamlit tool from a working translator for `.po` and `.xlf` files to a robust product foundation suitable for internal use, commercial pilots, and later hosted deployment.

## Phase 1 — Translation quality and control ✅ COMPLETE

### 1. Glossary / term protection ✅
Status: **Implemented**

Deliverables:
- ✅ glossary input in UI (sidebar text area, `source → target` format)
- ✅ glossary injection into prompts (both PO and XLIFF engines)
- ✅ exact-match term protection rules (enforced via system prompt)
- ✅ glossary saved with session state (`st.session_state.glossary`)

Implementation notes:
- `format_glossary_for_prompt()` in `po_translate_en_to_nb.py` — shared by both engines
- Glossary section inserted before domain context in system prompt
- UI supports `→`, `=`, and `->` as separators
- Shows count of loaded terms in sidebar

### 2. Prompt optimisation ✅
Status: **Implemented**

Deliverables:
- ✅ explicit register rules by language (`_REGISTER_NOTES` dict — 19 languages)
- ✅ richer translator role framing ("professional technical translator, native in…")
- ✅ stricter markup preservation guidance for XLIFF (correct/wrong `<g>` tag examples)
- ⏳ optional structured schema output — deferred, JSON mode already used

Implementation notes:
- `_REGISTER_NOTES` covers: nb_NO, nn_NO, da_DK, sv_SE, fi_FI, de_DE, fr_FR, es_ES, pt_BR, it_IT, nl_NL, pl_PL, cs_CZ, sk_SK, hu_HU, ro_RO, bg_BG, hr_HR, sr_RS
- Register rules injected after base translation rules in system prompt
- XLIFF prompt includes explicit before/after examples for `<g>` tag preservation

### 3. Cost estimator ✅
Status: **Implemented**

Deliverables:
- ✅ token estimate based on source length (`_CHARS_PER_TOKEN = 3.5`)
- ✅ estimated request count by batch size
- ✅ rough cost preview per model (6 models in pricing table)

Implementation notes:
- Module: `src/cost_estimator.py`
- Pricing table: gpt-4.1, gpt-4.1-mini, gpt-4.1-nano, gpt-5.2, gpt-4o, gpt-4o-mini
- Displayed as metrics in the file info column ("Est. tokens", "Est. cost")
- Constants: `_PROMPT_OVERHEAD_TOKENS = 600`, `_OUTPUT_MULTIPLIER = 1.4`

## Phase 2 — Review workflow

### 4. Side-by-side diff view
Deliverables:
- source / existing target / new target columns
- placeholder warning badges
- filter for changed or risky entries

### 5. Segment review UI
Deliverables:
- editable translation table after generation
- manual correction before export
- download final reviewed file

### 6. Back-translation sampling
Deliverables:
- sample X percent of entries
- back-translate to source language
- flag divergent results for review

## Phase 3 — Cost and scale

### 7. Translation memory
Deliverables:
- SQLite store keyed by source text, target language, and optional glossary/context signature
- hit/miss metrics
- reuse cached translations before model call

### 8. ZIP / batch processing
Deliverables:
- upload ZIP containing multiple files
- detect formats per file
- translate and return ZIP output

### 9. Multi-target runs
Deliverables:
- select multiple target languages
- produce one output per language
- batch execution with progress reporting

## Phase 4 — New formats

### 10. IDML support
Reason:
Highest-value next format for technical and marketing documentation.

Deliverables:
- unpack IDML ZIP
- translate `Stories/*.xml`
- repack valid IDML
- preserve styling and layout-related XML

### 11. HTML and Markdown
Deliverables:
- preserve tags, links, code blocks, front matter
- update language metadata where relevant

### 12. DITA, Android strings.xml, iOS .strings, JSON i18n
Deliverables:
- dedicated parser and writer per format
- shared work-item contract across all format modules

## Phase 5 — Productisation

### 13. Hosted deployment
Deliverables:
- hosted frontend
- secrets handling
- basic auth / access control
- usage logging

### 14. MCP / API exposure
Deliverables:
- importable service functions wrapped as tools/endpoints
- stable request/response contracts

### 15. Automated pipeline mode
Deliverables:
- folder watcher or queued job execution
- input/output location config
- status logs and retry handling

## Recommended immediate next build order

1. glossary / term protection
2. prompt optimisation
3. cost estimator
4. diff view
5. translation memory
6. IDML support

## Definition of done for each feature

- code path implemented
- basic UI path available if user-facing
- sample file tested successfully
- failure mode documented
- relevant docs updated

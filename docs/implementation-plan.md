# Implementation Plan

## Goal

Take the current local Streamlit tool from a working translator for `.po` and `.xlf` files to a robust product foundation suitable for internal use, commercial pilots, and later hosted deployment.

## Phase 1 — Translation quality and control

### 1. Glossary / term protection
Reason:
This is the highest-leverage improvement because terminology consistency matters more than minor prompt tweaks.

Deliverables:
- glossary input in UI
- glossary injection into prompts
- exact-match term protection rules
- glossary saved with session state

### 2. Prompt optimisation
Reason:
Prompt hardening improves all formats at once.

Deliverables:
- explicit register rules by language
- richer translator role framing
- stricter markup preservation guidance for XLIFF
- optional structured schema output if model support is confirmed

### 3. Cost estimator
Reason:
Large-file usage needs cost visibility before execution.

Deliverables:
- token estimate based on source length
- estimated request count by batch size
- rough cost preview per model

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

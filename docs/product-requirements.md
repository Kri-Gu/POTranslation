# Product Requirements

## Product summary

An AI-assisted translation tool for structured localisation and technical documentation files. The tool preserves placeholders, inline markup, and file structure while translating to multiple target languages.

Current supported formats:
- `.po`
- `.xlf` / XLIFF 1.2

Planned high-value formats:
- `.idml`
- `.html`
- `.md`
- `.dita`
- `strings.xml`
- `.strings`
- JSON i18n

## Problem statement

Generic machine translation tools are poor at structured localisation content because they often:
- break placeholders and inline tags
- mistranslate product terminology
- fail to preserve file format requirements
- require copy/paste workflows that do not scale
- offer weak support for niche technical formats like XLIFF and IDML

The project solves this by offering format-aware translation with context-aware prompting and downloadable round-tripped output files.

## Target users

### Primary
- localisation coordinators
- marketing teams handling multilingual product launches
- technical writers
- product/content teams exporting `.po` or `.xlf` files

### Secondary
- agencies handling client localisation work
- importers/distributors with repeat translation workflows
- developers managing app or site translation resources

## Core jobs to be done

1. Upload a localisation or documentation file and get a valid translated file back.
2. Preserve placeholders, tags, and structure without manual repair.
3. Apply domain terminology consistently.
4. Review risky translations before release.
5. Reduce repeated translation cost across projects.

## Functional requirements

### Existing
- upload `.po` and `.xlf`
- choose model, source language, target language, and batch size
- provide domain context
- translate in batches with retry logic
- download translated output
- warn on placeholder mismatches

### Near-term
- glossary / protected terms
- stronger prompt configuration
- pre-flight cost estimate
- side-by-side diff and segment review UI
- translation memory cache
- folder / ZIP processing

### Future
- additional file formats
- expanded language + locale coverage (e.g. `de`, `en_US`, `en_GB`, `fr_CA`)
- hosted multi-user version
- usage metering and billing
- MCP/API exposure
- background pipeline automation

## Non-functional requirements

- translated files must remain structurally valid
- failed batches must degrade gracefully to per-item retry
- the UI must stay simple enough for non-technical users
- modules should stay reusable outside Streamlit
- cost transparency should be visible before large runs
- locale variants should follow BCP 47 style codes and preserve regional spelling/terminology preferences

## Success criteria

### Quality
- placeholder mismatch rate stays very low
- translated files open correctly in their source tools
- terminology consistency improves with glossary and memory

### Product
- a user can upload and translate without reading code
- the tool handles real customer files without manual cleanup
- additional formats can be added with minimal change to the app shell

### Commercial
- translation cost per file decreases over time via memory/cache
- the product can support either a hosted SaaS or managed-service model

## Constraints

- quality depends on model and prompt quality
- different formats require different parsers and write-back rules
- some technical formats are ZIP containers rather than plain text files
- API cost can become material without memory/caching

## Out of scope for now

- full CAT-tool replacement
- collaborative translation editing workflow
- human translator marketplace
- live CMS plugins before the core engine is stable

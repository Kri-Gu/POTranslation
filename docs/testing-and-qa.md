# Testing and QA

## Testing goals

The main risk in this project is not raw code failure. It is silently producing output files that are syntactically valid but operationally wrong:
- placeholders changed or dropped
- inline tags broken
- wrong terminology used
- target file no longer opens in the source tool

Testing needs to focus on file validity and translation correctness together.

## Test layers

### 1. Parser and write-back tests

For each format module:
- parse a real sample file
- extract work items
- write translated output back
- confirm the output file can be parsed again

Examples:
- `.po`: output reopens with `polib.pofile()`
- `.xlf`: output reparses with `ElementTree.parse()` and target nodes are present
- future `.idml`: output ZIP reopens and required story files remain present

### 2. Placeholder integrity tests

For all formats containing placeholders:
- `%s`, `%d`, `%1$s`
- `{name}`, `{0}`
- HTML tags
- URLs
- XLIFF `<g id="…">`

Assertions:
- all placeholders from source appear in translation
- placeholder order is preserved where order matters
- protected tags are unchanged

### 3. Prompt regression tests

Create a stable set of representative segments and expected translation properties.

For example:
- short UI labels
- technical machine terms
- strings containing placeholders
- strings containing inline markup
- ambiguous strings like `Set`, `Open`, `On`

Assertions should focus on structure and terminology, not exact full-string equality for every language.

### 4. End-to-end smoke tests

For each supported format:
1. run translation on a known sample file
2. inspect summary output
3. verify output file loads successfully
4. spot-check a few translated segments manually

## Manual QA checklist

Before calling a feature stable:
- upload real customer-like sample files
- test with and without domain context
- test target languages `nb`, `sv`, `da`
- test one larger file with many entries
- test one file with existing translations and `force=False`
- confirm warnings appear when placeholders are intentionally broken in a mock response

## Suggested automated test cases

### PO
- empty `msgstr` gets translated
- existing `msgstr` is skipped unless `force=True`
- placeholders remain intact
- plural forms are preserved correctly

### XLIFF
- new `<target>` inserted after `<source>`
- `state="translated"` is written
- `target-language` is written on `<file>`
- inline `<g>` markup survives intact
- units marked `translate="no"` are skipped

### Prompting
- glossary terms override free translation
- register rules appear in generated prompt text
- domain context is injected when provided
- schema output parse succeeds when enabled

## Acceptance criteria for future formats

A new format is not done until:
- it can parse a real-world sample file
- translated output reparses cleanly
- core formatting structures are preserved
- at least one sample with placeholders or markup passes validation
- startup and format docs mention the new format

## Logging and diagnostics

Current useful logs:
- `raw_responses.log`
- `failed_items.log`
- `placeholder_warnings.log`

Recommended additions:
- per-run summary log with model, target language, batch size, file type, counts, and duration
- optional debug export of work items before API call

## Recommended next test additions

1. add unit tests around XLIFF markup preservation
2. add fixture-based smoke tests for `.po` and `.xlf`
3. add a regression suite for prompt generation functions
4. add one golden-file round-trip test per format module

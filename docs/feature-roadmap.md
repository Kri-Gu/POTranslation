# Feature Roadmap

Planned features in implementation order, building from simplest to most complex.

## Core translation quality

| # | Feature | Status | Notes |
|---|---------|--------|-------|
| 1 | **XLIFF translation state** (`state="translated"`) | ✅ Done | Sets standard XLIFF attribute on each `<target>` element |
| 2 | **XLIFF target-language attribute** | ✅ Done | Sets `target-language` on `<file>` elements to match chosen target lang |
| 3 | **Glossary / term protection** | 🔲 Pending | Sidebar input for terms that must never be translated (product names, brand terms) |
| 4 | **Prompt optimisation** | 🔲 Pending | Improve system/user prompts; per-format register; JSON schema enforcement; glossary injection. See `docs/prompt-guide.md` |

## Workflow & UI

| #   | Feature                           | Status     | Notes                                                                 |
| --- | --------------------------------- | ---------- | --------------------------------------------------------------------- |
| 5   | **`.env` editor in sidebar**      | 🔲 Pending | Small UI panel to set API key and defaults without editing files      |
| 6   | **Cost estimator**                | 🔲 Pending | Pre-flight token count + approximate API cost before translating      |
| 7   | **Multi-target batch language**   | 🔲 Pending | Translate one file into N languages in one click                      |
| 8   | **Side-by-side diff view**        | 🔲 Pending | 3-column table: source / old translation / new translation for review |
| 9   | **Segment review UI**             | 🔲 Pending | Editable table post-translation; correct entries before downloading   |
| 10  | **Batch folder / ZIP processing** | 🔲 Pending | Upload a ZIP of files, get a translated ZIP back                      |

## Infrastructure

| # | Feature | Status | Notes |
|---|---------|--------|-------|
| 11 | **Translation memory** (SQLite cache) | 🔲 Pending | Cache translated segments locally; identical source = free result |
| 12 | **Back-translation confidence check** | 🔲 Pending | Back-translate a random sample and flag divergent entries |

## File format support

| # | Feature | Status | Notes |
|---|---------|--------|-------|
| 13 | **IDML** (Adobe InDesign) | 🔲 Pending | Unzip, translate `Stories/*.xml` `<Content>` nodes, repack. See `docs/format-support.md` |
| 14 | **HTML / HTM** | 🔲 Pending | Translate text nodes, preserve tags and attributes |
| 15 | **Markdown** | 🔲 Pending | Translate body text, preserve headings, code blocks, links, front matter |
| 16 | **DITA** (.dita / .ditamap) | 🔲 Pending | XML-based technical writing format; translate `<title>`, `<p>`, `<li>`, `<td>` etc. |
| 17 | **Android strings.xml** | 🔲 Pending | `<resources>/<string>` and `<string-array>` elements |
| 18 | **iOS / macOS .strings** | 🔲 Pending | Key = "Source text"; translate values |
| 19 | **JSON i18n** (i18next / Angular / React) | 🔲 Pending | Flat and nested key→value; preserve numeric keys and ICU plurals |

---

## Rationale for ordering

- **1–2:** Zero-risk XLIFF compliance fixes, ship together
- **3:** Glossary is the single biggest quality improvement — self-contained, high ROI
- **4:** Prompt work builds on the glossary foundation; improves all formats at once
- **5–6:** UI polish and transparency before the bigger workflow features
- **7–10:** Bigger UI/workflow changes; diff view builds on multi-lang output; ZIP wraps existing logic
- **11:** Infrastructure change that underpins cost savings — best added when the flow is stable
- **12:** Most API-intensive feature; last in the core flow
- **13–19:** New format modules are independent of each other; IDML first as it's the most requested

## Future architecture considerations

- Keep all `translate_*_file()` functions clean and importable with no Streamlit dependency — this makes MCP server / API exposure trivial
- Translation memory (step 11) should live in `src/memory.py` and be shared by CLI and web flows
- New format modules should follow the same contract as `xliff_translate.py`:
  `translate_<format>_file(input_path, output_path, *, model, target_lang, ...) → Dict`
- All features should degrade gracefully when optional (empty glossary = unchanged behaviour)

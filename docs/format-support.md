# File Format Support

Supported formats and implementation notes for formats planned on the roadmap.

---

## Currently supported

### `.po` — gettext / Poedit

- **Library:** `polib`
- **Structure:** `msgid` (source) + `msgstr` (translation) pairs, with optional `msgctxt`
- **What we translate:** All entries where `msgstr` is empty, or all entries if `force=True`
- **Special handling:** Plural forms (`msgid_plural` / `msgstr[0]`, `msgstr[1]`); fuzzy-flagged entries skipped by default
- **Write-back:** `entry.msgstr = translated`; `polib` serialises back to the original format

### `.xlf` — XLIFF 1.2

- **Library:** `xml.etree.ElementTree` (stdlib)
- **Structure:** `<file>` → `<body>` → `<trans-unit>` → `<source>` + `<target>`
- **What we translate:** `<trans-unit>` elements where `<target>` is absent or empty, and `translate="no"` is not set
- **Special handling:** Inline `<g>` markup within `<source>` is preserved through round-trip XML serialisation; `state="translated"` is written on every `<target>`; `target-language` is set on every `<file>` element
- **Write-back:** `ElementTree.write()` with registered namespaces to avoid `ns0:` prefix pollution

---

## Planned formats

### IDML — Adobe InDesign (roadmap #13)

**What it is:** InDesign documents saved as "InDesign Markup Language". An IDML file is a ZIP archive containing XML files.

**Archive structure:**
```
document.idml
├── mimetype                    (plain text: "application/vnd.adobe.indesign-idml+zip")
├── designmap.xml               (references all component files)
├── Stories/
│   ├── Story_u1a3.xml          (each text frame is a separate story file)
│   └── Story_u2f9.xml
├── Spreads/
│   └── Spread_u1b2.xml         (layout geometry — do NOT translate)
├── Resources/
│   ├── Styles.xml
│   └── Fonts.xml
└── META-INF/
    └── container.xml
```

**Where the text lives:** **`Stories/*.xml` only.** Each story file has this structure:

```xml
<Story Self="u1a3" …>
  <ParagraphStyleRange AppliedParagraphStyle="…">
    <CharacterStyleRange AppliedCharacterStyle="…">
      <Content>This is the text to translate.</Content>
    </CharacterStyleRange>
    <CharacterStyleRange AppliedCharacterStyle="…" FontStyle="Bold">
      <Content>Bold text here.</Content>
    </CharacterStyleRange>
  </ParagraphStyleRange>
</Story>
```

**Translation target:** `<Content>` nodes only. All attributes, `<ParagraphStyleRange>`, `<CharacterStyleRange>`, and geometry files must be left untouched.

**Key challenges:**

| Challenge | Solution |
|---|---|
| Text split across multiple `<Content>` nodes (inline bold, italic, etc.) | Group consecutive `<Content>` nodes within the same `<ParagraphStyleRange>` into a single translation unit; map back by index |
| Special InDesign characters: soft return (`&#x000D;`), column break, forced line break | Represent as sentinel tokens in the prompt (e.g., `[[BR]]`); restore after translation |
| Locked/non-printing layers | Check parent element attributes; skip if `ContentType="Unassigned"` or story is referenced as `Hidden="true"` in Spreads |
| Master page text (page numbers, running heads) | Identify via `designmap.xml` spreads references; offer option to skip |
| Overset text | Not detectable at the XML level — flag in output that user should check for overset |

**Implementation plan:**
```python
# src/idml_translate.py
import zipfile
import shutil
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET

IDML_NS = "http://ns.adobe.com/AdobeInDesign/idml/1.0/…"

def _get_story_files(idml_path: str) -> List[str]:
    """Return list of Story/*.xml paths within the IDML zip."""

def _build_work_items_idml(story_tree) -> List[Dict]:
    """Extract <Content> nodes grouped by paragraph for translation."""

def translate_idml_file(input_path, output_path, *, model, target_lang, …) -> Dict:
    """
    1. Open IDML as zip
    2. Copy to temp dir
    3. For each Stories/*.xml:
        a. Parse XML
        b. Extract Content nodes grouped by paragraph
        c. Translate each paragraph group as a single unit
        d. Write translated text back to Content nodes
        e. Save modified XML back into the copy
    4. Repack as .idml zip
    5. Write to output_path
    """
```

**Paragraph grouping strategy:**

Because a single visible sentence may be split across many `<CharacterStyleRange>`/`<Content>` pairs (e.g., "Hello **world**" = two content nodes), the translator should:
1. Concatenate `<Content>` texts within one `<ParagraphStyleRange>`, separated by a marker like `|||`
2. Translate the concatenated string
3. Split the translated string on `|||` and write back to individual `<Content>` nodes

This preserves character-level styling (bold, italic, colour) at the cost of some translation ambiguity at split boundaries.

---

### HTML / HTM (roadmap #14)

**Library:** `html.parser` (stdlib) or `lxml.html`

**What we translate:** All text nodes that are not inside `<script>`, `<style>`, `<code>`, `<pre>`, `<head>`, or elements with `translate="no"`

**Key challenges:**

| Challenge | Solution |
|---|---|
| Inline elements break text continuity (`<a>`, `<strong>`, `<em>`) | Walk the DOM; collect runs of text+inline-elements as one segment |
| `alt`, `title`, `placeholder`, `aria-label` attributes | Enumerate translatable attributes explicitly |
| charset meta tag | Ensure output is UTF-8; update `<meta charset>` |
| `hreflang` / `lang` attributes | Update `<html lang="…">` to target language |

**Approach:** `lxml.html` gives a proper DOM; translate visible text nodes and known translatable attributes. Preserve all tags. Write with `lxml.html.tostring(tree, encoding="unicode")`.

---

### Markdown / MDX (roadmap #15)

**Library:** `mistune` or `markdown-it-py` for parsing; `regex` for extraction

**What we translate:** Paragraph text, headings, list items, blockquote content, table cell content

**What we preserve:** Fenced code blocks (` ``` `), inline code (`` ` ``), image URLs, link URLs (but optionally translate link text), YAML front matter keys (translate values only if whitelisted), MDX JSX attribute values

**Approach:**
1. Parse to AST (Abstract Syntax Tree)
2. Walk AST nodes for translatable text
3. Translate each text node individually (short) or group paragraphs into batches
4. Reconstruct Markdown from the modified AST

**Alternative (simpler):** Regex-based extraction — extract paragraphs between fence blocks, translate, splice back. Less robust but sufficient for most technical docs.

---

### DITA (roadmap #16)

**What it is:** Darwin Information Typing Architecture — XML-based structured documentation used by technical writers for product manuals, help systems.

**Library:** `xml.etree.ElementTree` or `lxml`

**File types:** `.dita` (topics), `.ditamap` (navigation maps)

**Translatable elements:** `<title>`, `<shortdesc>`, `<p>`, `<li>`, `<dt>`, `<dd>`, `<td>`, `<th>`, `<note>`, `<menucascade>`, `<uicontrol>`

**Elements to preserve untranslated:** `<codeph>`, `<codeblock>`, `<filepath>`, `<apiname>`, `<varname>`, `<userinput>`, `<systemoutput>`, elements with `translate="no"` attribute

**Approach:** Similar to XLIFF — walk the XML tree, extract text from known translatable tags while skipping code-content tags. The DITA `@translate="no"` attribute is the authoritative signal.

---

### Android `strings.xml` (roadmap #17)

**Library:** `xml.etree.ElementTree`

**Structure:**
```xml
<resources>
    <string name="app_name">My App</string>
    <string name="welcome_message">Welcome, %1$s!</string>
    <string-array name="days">
        <item>Monday</item>
        <item>Tuesday</item>
    </string-array>
    <plurals name="numberOfSongs">
        <item quantity="one">%d song found</item>
        <item quantity="other">%d songs found</item>
    </plurals>
</resources>
```

**What we translate:** `<string>` values, `<string-array>/<item>` values, `<plurals>/<item>` values

**Special handling:**
- Android placeholders: `%s`, `%d`, `%1$s`, `@string/ref` — must be preserved
- `translatable="false"` attribute on `<string>` — skip these
- CDATA sections
- HTML markup within strings (e.g., `<string><b>Bold</b> text</string>`) — preserve tags

---

### iOS / macOS `.strings` (roadmap #18)

**Format:** Plain text key-value, two variants:

```
// Standard .strings
"source_key" = "Source text here";

// Localizable.stringsdict (XML, for plurals)
```

**Library:** Custom parser (no stdlib support) — parse with `re`

Pattern: `^"((?:[^"\\]|\\.)*)"\s*=\s*"((?:[^"\\]|\\.)*)"\s*;`

**What we translate:** The value side only. Keys are code identifiers and must not change.

**Special handling:**
- `%@`, `%d`, `%1$@` placeholders
- Comments (`/* comment */`, `// comment`) — preserve
- `.stringsdict` files are XML and can be handled like `strings.xml` for the plural forms

---

### JSON i18n (roadmap #19)

**Formats covered:**

| Library/Framework | JSON structure |
|---|---|
| i18next | Flat: `{"key": "text"}` or nested: `{"ns": {"key": "text"}}` |
| Angular i18n | Flat: `{"BUTTON_SAVE": "Save"}` |
| React i18n (react-i18next) | Nested, supports ICU plurals |
| Vue i18n | Nested objects |
| go-i18n | Arrays of objects with `id`, `other`, `one` fields |

**What we translate:** String values only. Keys, numeric values, boolean values, and nested object structure must be preserved exactly.

**Special handling:**
- ICU plural syntax: `"items": "You have {count, plural, one {# item} other {# items}}"` — translate the human text but preserve the ICU structure
- Variables: `{{name}}`, `{name}`, `%(name)s` — preserve
- HTML within strings: `"label": "<strong>Important</strong>"` — preserve tags
- `_comment` and `description` keys — optionally translate for developer context

**Approach:**
1. Flatten nested JSON to `{"path.to.key": "value"}` for batching
2. Translate string values in batches
3. Reconstruct nested structure from dotted paths

---

## Format detection

Current detection is by file extension in `app.py`. As more formats are added, consider a two-level detection:

1. **Extension** → candidate format list
2. **Magic bytes / root element** → confirm

```python
def detect_format(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext == ".po":
        return "po"
    if ext in (".xlf", ".xliff"):
        return "xliff"
    if ext == ".idml":
        return "idml"
    if ext == ".html" or ext == ".htm":
        return "html"
    if ext == ".md" or ext == ".mdx":
        return "markdown"
    if ext in (".dita", ".ditamap"):
        return "dita"
    if ext == ".strings":
        return "ios_strings"
    if ext == ".xml":
        # Disambiguate by root element
        root_tag = _peek_xml_root(path)
        if root_tag == "resources":
            return "android_strings"
        if root_tag in ("topic", "concept", "task", "reference", "map"):
            return "dita"
        if root_tag == "xliff":
            return "xliff"
    if ext == ".json":
        return "json_i18n"
    raise ValueError(f"Unrecognised file format: {ext}")
```

---

## Priority and effort summary

| Format | Effort | Business demand | Priority |
|---|---|---|---|
| IDML | High | High (InDesign users, marketing agencies) | 🔴 Top |
| HTML | Low | High (web content, CMSs) | 🔴 Top |
| Markdown | Low | Medium (docs sites, GitHub wikis) | 🟠 Medium |
| DITA | Medium | Medium (technical writing teams) | 🟠 Medium |
| JSON i18n | Low | Medium (developers React/Angular/Vue) | 🟠 Medium |
| Android strings.xml | Low | Medium (mobile dev teams) | 🟡 Low-medium |
| iOS .strings | Low | Medium (mobile dev teams) | 🟡 Low-medium |

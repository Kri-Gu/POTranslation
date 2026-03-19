# Translation File Translator (OpenAI-powered)

Translate `.po` (gettext/Poedit) and `.xlf` (XLIFF 1.2) files using the OpenAI API. Built for translating UI strings and technical content from English or German into Norwegian Bokmål, Swedish, Danish, and other European languages — while preserving placeholders, inline markup, HTML tags, and formatting.

## Features

- **Web UI (Streamlit)** — upload, configure, translate, and download without touching the command line
- **Multi-format support** — `.po` (gettext/Poedit) and `.xlf` (XLIFF 1.2) with correct round-trip handling
- **High-quality translation** via `gpt-4.1` or `gpt-5.2` (configurable) with JSON mode for reliable output
- **Glossary / term protection** — define enforced term pairs to ensure consistent terminology
- **Cost estimator** — token and cost estimate displayed before translation starts
- **Per-language register rules** — automatic formal/informal or locale-style guidance for 23 languages/locales
- **Domain context support** — feed a context file so the model understands your product domain
- **Per-entry source detection** (English vs German) with a `--source-lang` override
- **Target languages**: `nb` (Norwegian Bokmål), `sv` (Swedish), `da` (Danish), `de` (German), `fr`, `fr_CA`, `en_US`, `en_GB`, `es`, `pl`, `cs`, `sk`, `hu`, `hr`, `bs`, `sr`, `sl`, `ro`, `bg`, `ru`, `ka`, `el`, `me`
- **Placeholder preservation** with post-translation validation (`%s`, `%d`, `{name}`, HTML tags, URLs)
- **XLIFF inline markup preservation** — `<g>` elements and their attributes survive translation unchanged
- **Batch processing** with retry and per-item fallback on failure
- **Dry-run mode** to preview what will be translated before spending API credits
- Logs unparsable responses to `raw_responses.log` and failed items to `failed_items.log`

## Documentation

| Document | Description |
|---|---|
| [docs/startup-guide.md](docs/startup-guide.md) | Setup, launch, CLI usage, and troubleshooting |
| [docs/architecture.md](docs/architecture.md) | Code structure, modules, data flow |
| [docs/feature-roadmap.md](docs/feature-roadmap.md) | Prioritised feature list with status |
| [docs/prompt-guide.md](docs/prompt-guide.md) | Prompt design and optimisation recommendations |
| [docs/format-support.md](docs/format-support.md) | Supported formats and implementation notes (IDML, HTML, Markdown, DITA, etc.) |
| [docs/product-requirements.md](docs/product-requirements.md) | Product scope, users, jobs to be done, requirements |
| [docs/implementation-plan.md](docs/implementation-plan.md) | Phased execution plan and recommended build order |
| [docs/testing-and-qa.md](docs/testing-and-qa.md) | Test strategy, QA checklist, and acceptance criteria |
| [docs/deployment-and-ops.md](docs/deployment-and-ops.md) | Local operation, hosted path, and operational concerns |

## Quick start

### Requirements

- Python 3.10+
- An OpenAI API key

### Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a local `.env` file from the template (**DO NOT** commit this file):

```powershell
cp .env.example .env
# Edit .env and add your API key
```

The `.env` file configures defaults for both the CLI and the web UI:

```ini
OPENAI_API_KEY=sk-proj-YOUR-KEY-HERE

# All of these are optional — they set the default values
DEFAULT_TARGET_LANGUAGE=nb    # e.g. nb, sv, da, de, fr_CA, en_US, en_GB
DEFAULT_SOURCE_LANGUAGE=auto  # auto, en, de
DEFAULT_MODEL=gpt-4.1        # any model from the table below
BATCH_SIZE=20                 # 5–50
DEFAULT_CONTEXT_FILE=context.json  # path to domain context (optional)
```

> **Tip:** If your team mostly translates to Swedish, set `DEFAULT_TARGET_LANGUAGE=sv` and everyone gets Swedish as the default without passing `--target-lang` every time.

## Web UI (recommended)

The easiest way to use the translator:

```powershell
streamlit run src/app.py
```

This opens a browser with:
- File upload for your `.po` or `.xlf` file
- Sidebar to choose model, target language, batch size, domain context, and glossary terms
- Pre-flight cost estimate (tokens and USD) before translation
- Live progress bar during translation
- Translation preview table
- Download button for the result

You can also enter your API key directly in the sidebar (it is never stored).

## CLI usage

### `.po` files

Basic usage:

```powershell
python src/po_translate_en_to_nb.py "input.po" "output.po" --target-lang nb
```

### Recommended: use domain context

If your translations cover a specific domain (e.g. lawn/garden machinery), pass a context file for much better terminology:

```powershell
python src/po_translate_en_to_nb.py "input.po" "output.po" --target-lang nb --context-file context.json
```

### Examples

Translate to Norwegian Bokmål with context:

```powershell
python src/po_translate_en_to_nb.py "Internal_documentation/Poedit files/nb_NO.po" "output/translated_NO_all.po" --model gpt-4.1 --batch-size 20 --force --target-lang nb --context-file context.json
```

Translate to Swedish:

```powershell
python src/po_translate_en_to_nb.py "Internal_documentation/Poedit files/nb_NO.po" "output/translated_SE_all.po" --model gpt-4.1 --batch-size 20 --force --target-lang sv --context-file context.json
```

Translate to Danish:

```powershell
python src/po_translate_en_to_nb.py "Internal_documentation/Poedit files/nb_NO.po" "output/translated_DK_all.po" --model gpt-4.1 --batch-size 20 --force --target-lang da --context-file context.json
```

Dry run (preview without API calls):

```powershell
python src/po_translate_en_to_nb.py "Internal_documentation/Poedit files/nb_NO.po" "output.po" --force --target-lang nb --dry-run
```

### `.xlf` files (XLIFF 1.2)

```powershell
python src/xliff_translate.py "input.xlf" "output.xlf" --target-lang nb
```

With domain context and a specific model:

```powershell
python src/xliff_translate.py "input.xlf" "output.xlf" --target-lang sv --model gpt-4.1 --context-file context.json
```

The XLIFF translator writes `state="translated"` on every `<target>` element and sets `target-language` on every `<file>` element, conforming to the XLIFF 1.2 standard.

### CLI options

| Option | Default | Description |
|--------|---------|-------------|
| `--model` | `gpt-4.1` | OpenAI model to use |
| `--batch-size` | `20` | Items per API call (smaller = better quality) |
| `--force` | off | Translate all entries (prefer `msgstr` if present) |
| `--source-lang` | `auto` | `auto`, `en`, or `de` — source detection behaviour |
| `--target-lang` | `nb` | `nb`, `sv`, or `da` — target language |
| `--context-file` | none | Path to domain context file (e.g. `context.json`) |
| `--dry-run` | off | Preview what would be translated, no API calls |
| `--verbose` / `-v` | off | Show detailed progress |

### Model recommendations

| Model | Quality | Cost | Best for |
|-------|---------|------|----------|
| `gpt-5.2` | ★★★★★+ | High | Best available quality — complex / critical translations |
| `gpt-4.1` | ★★★★★ | Medium | Production translations (recommended default) |
| `gpt-4.1-mini` | ★★★★ | Low | Large files where cost matters |
| `gpt-4.1-nano` | ★★★ | Very low | Quick drafts / testing |
| `gpt-4o` | ★★★★ | Medium | Alternative if 4.1 unavailable |

## Verification

After a run, you should verify:

1. Open the resulting `.po` in Poedit for spot checks.
2. Check the console output for **placeholder warnings** (reported automatically).
3. Review `placeholder_warnings.log` if any placeholders were dropped during translation.
4. Count empty translations:

```powershell
python -c "import polib; p=polib.pofile('output/translated_NO_all.po'); empty=[e for e in p if not e.msgstr.strip() and e.msgid!='']; print(f'Empty: {len(empty)}')"
```

## Domain context file

The `--context-file` option lets you provide domain-specific instructions. This dramatically improves translation quality for specialised content.

The file can be plain text or JSON. Example (`context.json`):

```
Translate technical language related to lawn and garden machinery and automotive
topics. Pay particular attention to accurate terminology for components,
mechanisms, and technical processes.
```

## Security & Git

**Do NOT commit your `.env` or API keys.** The `.gitignore` excludes:

- `.env`, `.venv/`, `venv/`
- `raw_responses.log`, `failed_items.log`, `placeholder_warnings.log`
- `translated_*.po` and `Internal_documentation/`

Before pushing, verify: `git status --short`

## License

MIT

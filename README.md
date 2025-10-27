<<<<<<< HEAD
# PO file translator (OpenAI-powered)

Small utility to translate .po files (gettext) using the OpenAI API. The tool was built to translate UI strings from English or German into Norwegian Bokmål, Swedish, or Danish while preserving placeholders, HTML tags, and formatting.

This repository contains a standalone script that:

- Loads a `.po` file with `polib`.
- Heuristically detects whether the source text is English or German (per-entry).
- Sends batches to the OpenAI API with strict instructions to return JSON mappings id->translation.
- Writes translated `.po` files ready to open in Poedit.

Important: This project uses your OpenAI API key. Do NOT commit `.env` or any files containing secrets.

## Quick start

Requirements

- Python 3.10+
- A working OpenAI API key

Install dependencies (recommended inside a venv):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a local `.env` file with your API key (DO NOT commit this file):

```
OPENAI_API_KEY="sk-..."
```

## Usage

Basic usage:

```powershell
python src/po_translate_en_to_nb.py "path\to\input.po" "path\to\output.po" --target-lang nb
```

Examples

- Translate to Norwegian Bokmål (default):

```powershell
python src/po_translate_en_to_nb.py "Internal_documentation/Poedit files/nb_NO.po" "translated_nb_NO_gpt4o_all.po" --model gpt-4o --batch-size 20 --force --target-lang nb
```

- Translate to Swedish:

```powershell
python src/po_translate_en_to_nb.py "Internal_documentation/Poedit files/nb_NO.po" "translated_sv_SE_gpt4o_all.po" --model gpt-4o --batch-size 20 --force --target-lang sv
```

- Translate to Danish:

```powershell
python src/po_translate_en_to_nb.py "Internal_documentation/Poedit files/nb_NO.po" "translated_da_DK_gpt4o_all.po" --model gpt-4o --batch-size 20 --force --target-lang da
```

CLI options of interest

- `--model`: OpenAI model to use (default `gpt-4o`)
- `--batch-size`: Items per API call (tune to balance cost and reliability)
- `--force`: Translate all entries (prefer `msgstr` if present, otherwise `msgid`)
- `--source-lang`: `auto`, `en`, or `de` — controls source detection behavior
- `--target-lang`: `nb`, `sv`, or `da` — target language

## Verification

After a run, you should verify:

- Open the resulting `.po` in Poedit for spot checks.
- Ensure placeholders are preserved (`%s`, `{name}`, `%%`, etc.).
- Check for empty `msgstr` entries or untranslated entries where `msgstr == msgid`.

Quick check (count empty translations) using Python/polib:

```powershell
python - <<'PY'
import polib
p = polib.pofile(r'translated_nb_NO_gpt4o_all.po')
empty = [e for e in p if not e.msgstr.strip() and e.msgid!='']
print('empty:', len(empty))
for e in empty[:20]:
   print(e.msgid)
PY
```

## Security & Git

Don't commit your `.env` or API keys. The repository `.gitignore` excludes the common secrets and generated outputs:

- `.env`, `.venv`, `venv/`
- `raw_responses.log`, `failed_items.log`
- `translated_*.po` and `Internal_documentation/`

Before uploading to GitHub

1. Remove or move any `translated_*.po` files you don't want public. They are ignored by default, but double-check with `git status`.
2. Ensure `.env` is present in `.gitignore` and not staged: `git restore --staged .env` (if previously staged).

## Resume workflow

If a run is interrupted or you need to re-run only missing translations:

1. Edit/inspect the partially translated `.po` and identify missing `msgstr` entries.
 # POTranslation

 Automatic PO (Poedit) file translator using the OpenAI API.

 This project provides a small CLI tool to translate gettext `.po` files. It is designed to
 handle mixed German/English source strings and translate them into a chosen target language
 (Norwegian Bokmål, Swedish, or Danish) while preserving placeholders, HTML tags and formatting.

 Key features

 - Per-entry source detection (English vs German) with a `--source-lang` override
 - Target languages: `nb` (Norwegian Bokmål), `sv` (Swedish), `da` (Danish)
 - Preserves placeholders (printf `%s`, `%d`, `%%`), Python/ICU `{name}`, numeric `{0}`, and HTML tags
 - Batch processing with retry and per-item fallback
 - Logs unparsable model responses to `raw_responses.log` and failed items to `failed_items.log`

 Quick start

 Requirements

 - Python 3.10+
 - OpenAI API key

 Install in a virtual environment:

 ```powershell
 python -m venv .venv
 .\.venv\Scripts\Activate.ps1
 pip install -r requirements.txt
 ```

 Create a local `.env` file with your API key (DO NOT commit this file):

 ```
 OPENAI_API_KEY="sk-..."
 ```

 Usage

 ```powershell
 python src/po_translate_en_to_nb.py "input.po" "output.po" --target-lang nb
 ```

 Important options

 - `--model`       : OpenAI model (default `gpt-4o`)
 - `--batch-size`  : Items per API call (default 50)
 - `--force`       : Translate all entries (prefer `msgstr` if present)
 - `--source-lang` : `auto`, `en`, or `de` — controls source detection
 - `--target-lang` : `nb`, `sv`, or `da` — target language

 Verification

 After a run, open the generated `.po` in Poedit and spot-check.
 Run the simple Python snippet below to count empty translations:

 ```powershell
 python - <<'PY'
 import polib
 p = polib.pofile(r'translated_nb_NO_gpt4o_all.po')
 empty = [e for e in p if not e.msgstr.strip() and e.msgid!='']
 print('empty:', len(empty))
 for e in empty[:20]:
     print(e.msgid)
 PY
 ```

 Security / git

 Do NOT commit secrets. The `.gitignore` is configured to exclude:

 - `.env`, `.venv`/`venv/`
 - generated translations `translated_*.po`
 - logs: `raw_responses.log`, `failed_items.log`
 - `Internal_documentation/`

 Before publishing to GitHub, verify there are no sensitive files staged:

 ```powershell
 git check-ignore -v .env translated_*.po raw_responses.log failed_items.log "Internal_documentation/*"
 git status --short
 ```

 Resume workflow

 If a run fails or you need to retry only missing items, re-run with `--force` and `--batch-size` tuned (smaller for reliability).
 Failed items are appended to `failed_items.log`.

 Next steps I can help with

 - Add an automated placeholder/format-preservation check script (recommended before publishing)
 - Run final pre-publish checks and push again if you want me to complete the Git push

 License

 Add a license file if you plan to publish this repository publicly.

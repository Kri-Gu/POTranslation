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
2. Re-run the script with `--force` or `--source-lang`/`--batch-size` tuned to re-translate only what you need. Example:

```powershell
python src/po_translate_en_to_nb.py "partial.po" "partial_retry.po" --batch-size 1 --model gpt-4o --force --target-lang nb
```

This script logs any items that failed to `failed_items.log` and raw model responses to `raw_responses.log` to aid debugging.

## Troubleshooting

- If you see parsing errors in `raw_responses.log`, increase retries or reduce `--batch-size`.
- If translations are incorrect in context, consider re-running problematic entries with additional context or a glossary.

## License

This project is provided as-is for internal use. Add a license file if you plan to publish.

---
If you want, I can add an automated placeholder-check tool and a small test that validates all placeholders are preserved across translations before uploading to GitHub.
# PO File Translator: English to Norwegian Bokmål

A Python tool that automatically translates PO (Poedit) files from English to Norwegian Bokmål using OpenAI's API.

## Features

- 🔄 Translates English msgstr entries to Norwegian Bokmål
- 🛡️ Preserves all formatting, placeholders, and metadata
- 🎯 Maintains capitalization and punctuation style
- 📝 Keeps comments, msgctxt, and developer notes intact
- 🔧 Handles printf-style (%s, %d), Python/ICU ({name}, {0}), and HTML placeholders
- 🚀 Batch processing for efficient API usage
- ⚡ Retry logic for robust operation

## Prerequisites

- Python 3.7+
- OpenAI API key
- PO files with English text to translate

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd translate_poedit
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set your OpenAI API key:
```bash
# On Windows:
set OPENAI_API_KEY=your_api_key_here

# On macOS/Linux:
export OPENAI_API_KEY=your_api_key_here
```

## Usage

### Basic Usage

```bash
python src/po_translate_en_to_nb.py input.po output.po
```

### Advanced Options

```bash
python src/po_translate_en_to_nb.py input.po output.po \
    --model gpt-4o \
    --batch-size 50 \
    --verbose
```

### Options

- `--model`: OpenAI model to use (default: `gpt-4o`)
- `--batch-size`: Number of entries per API call (default: 50)
- `--verbose`: Enable verbose output

## How It Works

The tool processes PO files with the following logic:

1. **English Detection**: Identifies English text using heuristics (ASCII characters + common English UI words)
2. **Translation Strategy**:
   - If `msgstr` contains English → translates it to Norwegian
   - If `msgstr` is empty and `msgid` looks English → translates `msgid` and uses as `msgstr`
   - Otherwise → leaves entry unchanged
3. **Preservation**: Maintains all PO file structure, comments, and formatting
4. **Batch Processing**: Groups translations for efficient API usage

## Examples

### Input PO Entry
```po
#. Developer comment
#: source/file.php:123
msgctxt "UI context"
msgid "Kundenstimmen - Archiv"
msgstr "Customer reviews archive"
```

### Output PO Entry
```po
#. Developer comment
#: source/file.php:123
msgctxt "UI context"
msgid "Kundenstimmen - Archiv"
msgstr "Arkiv for kundeanmeldelser"
```

## Translation Rules

The tool follows strict Norwegian Bokmål translation guidelines:

- ✅ Standard Norwegian Bokmål terminology
- ✅ Preserves placeholder formatting: `%s`, `{name}`, `%d`, etc.
- ✅ Maintains HTML tags and URLs unchanged
- ✅ Keeps original capitalization style (Title Case → Title Case)
- ✅ Consistent technical term translation

## Project Structure

```
translate_poedit/
├── src/
│   └── po_translate_en_to_nb.py    # Main translation script
├── tests/                          # Unit tests
├── docs/                          # Documentation
├── examples/                      # Example PO files
├── Internal_documentation/        # Project documentation
├── requirements.txt               # Python dependencies
├── .gitignore                    # Git ignore rules
├── CHANGELOG.md                  # Version history
└── README.md                     # This file
```

## Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black src/
flake8 src/
```

### Type Checking
```bash
mypy src/
```

## Dependencies

### Core
- `openai`: OpenAI API client
- `polib`: PO file parsing and manipulation
- `tenacity`: Retry logic for API calls

### Development (Optional)
- `pytest`: Testing framework
- `black`: Code formatter
- `flake8`: Linting
- `mypy`: Type checking

## Configuration

### Environment Variables

- `OPENAI_API_KEY` (required): Your OpenAI API key

### Model Recommendations

- **Quality**: `gpt-4o` (default) - Best translation quality
- **Speed**: `gpt-4o-mini` - Faster and more cost-effective
- **Legacy**: `gpt-3.5-turbo` - Budget option

## Cost Estimation

Translation costs depend on:
- Number of strings to translate
- Model choice (gpt-4o vs gpt-4o-mini)
- String length

Example: ~1000 UI strings typically cost $0.50-$2.00 with gpt-4o-mini.

## Troubleshooting

### Common Issues

1. **"Please set OPENAI_API_KEY"**
   - Ensure your API key is set as an environment variable

2. **"Failed to load PO file"**
   - Verify the input file path and encoding (should be UTF-8)

3. **API Rate Limits**
   - Reduce `--batch-size` or add delays between requests

4. **Translation Quality Issues**
   - Try a different model (gpt-4o for best quality)
   - Check if technical terms need custom handling

### Debug Mode
```bash
python src/po_translate_en_to_nb.py input.po output.po --verbose
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license here]

## Support

For issues and questions:
- Check the [troubleshooting section](#troubleshooting)
- Review the [examples](examples/)
- Open an issue on GitHub

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and updates.
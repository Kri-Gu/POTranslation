# Startup Guide

## Prerequisites

- Windows with PowerShell
- Python 3.10+
- An OpenAI API key

## First-time setup

From the project root:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a local `.env` file in the project root and add your API key:

```ini
OPENAI_API_KEY=your_api_key_here
DEFAULT_TARGET_LANGUAGE=nb
DEFAULT_SOURCE_LANGUAGE=auto
DEFAULT_MODEL=gpt-4.1
BATCH_SIZE=20
DEFAULT_CONTEXT_FILE=context.json
```

## Start the frontend

From the project root:

```powershell
.\venv\Scripts\Activate.ps1
streamlit run src/app.py
```

Default local URL:

```text
http://localhost:8501
```

If port `8501` is already in use, Streamlit will select the next available port.

## Start the frontend without activating the venv

```powershell
"C:/01. Development/translate_poedit/venv/Scripts/python.exe" -m streamlit run src/app.py
```

## Use the frontend

1. Upload a `.po` or `.xlf` file.
2. Select target language, model, and batch size.
3. Optionally provide a context file.
4. Add your API key in the sidebar if it is not in `.env`.
5. Click the translate button and download the output file.

## CLI usage

### Translate a PO file

```powershell
"C:/01. Development/translate_poedit/venv/Scripts/python.exe" src/po_translate_en_to_nb.py input.po output.po --target-lang nb --context-file context.json
```

### Translate an XLIFF file

```powershell
"C:/01. Development/translate_poedit/venv/Scripts/python.exe" src/xliff_translate.py input.xlf output.xlf --target-lang sv --context-file context.json
```

## Troubleshooting

### `streamlit` is not recognized

Run:

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Or launch Streamlit through Python:

```powershell
"C:/01. Development/translate_poedit/venv/Scripts/python.exe" -m streamlit run src/app.py
```

### `OPENAI_API_KEY` missing

Add the key to `.env` or enter it in the Streamlit sidebar before starting a translation.

### Module import errors

Always launch the app from the project root:

```powershell
cd "C:\01. Development\translate_poedit"
streamlit run src/app.py
```

### Port conflict

Run Streamlit on a different port:

```powershell
streamlit run src/app.py --server.port 8502
```

## Recommended startup commands

### Day-to-day frontend use

```powershell
cd "C:\01. Development\translate_poedit"
.\venv\Scripts\Activate.ps1
streamlit run src/app.py
```

### Quick restart

```powershell
cd "C:\01. Development\translate_poedit"
"C:/01. Development/translate_poedit/venv/Scripts/python.exe" -m streamlit run src/app.py
```
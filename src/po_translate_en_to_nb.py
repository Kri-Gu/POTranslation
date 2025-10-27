#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Translate English -> Norwegian Bokmål in a .po file using OpenAI's API.

- Preserves: comments, msgctxt, metadata, placeholders, punctuation, capitalization, HTML tags.
- Policy: If msgstr has English, translate it. If msgstr is empty and msgid looks English,
  translate the msgid. Otherwise leave untouched.
- Outputs UTF-8 .po ready for Poedit.

Usage:
  python po_translate_en_to_nb.py input.po output.po --model gpt-4o
"""

import os
import re
import json
import argparse
from typing import List, Dict
import polib
from tenacity import retry, stop_after_attempt, wait_exponential
from tqdm import tqdm

# ---- Simple heuristic to guess if a string is English-looking (ASCII + common words) ----
_EN_HINTS = re.compile(r"\b(accept|settings|cookie|filter|configure|products?|reviews?|customer|archive|example|save|cancel|next|previous|email|password|sign|log|home|about|contact|help)\b", re.I)

def looks_english(s: str) -> bool:
    """Check if a string looks like English text."""
    if not s:
        return False
    # ASCII-ish and/or contains common English UI words
    asciiish = all(ord(c) < 128 for c in s)
    return asciiish and bool(_EN_HINTS.search(s))


# Simple heuristic to guess if a string looks like German (contains umlauts or common words)
_DE_HINTS = re.compile(r"\b(der|die|das|und|ist|nicht|für|mit|ein|eine|zu|von|auf|als|auch)\b", re.I)

def looks_german(s: str) -> bool:
    if not s:
        return False
    # presence of German-specific characters or common German words
    if any(ch in s for ch in ("ä", "ö", "ü", "ß", "Ä", "Ö", "Ü")):
        return True
    return bool(_DE_HINTS.search(s))

# ---- OpenAI client ----
try:
    from openai import OpenAI
    client = OpenAI()
except Exception as e:
    raise SystemExit("OpenAI SDK not installed or import failed. Run: pip install openai") from e

def make_prompt(pairs: List[Dict[str, str]], target_lang: str = "nb") -> str:
    """
    We send a batch of items; each has "id" and "text".
    The model must return a JSON array of {"id": ..., "translation": ...}.
    """
    lang_map = {
        "nb": "Norwegian Bokmål",
        "sv": "Swedish",
        "da": "Danish",
    }
    target_name = lang_map.get(target_lang, target_lang)

    instructions = (
        f"You are translating UI strings to {target_name} ({target_lang}). The source language for each item may be English or German; use the provided `lang` field for each item and translate from that language into the target language.\n"
        "Rules (strictly enforce):\n"
        "1) Translate to **Norwegian Bokmål** only.\n"
        "2) **Preserve placeholders** exactly: printf-style (%s, %d, %% …), Python/ICU ({name}, {0}), HTML tags, URLs.\n"
    "3) **Do not change capitalization or punctuation** unless required by the target language grammar for the same casing style (e.g., title case stays title case).\n"
    f"4) Keep technical terms consistent and natural for standard {target_name}.\n"
        "5) Return **valid JSON** ONLY: a list of objects with keys `id` and `translation`.\n"
        "6) Do not add extra keys. Do not wrap in markdown.\n"
    )
    # Provide examples tailored for the requested target language when possible
    if target_lang == "nb":
        examples = [
            {"id": "1", "text": "Accept All", "lang": "en", "translation": "Godta alle"},
            {"id": "2", "text": "Cookie Settings", "lang": "en", "translation": "Innstillinger for informasjonskapsler"},
            {"id": "3", "text": "Kundenstimmen - Archiv", "lang": "de", "translation": "Arkiv for kundeanmeldelser"},
        ]
    elif target_lang == "sv":
        examples = [
            {"id": "1", "text": "Accept All", "lang": "en", "translation": "Acceptera alla"},
            {"id": "2", "text": "Cookie Settings", "lang": "en", "translation": "Cookie-inställningar"},
            {"id": "3", "text": "Kundenstimmen - Archiv", "lang": "de", "translation": "Arkiv för kundomdömen"},
        ]
    elif target_lang == "da":
        examples = [
            {"id": "1", "text": "Accept All", "lang": "en", "translation": "Accepter alle"},
            {"id": "2", "text": "Cookie Settings", "lang": "en", "translation": "Cookie-indstillinger"},
            {"id": "3", "text": "Kundenstimmen - Archiv", "lang": "de", "translation": "Arkiv for kundeanmeldelser"},
        ]
    else:
        examples = [
            {"id": "1", "text": "Accept All", "lang": "en", "translation": "Accept All"},
        ]
    payload = {
        "instructions": instructions,
        "examples": examples,
        "items": pairs,
        "target_lang": target_lang,
    }
    return json.dumps(payload, ensure_ascii=False)

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=20))
def call_model(batch: List[Dict[str, str]], model: str, target_lang: str = "nb") -> Dict[str, str]:
    """
    Send a batch to the model and get back a dict id -> translation.
    Retries on transient errors.
    """
    prompt_json = make_prompt(batch, target_lang=target_lang)

    # Build request payload for the model
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You translate UI strings. Return only valid JSON without markdown formatting."
                },
                {
                    "role": "user",
                    "content": prompt_json
                },
            ],
            temperature=0.2,
        )
    except Exception:
        # Let tenacity handle retries for transport-level errors
        raise

    # Try multiple ways to extract text from the response
    text = None
    try:
        # Some SDK versions provide different fields; try several common ones
        # 1) direct output_text (Responses API)
        if hasattr(resp, "output_text") and getattr(resp, "output_text"):
            text = getattr(resp, "output_text")
        # 2) choices -> message -> content (ChatCompletion-like)
        elif getattr(resp, "choices", None):
            choice = resp.choices[0]
            if hasattr(choice, "message") and getattr(choice.message, "content", None):
                text = getattr(choice.message, "content")
            elif isinstance(choice, dict):
                if "message" in choice and isinstance(choice["message"], dict) and "content" in choice["message"]:
                    text = choice["message"]["content"]
                elif "text" in choice:
                    text = choice["text"]
        # 3) top-level 'text' field
        elif getattr(resp, "text", None):
            text = getattr(resp, "text")
    except Exception:
        text = None

    # As a last resort, stringify the whole response
    if not text:
        try:
            text = str(resp)
        except Exception:
            text = None

    if not text:
        # Log raw response for debugging and raise
        with open("raw_responses.log", "a", encoding="utf-8") as f:
            f.write("--- MISSING TEXT RESPONSE ---\n")
            f.write(repr(resp))
            f.write("\n\n")
        raise TypeError("Model response contained no text/content")

    # Expecting pure JSON (list of {"id":..., "translation":...})
    try:
        data = json.loads(text)
    except Exception:
        # Try to extract a JSON substring from text
        import re as _re

        m = _re.search(r"(\[\s*\{.*\}\s*\])", text, _re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
            except Exception:
                data = None
        else:
            data = None

    if data is None:
        # Save the raw text for debugging
        with open("raw_responses.log", "a", encoding="utf-8") as f:
            f.write("--- UNPARSABLE RESPONSE ---\n")
            f.write(text)
            f.write("\n\n")
        raise TypeError("Failed to parse JSON from model response")

    # Handle both direct list format and wrapped format
    if isinstance(data, dict) and "translations" in data:
        data = data["translations"]
    elif isinstance(data, dict) and "items" in data:
        data = data["items"]

    # Final normalization: expect a list of objects with id/translation
    result = {}
    for item in data:
        try:
            result[str(item["id"])]= item.get("translation") if isinstance(item, dict) else None
        except Exception:
            continue

    return result

def chunked(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

def main():
    parser = argparse.ArgumentParser(description="Translate PO files using OpenAI API")
    parser.add_argument("input_po", help="Input .po file path")
    parser.add_argument("output_po", help="Output .po file path")
    parser.add_argument("--model", default="gpt-4o", help="OpenAI model (default: gpt-4o)")
    parser.add_argument("--batch-size", type=int, default=50, help="Items per API call (default: 50)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--force", action="store_true", help="Translate all entries (use msgstr if present, otherwise msgid)")
    parser.add_argument("--source-lang", choices=("auto","en","de"), default="auto",
                        help="Source language: auto (detect per-entry), en (force English->target), de (force German->target)")
    parser.add_argument("--target-lang", choices=("nb","sv","da"), default="nb",
                        help="Target language: nb (Norwegian Bokmål), sv (Swedish), da (Danish)")
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Please set OPENAI_API_KEY environment variable")

    if args.verbose:
        print(f"Loading PO file: {args.input_po}")
    
    try:
        po = polib.pofile(args.input_po, encoding="utf-8")
    except Exception as e:
        raise SystemExit(f"Failed to load PO file: {e}")

    # Build full translation worklist first so we can show progress
    work_items = []  # list of {"id": str, "text": str}
    id_map = {}      # tmp_id -> (entry, source_field)
    id_counter = 0
    total_entries = 0
    translated_count = 0

    for entry in po:
        # Skip header entry
        if entry.msgid == "":
            continue

        total_entries += 1

        text_to_translate = None
        source_field = None

        # Determine source text and field depending on source-lang and heuristics
        # Priority rules:
        # - if --source-lang=en => prefer msgstr if present and English, else msgid if English
        # - if --source-lang=de => translate msgid (German)
        # - if auto => prefer msgstr when it looks like English; else if msgid looks German translate msgid; else fall back to msgid
        if args.force:
            # Force translation: prefer msgstr if present, otherwise msgid
            if entry.msgstr:
                text_to_translate = entry.msgstr
                source_field = "msgstr"
            else:
                text_to_translate = entry.msgid
                source_field = "msgid"
        else:
            if args.source_lang == "en":
                if entry.msgstr and looks_english(entry.msgstr):
                    text_to_translate = entry.msgstr
                    source_field = "msgstr"
                elif looks_english(entry.msgid):
                    text_to_translate = entry.msgid
                    source_field = "msgid"
            elif args.source_lang == "de":
                # Treat msgid as German source always
                text_to_translate = entry.msgid
                source_field = "msgid"
            else:  # auto
                if entry.msgstr and looks_english(entry.msgstr):
                    text_to_translate = entry.msgstr
                    source_field = "msgstr"
                elif looks_german(entry.msgid):
                    text_to_translate = entry.msgid
                    source_field = "msgid"
                else:
                    # fallback: if msgstr is present but not English, assume it's the desired source; otherwise use msgid
                    if entry.msgstr:
                        text_to_translate = entry.msgstr
                        source_field = "msgstr"
                    else:
                        text_to_translate = entry.msgid
                        source_field = "msgid"

        if text_to_translate:
            id_counter += 1
            tmp_id = f"{id_counter}"
            # include detected source language for the item to guide the model
            detected_lang = "de" if looks_german(text_to_translate) and not looks_english(text_to_translate) else "en"
            work_items.append({"id": tmp_id, "text": text_to_translate, "lang": detected_lang})
            id_map[tmp_id] = (entry, source_field)

    total_to_translate = len(work_items)
    if args.verbose:
        print(f"Total entries in file: {total_entries}")
        print(f"Entries to translate: {total_to_translate}")

    # Process in batches and show a progress bar
    pbar = None
    if not args.verbose:
        pbar = tqdm(total=total_to_translate, desc="Translating", unit="items")

    for batch in chunked(work_items, args.batch_size):
        if args.verbose:
            print(f"Translating batch of {len(batch)} entries...")

        try:
            translations = call_model(batch, args.model, target_lang=args.target_lang)
            for tid, trans in translations.items():
                e, src = id_map[tid]
                e.msgstr = trans
                translated_count += 1
        except Exception as e:
            # Batch failed: attempt per-item fallback and log failures
            print(f"Warning: Failed to translate batch: {e}")
            failed = []
            for item in batch:
                try:
                    single_trans = call_model([item], args.model, target_lang=args.target_lang)
                    # single_trans is dict id->translation
                    for tid, trans in single_trans.items():
                        e, src = id_map[tid]
                        e.msgstr = trans
                        translated_count += 1
                except Exception as single_e:
                    # Log failed item for later inspection
                    failed.append({
                        "id": item.get("id"),
                        "text": item.get("text"),
                        "error": str(single_e),
                    })
                    with open("failed_items.log", "a", encoding="utf-8") as f:
                        f.write(json.dumps(failed[-1], ensure_ascii=False) + "\n")

        # Update progress display
        # We update by the number of items in this batch that now have msgstr values
        if pbar is not None:
            # advance by number of items attempted in this batch
            pbar.update(len(batch))
        elif args.verbose:
            print(f"Translated so far: {translated_count}/{total_to_translate}")

    # Close progress bar and show final summary
    if pbar is not None:
        pbar.close()

    print(f"✅ Successfully translated {translated_count}/{total_to_translate} entries")

    # Save output as UTF-8
    try:
        po.save(args.output_po)
        print(f"✅ Successfully translated {translated_count}/{total_entries} entries")
        print(f"✅ Wrote: {args.output_po}")
    except Exception as e:
        raise SystemExit(f"Failed to save output file: {e}")

if __name__ == "__main__":
    main()
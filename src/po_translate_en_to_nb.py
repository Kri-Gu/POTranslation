#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Translate .po file UI strings using the OpenAI API.

Supports English and German source text → Norwegian Bokmål / Swedish / Danish.

- Preserves: comments, msgctxt, metadata, placeholders, punctuation, capitalization, HTML tags.
- Validates that placeholders survive translation and warns if any are dropped.
- Uses JSON mode for reliable structured API responses.
- Accepts a domain context file (--context-file) for specialised terminology.

Usage:
  python po_translate_en_to_nb.py input.po output.po --model gpt-4.1 --context-file context.json
"""

import os
import re
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Set, Any
import polib
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from tqdm import tqdm

# Load .env from project root (searches upward from this file)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

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

# ---- Placeholder extraction & validation ----
_PLACEHOLDER_RE = re.compile(
    r"(%(?:\d+\$)?[-+0 #]*(?:\d+|\*)?(?:\.(?:\d+|\*))?[hlLqjzt]*[diouxXeEfFgGaAcspn%])"
    r"|(%@)"
    r"|(\{\w*\})"
    r"|(<[^>]+>)"
    r"|(\[\/?[^\]]+\])"
    r"|(https?://\S+)",
    re.IGNORECASE,
)

def extract_placeholders(text: str) -> List[str]:
    """Extract all placeholders, HTML tags, and URLs from text."""
    return [m.group() for m in _PLACEHOLDER_RE.finditer(text)]

def validate_placeholders(source: str, translation: str) -> List[str]:
    """Return list of placeholders present in source but missing in translation."""
    src_ph = extract_placeholders(source)
    if not src_ph:
        return []
    missing = []
    for ph in src_ph:
        if ph not in translation:
            missing.append(ph)
    return missing

# ---- Context loading ----
def load_context(context_path: Optional[str] = None) -> str:
    """Load domain context from a file (plain text or JSON)."""
    if not context_path:
        return ""
    p = Path(context_path)
    if not p.exists():
        print(f"Warning: Context file not found: {context_path}")
        return ""
    text = p.read_text(encoding="utf-8").strip()
    # If it looks like JSON, try to extract just the instructional text
    if text.startswith("{") or text.startswith("["):
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "instructions" in data:
                return data["instructions"]
        except json.JSONDecodeError:
            pass
    return text

# ---- OpenAI client ----
try:
    from openai import OpenAI
    client = OpenAI()
except Exception as e:
    raise SystemExit("OpenAI SDK not installed or import failed. Run: pip install openai") from e

def make_system_prompt(target_lang: str = "nb", domain_context: str = "") -> str:
    """
    Build a rich system prompt that tells the model exactly how to behave.
    """
    lang_map = {
        "nb": "Norwegian Bokmål",
        "sv": "Swedish",
        "da": "Danish",
    }
    target_name = lang_map.get(target_lang, target_lang)

    parts = [
        f"You are an expert translator specialising in {target_name} ({target_lang}).",
        "You translate UI strings and technical content from English or German into the target language.",
        "The source language for each item is indicated by its `lang` field.",
        "",
        "=== RULES (strictly enforce) ===",
        f"1) Translate into {target_name} ONLY. Every translation must be in {target_name}.",
        "2) Preserve ALL placeholders exactly as they appear: printf-style (%s, %d, %1$s, %% …), Python/ICU ({name}, {0}), HTML tags (<b>, </b>, <a href=\"...\">), BBCode-style tags ([button], [/button]), and URLs.",
        "3) Match the source string's capitalization style (title case → title case, sentence case → sentence case) unless target-language grammar requires otherwise.",
        "4) Preserve the same punctuation and whitespace pattern (trailing periods, colons, spaces).",
        f"5) Use natural, idiomatic {target_name}. Prefer standard terminology over literal word-for-word translation.",
        "6) For technical/product terms with no established translation, keep the original term.",
        "7) Return ONLY a valid JSON object: {\"translations\": [{\"id\": \"…\", \"translation\": \"…\"}, …]}",
        "8) Do NOT add extra keys, markdown formatting, or commentary.",
    ]

    if domain_context:
        parts.append("")
        parts.append("=== DOMAIN CONTEXT ===")
        parts.append("The content you are translating relates to the following domain. Use this context to choose accurate terminology:")
        parts.append(domain_context)

    return "\n".join(parts)


def make_user_prompt(pairs: List[Dict[str, str]], target_lang: str = "nb") -> str:
    """
    Build the user message containing items to translate, with few-shot examples.
    """
    lang_map = {
        "nb": "Norwegian Bokmål",
        "sv": "Swedish",
        "da": "Danish",
    }
    target_name = lang_map.get(target_lang, target_lang)

    # Provide examples tailored for the requested target language
    if target_lang == "nb":
        examples = {
            "translations": [
                {"id": "ex1", "translation": "Godta alle"},
                {"id": "ex2", "translation": "Innstillinger for informasjonskapsler"},
                {"id": "ex3", "translation": "Arkiv for kundeanmeldelser"},
                {"id": "ex4", "translation": "Velg %s produkter"},
            ]
        }
        example_items = [
            {"id": "ex1", "text": "Accept All", "lang": "en"},
            {"id": "ex2", "text": "Cookie Settings", "lang": "en"},
            {"id": "ex3", "text": "Kundenstimmen - Archiv", "lang": "de"},
            {"id": "ex4", "text": "Select %s products", "lang": "en"},
        ]
    elif target_lang == "sv":
        examples = {
            "translations": [
                {"id": "ex1", "translation": "Acceptera alla"},
                {"id": "ex2", "translation": "Cookie-inställningar"},
                {"id": "ex3", "translation": "Arkiv för kundomdömen"},
            ]
        }
        example_items = [
            {"id": "ex1", "text": "Accept All", "lang": "en"},
            {"id": "ex2", "text": "Cookie Settings", "lang": "en"},
            {"id": "ex3", "text": "Kundenstimmen - Archiv", "lang": "de"},
        ]
    elif target_lang == "da":
        examples = {
            "translations": [
                {"id": "ex1", "translation": "Accepter alle"},
                {"id": "ex2", "translation": "Cookie-indstillinger"},
                {"id": "ex3", "translation": "Arkiv for kundeanmeldelser"},
            ]
        }
        example_items = [
            {"id": "ex1", "text": "Accept All", "lang": "en"},
            {"id": "ex2", "text": "Cookie Settings", "lang": "en"},
            {"id": "ex3", "text": "Kundenstimmen - Archiv", "lang": "de"},
        ]
    else:
        examples = {"translations": [{"id": "ex1", "translation": "Accept All"}]}
        example_items = [{"id": "ex1", "text": "Accept All", "lang": "en"}]

    prompt_parts = [
        f"Translate the following items into {target_name}.",
        "",
        "--- EXAMPLE ---",
        "Input items:",
        json.dumps(example_items, ensure_ascii=False),
        "Expected output:",
        json.dumps(examples, ensure_ascii=False),
        "--- END EXAMPLE ---",
        "",
        "Now translate these items:",
        json.dumps(pairs, ensure_ascii=False),
    ]
    return "\n".join(prompt_parts)

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=20))
def call_model(
    batch: List[Dict[str, str]],
    model: str,
    target_lang: str = "nb",
    domain_context: str = "",
) -> Dict[str, str]:
    """
    Send a batch to the model and get back a dict id -> translation.
    Uses JSON mode for reliable structured output. Retries on transient errors.
    """
    system_prompt = make_system_prompt(target_lang=target_lang, domain_context=domain_context)
    user_prompt = make_user_prompt(batch, target_lang=target_lang)

    # Build request payload — use JSON mode for guaranteed valid JSON
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    # Cast for OpenAI SDK type checker compatibility
    typed_messages: Any = messages

    try:
        # gpt-5.x models use max_completion_tokens; older models use max_tokens
        if model.startswith("gpt-5"):
            resp = client.chat.completions.create(
                model=model,
                messages=typed_messages,
                temperature=0.1,
                response_format={"type": "json_object"},
                max_completion_tokens=4096,
            )
        else:
            resp = client.chat.completions.create(
                model=model,
                messages=typed_messages,
                temperature=0.1,
                response_format={"type": "json_object"},
                max_tokens=4096,
            )
    except Exception:
        # Let tenacity handle retries for transport-level errors
        raise

    # With JSON mode the response is always in choices[0].message.content
    text = None
    try:
        text = resp.choices[0].message.content
    except (AttributeError, IndexError, TypeError):
        pass

    if not text:
        with open("raw_responses.log", "a", encoding="utf-8") as f:
            f.write("--- MISSING TEXT RESPONSE ---\n")
            f.write(repr(resp))
            f.write("\n\n")
        raise TypeError("Model response contained no text/content")

    # Parse JSON — should always be valid thanks to JSON mode
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Fallback: try to extract a JSON substring
        m = re.search(r"(\{.*\})", text, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
            except json.JSONDecodeError:
                data = None
        else:
            data = None

    if data is None:
        with open("raw_responses.log", "a", encoding="utf-8") as f:
            f.write("--- UNPARSABLE RESPONSE ---\n")
            f.write(text)
            f.write("\n\n")
        raise TypeError("Failed to parse JSON from model response")

    # Normalise: accept {"translations": [...]}, {"items": [...]}, or bare [...]
    if isinstance(data, dict):
        if "translations" in data:
            data = data["translations"]
        elif "items" in data:
            data = data["items"]
        else:
            # Try the first list-valued key
            for v in data.values():
                if isinstance(v, list):
                    data = v
                    break

    if not isinstance(data, list):
        raise TypeError(f"Expected a list of translation objects, got {type(data).__name__}")

    result = {}
    for item in data:
        try:
            result[str(item["id"])] = item.get("translation") if isinstance(item, dict) else None
        except Exception:
            continue

    return result

def chunked(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i+n]


# ---- Available models (ordered by recommendation) ----
AVAILABLE_MODELS = [
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4.1-nano",
    "gpt-5.2",
    "gpt-4o",
    "gpt-4o-mini",
]

TARGET_LANGUAGES = {
    "nb": "Norwegian Bokmål",
    "sv": "Swedish",
    "da": "Danish",
}

SOURCE_LANGUAGES = ["auto", "en", "de"]

# Map common aliases to our canonical language codes
_LANG_ALIASES = {
    "no": "nb", "norwegian": "nb", "norsk": "nb",
    "se": "sv", "swedish": "sv", "svenska": "sv",
    "dk": "da", "danish": "da", "dansk": "da",
}


def _normalise_lang(code: str) -> str:
    """Map common aliases (no, dk, se) to canonical codes (nb, da, sv)."""
    return _LANG_ALIASES.get(code.lower().strip(), code.lower().strip())


def get_defaults() -> Dict:
    """
    Read user defaults from environment / .env file.
    Returns a dict with resolved defaults, falling back to hardcoded values.
    """
    raw_target = os.getenv("DEFAULT_TARGET_LANGUAGE", "nb")
    raw_source = os.getenv("DEFAULT_SOURCE_LANGUAGE", "auto")
    model = os.getenv("DEFAULT_MODEL", "gpt-4.1")
    batch = os.getenv("BATCH_SIZE", "20")
    context = os.getenv("DEFAULT_CONTEXT_FILE", "")

    target = _normalise_lang(raw_target)
    source = raw_source.lower().strip() if raw_source in SOURCE_LANGUAGES else "auto"
    if target not in TARGET_LANGUAGES:
        target = "nb"

    try:
        batch_int = int(batch)
    except ValueError:
        batch_int = 20

    return {
        "model": model if model in AVAILABLE_MODELS else "gpt-4.1",
        "target_lang": target,
        "source_lang": source,
        "batch_size": batch_int,
        "context_file": context or None,
    }


def build_work_items(po, source_lang: str = "auto", force: bool = False):
    """
    Scan a polib PO object and return (work_items, id_map, total_entries).

    work_items: list of {"id": str, "text": str, "lang": str}
    id_map:     dict  tmp_id -> (entry, source_field)
    total_entries: int  total non-header entries scanned
    """
    work_items = []
    id_map = {}
    id_counter = 0
    total_entries = 0

    for entry in po:
        if entry.msgid == "":
            continue
        total_entries += 1

        text_to_translate = None
        source_field = None

        if force:
            if entry.msgstr:
                text_to_translate = entry.msgstr
                source_field = "msgstr"
            else:
                text_to_translate = entry.msgid
                source_field = "msgid"
        else:
            if source_lang == "en":
                if entry.msgstr and looks_english(entry.msgstr):
                    text_to_translate = entry.msgstr
                    source_field = "msgstr"
                elif looks_english(entry.msgid):
                    text_to_translate = entry.msgid
                    source_field = "msgid"
            elif source_lang == "de":
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
                    if entry.msgstr:
                        text_to_translate = entry.msgstr
                        source_field = "msgstr"
                    else:
                        text_to_translate = entry.msgid
                        source_field = "msgid"

        if text_to_translate:
            id_counter += 1
            tmp_id = f"{id_counter}"
            detected_lang = "de" if looks_german(text_to_translate) and not looks_english(text_to_translate) else "en"
            work_items.append({"id": tmp_id, "text": text_to_translate, "lang": detected_lang})
            id_map[tmp_id] = (entry, source_field)

    return work_items, id_map, total_entries


def translate_po_file(
    input_path: str,
    output_path: str,
    *,
    model: str = "gpt-4.1",
    batch_size: int = 20,
    target_lang: str = "nb",
    source_lang: str = "auto",
    force: bool = False,
    context_file: Optional[str] = None,
    progress_callback=None,
    log_callback=None,
) -> Dict:
    """
    Core translation function usable by both CLI and GUI.

    Args:
        progress_callback: callable(translated_so_far, total) — called after each batch.
        log_callback:      callable(message) — called for status messages.

    Returns a dict with summary info:
        {"translated": int, "total_entries": int, "total_to_translate": int,
         "placeholder_warnings": list, "failed": list}
    """
    def _log(msg):
        if log_callback:
            log_callback(msg)

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Please set OPENAI_API_KEY environment variable")

    domain_context = load_context(context_file)
    if domain_context:
        _log(f"Loaded domain context ({len(domain_context)} chars)")

    _log(f"Model: {model} | Batch size: {batch_size} | Target: {target_lang}")

    try:
        po = polib.pofile(input_path, encoding="utf-8")
    except Exception as e:
        raise RuntimeError(f"Failed to load PO file: {e}")

    work_items, id_map, total_entries = build_work_items(po, source_lang=source_lang, force=force)
    total_to_translate = len(work_items)
    _log(f"Entries in file: {total_entries} | To translate: {total_to_translate}")

    translated_count = 0
    placeholder_warnings = []
    failed_items = []

    for batch in chunked(work_items, batch_size):
        try:
            translations = call_model(batch, model, target_lang=target_lang, domain_context=domain_context)
            for tid, trans in translations.items():
                if trans is None:
                    continue
                entry_obj, _src = id_map[tid]
                orig_text = next((it["text"] for it in batch if it["id"] == tid), "")
                missing_ph = validate_placeholders(orig_text, trans)
                if missing_ph:
                    placeholder_warnings.append({
                        "id": tid, "source": orig_text,
                        "translation": trans, "missing": missing_ph,
                    })
                entry_obj.msgstr = trans
                translated_count += 1
        except Exception as e:
            _log(f"Batch failed ({e}), retrying individually…")
            for item in batch:
                try:
                    single_trans = call_model([item], model, target_lang=target_lang, domain_context=domain_context)
                    for tid, trans in single_trans.items():
                        if trans is None:
                            continue
                        entry_obj, _src = id_map[tid]
                        missing_ph = validate_placeholders(item["text"], trans)
                        if missing_ph:
                            placeholder_warnings.append({
                                "id": tid, "source": item["text"],
                                "translation": trans, "missing": missing_ph,
                            })
                        entry_obj.msgstr = trans
                        translated_count += 1
                except Exception as single_e:
                    failed_items.append({
                        "id": item.get("id"), "text": item.get("text"),
                        "error": str(single_e),
                    })

        if progress_callback:
            progress_callback(translated_count, total_to_translate)

    # Save
    po.save(output_path)

    return {
        "translated": translated_count,
        "total_entries": total_entries,
        "total_to_translate": total_to_translate,
        "placeholder_warnings": placeholder_warnings,
        "failed": failed_items,
        "output_path": output_path,
    }


def main():
    defaults = get_defaults()

    parser = argparse.ArgumentParser(description="Translate PO files using OpenAI API")
    parser.add_argument("input_po", help="Input .po file path")
    parser.add_argument("output_po", help="Output .po file path")
    parser.add_argument("--model", default=defaults["model"],
                        help=f"OpenAI model (default: {defaults['model']}, from .env DEFAULT_MODEL)")
    parser.add_argument("--batch-size", type=int, default=defaults["batch_size"],
                        help=f"Items per API call (default: {defaults['batch_size']}, from .env BATCH_SIZE)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--force", action="store_true", help="Translate all entries (use msgstr if present, otherwise msgid)")
    parser.add_argument("--source-lang", choices=("auto","en","de"), default=defaults["source_lang"],
                        help=f"Source language (default: {defaults['source_lang']}, from .env DEFAULT_SOURCE_LANGUAGE)")
    parser.add_argument("--target-lang", choices=tuple(TARGET_LANGUAGES.keys()), default=defaults["target_lang"],
                        help=f"Target language (default: {defaults['target_lang']}, from .env DEFAULT_TARGET_LANGUAGE)")
    parser.add_argument("--context-file", default=defaults["context_file"],
                        help="Path to a context file with domain-specific instructions (from .env DEFAULT_CONTEXT_FILE)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be translated without making API calls")
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Please set OPENAI_API_KEY environment variable")

    # --- Dry run: preview only, no API calls ---
    if args.dry_run:
        domain_context = load_context(args.context_file)
        try:
            po = polib.pofile(args.input_po, encoding="utf-8")
        except Exception as e:
            raise SystemExit(f"Failed to load PO file: {e}")
        work_items, _id_map, total_entries = build_work_items(po, source_lang=args.source_lang, force=args.force)
        total_to_translate = len(work_items)
        print(f"\n=== DRY RUN ===")
        print(f"Would translate {total_to_translate} / {total_entries} entries")
        print(f"Model: {args.model} | Batch size: {args.batch_size} | Target: {args.target_lang}")
        print(f"Estimated API calls: {(total_to_translate + args.batch_size - 1) // args.batch_size}")
        if domain_context:
            print(f"Domain context: {args.context_file} ({len(domain_context)} chars)")
        print("\nFirst 10 items that would be translated:")
        for item in work_items[:10]:
            print(f"  [{item['lang']}] {item['text'][:80]}")
        return

    # --- Real run with tqdm progress ---
    pbar = None

    def cli_progress(translated, total):
        nonlocal pbar
        if pbar is None:
            pbar = tqdm(total=total, desc="Translating", unit="items")
        pbar.n = translated
        pbar.refresh()

    def cli_log(msg):
        if args.verbose:
            print(msg)

    try:
        result = translate_po_file(
            args.input_po,
            args.output_po,
            model=args.model,
            batch_size=args.batch_size,
            target_lang=args.target_lang,
            source_lang=args.source_lang,
            force=args.force,
            context_file=args.context_file,
            progress_callback=cli_progress if not args.verbose else None,
            log_callback=cli_log,
        )
    finally:
        if pbar is not None:
            pbar.close()

    # --- Summary ---
    print(f"\n✅ Successfully translated {result['translated']}/{result['total_to_translate']} entries")

    if result["placeholder_warnings"]:
        print(f"\n⚠️  {len(result['placeholder_warnings'])} translation(s) have missing placeholders:")
        for pw in result["placeholder_warnings"][:20]:
            print(f"  ID {pw['id']}: missing {pw['missing']}")
            print(f"    Source:      {pw['source'][:80]}")
            print(f"    Translation: {pw['translation'][:80]}")
        if len(result["placeholder_warnings"]) > 20:
            print(f"  ... and {len(result['placeholder_warnings']) - 20} more.")
        with open("placeholder_warnings.log", "w", encoding="utf-8") as f:
            for pw in result["placeholder_warnings"]:
                f.write(json.dumps(pw, ensure_ascii=False) + "\n")
        print("  Full list saved to placeholder_warnings.log")

    if result["failed"]:
        with open("failed_items.log", "a", encoding="utf-8") as f:
            for fi in result["failed"]:
                f.write(json.dumps(fi, ensure_ascii=False) + "\n")
        print(f"⚠️  {len(result['failed'])} item(s) failed — see failed_items.log")

    print(f"✅ Wrote: {result['output_path']}")

if __name__ == "__main__":
    main()
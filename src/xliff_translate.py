#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Translate XLIFF 1.2 (.xlf) files using the OpenAI API.

XLIFF (XML Localization Interchange File Format) files are XML files containing
<trans-unit> elements. Each has a <source> (text to translate) and an optional
<target> (translated result). The <source> may be plain text or contain inline
XLIFF <g> codes representing HTML markup — both are handled correctly.

Usage (CLI):
  python xliff_translate.py input.xlf output.xlf --target-lang nb --model gpt-4.1

Usage (imported):
  from src.xliff_translate import translate_xliff_file
"""

import os
import re
import json
import copy
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

# ── Project root / env ────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# ── Namespace constants ────────────────────────────────────────────────────────
XLIFF_NS  = "urn:oasis:names:tc:xliff:document:1.2"
XHTML_NS  = "http://www.w3.org/1999/xhtml"
XSI_NS    = "http://www.w3.org/2001/XMLSchema-instance"

# Register so ET serialises with proper prefixes (default ns = no prefix)
ET.register_namespace("",      XLIFF_NS)
ET.register_namespace("xhtml", XHTML_NS)
ET.register_namespace("xsi",   XSI_NS)

# Clark-notation shorthand
def _q(tag: str) -> str:
    return f"{{{XLIFF_NS}}}{tag}"


# ── Re-use shared objects from the PO translator ──────────────────────────────
from src.po_translate_en_to_nb import (
    AVAILABLE_MODELS,
    TARGET_LANGUAGES,
    SOURCE_LANGUAGES,
    load_context,
    get_defaults,
    _normalise_lang,
    chunked,
    client,          # already-initialised OpenAI client
    format_glossary_for_prompt,
    _REGISTER_NOTES,
)

# ── XML helpers ───────────────────────────────────────────────────────────────

def _inner_xml(element: ET.Element) -> str:
    """
    Return the *inner* XML/text of an element (everything between its opening
    and closing tags), as a Unicode string.

    ElementTree includes .tail on each child inside tostring(), so we only
    need element.text + the serialised children.
    """
    parts: List[str] = [element.text or ""]
    for child in element:
        # tostring includes child.tail automatically
        parts.append(ET.tostring(child, encoding="unicode"))
    return "".join(parts)


def _extract_plain_text(element: ET.Element) -> str:
    """Recursively collect all text nodes from an element (ignores tags)."""
    parts: List[str] = []
    if element.text:
        parts.append(element.text.strip())
    for child in element:
        child_text = _extract_plain_text(child)
        if child_text:
            parts.append(child_text)
        if child.tail and child.tail.strip():
            parts.append(child.tail.strip())
    return " ".join(p for p in parts if p)


def _has_children(element: ET.Element) -> bool:
    return len(element) > 0


def _set_target_content(
    trans_unit_el: ET.Element,
    translated: str,
    source_el: ET.Element,
) -> ET.Element:
    """
    Insert (or replace) a <target> element in *trans_unit_el* containing
    the translated content.  Mirrors the structure of <source> when it
    contains <g> markup.
    """
    # Remove any pre-existing <target>
    existing = trans_unit_el.find(_q("target"))
    if existing is not None:
        trans_unit_el.remove(existing)

    target_el = ET.Element(_q("target"))
    target_el.set("state", "translated")

    if "<" in translated:
        # The AI returned XML – parse it safely inside a wrapper element
        try:
            wrapper_xml = (
                f'<_root_ xmlns="{XLIFF_NS}" '
                f'xmlns:xhtml="{XHTML_NS}" '
                f'xmlns:xsi="{XSI_NS}">'
                f"{translated}"
                f"</_root_>"
            )
            wrapper = ET.fromstring(wrapper_xml)
            target_el.text = wrapper.text
            for child in list(wrapper):
                # Preserve tail text (text after a closing tag within the same parent)
                target_el.append(child)
        except ET.ParseError:
            # XML parsing failed – write as plain text fallback
            target_el.text = re.sub(r"<[^>]+>", "", translated).strip()
    else:
        target_el.text = translated

    # Insert immediately after <source>
    children = list(trans_unit_el)
    src_idx = next(
        (i for i, c in enumerate(children) if c.tag == _q("source")), -1
    )
    if src_idx >= 0:
        trans_unit_el.insert(src_idx + 1, target_el)
    else:
        trans_unit_el.append(target_el)

    return target_el


# ── Work-item extraction ───────────────────────────────────────────────────────

def build_work_items_xliff(
    tree: ET.ElementTree,
    source_lang: str = "auto",
    force: bool = False,
) -> Tuple[List[Dict], Dict[str, Tuple], int]:
    """
    Walk the XLIFF ElementTree and collect items that need translating.

    Returns
    -------
    work_items   : list of dicts  {"id", "text", "source_xml", "has_markup", "lang"}
    id_map       : dict  str → (source_el, trans_unit_el)
    total_entries: int   total <trans-unit> elements found
    """
    root = tree.getroot()
    work_items: List[Dict] = []
    id_map: Dict[str, Tuple] = {}
    total_entries = 0
    counter = 0

    for file_el in root.iter(_q("file")):
        body = file_el.find(_q("body"))
        if body is None:
            continue

        for trans_unit in body.iter(_q("trans-unit")):
            source_el = trans_unit.find(_q("source"))
            if source_el is None:
                continue

            total_entries += 1

            # Skip already-translated entries unless force=True
            target_el = trans_unit.find(_q("target"))
            if not force and target_el is not None:
                target_content = _extract_plain_text(target_el) if _has_children(target_el) else (target_el.text or "")
                if target_content.strip():
                    continue

            has_markup = _has_children(source_el)
            source_xml = _inner_xml(source_el).strip()

            if has_markup:
                plain_text = _extract_plain_text(source_el)
            else:
                plain_text = (source_el.text or "").strip()

            if not plain_text:
                continue

            counter += 1
            tmp_id = str(counter)

            work_items.append(
                {
                    "id":         tmp_id,
                    "text":       plain_text[:300],   # for display / batching heuristic
                    "source_xml": source_xml,
                    "has_markup": has_markup,
                    "lang":       "en",               # XLIFF files here are all en-us
                }
            )
            id_map[tmp_id] = (source_el, trans_unit)

    return work_items, id_map, total_entries


# ── System & user prompts ─────────────────────────────────────────────────────

def _make_xliff_system_prompt(target_lang: str, domain_context: str = "", glossary: Optional[List[Dict[str, str]]] = None) -> str:
    target_name = TARGET_LANGUAGES.get(target_lang, target_lang)

    # Look up register note using short code (strip _XX suffix if present)
    lang_short = target_lang.split("_")[0] if "_" in target_lang else target_lang
    register_note = _REGISTER_NOTES.get(lang_short, "")

    parts = [
        f"You are a professional technical translator, native in {target_name}, with deep experience "
        f"localising software UI, user manuals, and e-commerce content.",
        "Your translations are used directly in production software without human review, "
        "so precision and consistency are critical.",
        "",
        "=== RULES ===",
        f"1) Translate into {target_name} ONLY.",
        "2) Some items contain plain text — translate the text naturally.",
        (
            "3) Some items contain XLIFF 1.2 inner XML with <g> inline codes representing "
            "HTML formatting (bold, italics, spans, etc.). "
            "You MUST preserve all <g> tags, their id attributes, ctype attributes, "
            "xhtml: namespace attributes, and structure EXACTLY as given. "
            "Only the human-readable text INSIDE the tags should be translated."
        ),
        "4) Preserve placeholders (%s, %d, {name}, HTML entities like &amp;) exactly.",
        "5) Match the source capitalization style (ALL CAPS → ALL CAPS, Title Case → Title Case).",
    ]

    if register_note:
        parts.append(f"5b) Register: {register_note}")

    parts += [
        "6) Keep technical terms and product names (e.g. 'Hydro-Gear ZT-3100', 'AS 990 Tahr RC') as-is.",
        "7) Return ONLY a valid JSON object: {\"translations\": [{\"id\": \"…\", \"translation\": \"…\"}, …]}",
        "8) Do NOT add markdown, code fences, or commentary outside the JSON.",
        "",
        "=== XLIFF INLINE MARKUP RULES ===",
        "Source segments may contain <g> tags representing inline formatting.",
        "You MUST:",
        "- Keep every <g> tag and its id attribute exactly: <g id=\"1\">…</g>",
        "- Only translate the TEXT CONTENT between and around the tags",
        "- Never add, remove, rename, or re-order <g> tags",
        "- Never change id=\"…\" values",
        "",
        "Example:",
        "  Source:  Add <g id=\"1\">all</g> items to cart",
        "  Correct: Legg til <g id=\"1\">alle</g> varer i handlekurven",
        "  Wrong:   Legg til <g id=\"2\">alle</g> varer i handlekurven   ← id changed",
        "  Wrong:   Legg <g id=\"1\">til alle varer</g> i handlekurven  ← tag scope changed",
    ]

    # Glossary section
    if glossary:
        glossary_text = format_glossary_for_prompt(glossary)
        parts += [
            "",
            "=== GLOSSARY (mandatory) ===",
            glossary_text,
        ]

    if domain_context:
        parts += [
            "",
            "=== DOMAIN CONTEXT ===",
            "You are translating product content related to the following domain:",
            domain_context,
        ]

    return "\n".join(parts)


def _make_xliff_user_prompt(items: List[Dict], target_lang: str) -> str:
    """Build the user message for a batch of XLIFF items."""
    target_name = TARGET_LANGUAGES.get(target_lang, target_lang)

    # Build compact representation for the model
    api_items = []
    for item in items:
        api_items.append(
            {
                "id":   item["id"],
                # Send source_xml so the model sees markup (or plain text) correctly
                "source": item["source_xml"],
            }
        )

    prompt_parts = [
        f"Translate the following items into {target_name}.",
        "For items with <g> XML markup, translate only the text — preserve all tags and attributes.",
        "For plain text items, translate directly.",
        "",
        "Items:",
        json.dumps(api_items, ensure_ascii=False),
    ]
    return "\n".join(prompt_parts)


# ── OpenAI call ───────────────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=20))
def _call_model_xliff(
    batch: List[Dict],
    model: str,
    target_lang: str = "nb",
    domain_context: str = "",
    glossary: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, str]:
    """Send a batch of XLIFF items to the model; return {id: translated_content}."""
    system_prompt = _make_xliff_system_prompt(target_lang, domain_context, glossary=glossary)
    user_prompt   = _make_xliff_user_prompt(batch, target_lang)

    messages: Any = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_prompt},
    ]

    if model.startswith("gpt-5"):
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1,
            response_format={"type": "json_object"},
            max_completion_tokens=8192,
        )
    else:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.1,
            response_format={"type": "json_object"},
            max_tokens=8192,
        )

    text = resp.choices[0].message.content or ""

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"(\{.*\})", text, re.DOTALL)
        data = json.loads(m.group(1)) if m else None

    if data is None:
        raise TypeError("Failed to parse JSON from model response")

    # Normalise response envelope
    if isinstance(data, dict):
        if "translations" in data:
            data = data["translations"]
        elif "items" in data:
            data = data["items"]
        else:
            data = next((v for v in data.values() if isinstance(v, list)), [])

    if not isinstance(data, list):
        raise TypeError(f"Expected a list, got {type(data).__name__}")

    return {
        str(item["id"]): item.get("translation")
        for item in data
        if isinstance(item, dict) and "id" in item
    }


# ── Validate placeholder survival ────────────────────────────────────────────

_PH_RE = re.compile(
    r"(%(?:\d+\$)?[-+0 #]*(?:\d+|\*)?(?:\.(?:\d+|\*))?[hlLqjzt]*[diouxXeEfFgGaAcspn%])"
    r"|(%@)"
    r"|(\{\w*\})"
    r"|(https?://\S+)"
    r"|(&[a-zA-Z]+;|&#\d+;)",
    re.IGNORECASE,
)

def _validate_placeholders(source: str, translation: str) -> List[str]:
    src_ph = [m.group() for m in _PH_RE.finditer(source)]
    return [ph for ph in src_ph if ph not in translation]


# ── Main translate function ───────────────────────────────────────────────────

def translate_xliff_file(
    input_path: str,
    output_path: str,
    *,
    model: str = "gpt-4.1",
    batch_size: int = 10,
    target_lang: str = "nb",
    source_lang: str = "auto",
    force: bool = False,
    context_file: Optional[str] = None,
    glossary: Optional[List[Dict[str, str]]] = None,
    progress_callback=None,
    log_callback=None,
) -> Dict:
    """
    Translate an XLIFF 1.2 file and write the result to *output_path*.

    Parameters mirror translate_po_file() for API compatibility.

    Returns a summary dict:
        {"translated", "total_entries", "total_to_translate",
         "placeholder_warnings", "failed", "output_path"}
    """
    def _log(msg: str) -> None:
        if log_callback:
            log_callback(msg)

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Please set OPENAI_API_KEY environment variable")

    domain_context = load_context(context_file)
    if domain_context:
        _log(f"Loaded domain context ({len(domain_context)} chars)")

    _log(f"Model: {model} | Batch: {batch_size} | Target: {target_lang}")

    # ── Parse XLIFF ──────────────────────────────────────────────────────────
    try:
        tree = ET.parse(input_path)
    except ET.ParseError as e:
        raise RuntimeError(f"Failed to parse XLIFF: {e}") from e

    # Set target-language on every <file> element (XLIFF 1.2 §2.3)
    root = tree.getroot()
    for file_el in root.iter(_q("file")):
        file_el.set("target-language", target_lang)

    work_items, id_map, total_entries = build_work_items_xliff(
        tree, source_lang=source_lang, force=force
    )
    total_to_translate = len(work_items)
    _log(f"Trans-units found: {total_entries} | To translate: {total_to_translate}")

    translated_count    = 0
    placeholder_warnings: List[Dict] = []
    failed_items:         List[Dict] = []

    # ── Translate in batches ─────────────────────────────────────────────────
    # XLIFF markup items can have long source XML → use smaller effective batch
    # The caller's batch_size is respected but we cap at 10 for XML items
    for batch in chunked(work_items, batch_size):
        try:
            translations = _call_model_xliff(
                batch, model, target_lang=target_lang, domain_context=domain_context, glossary=glossary
            )

            for item in batch:
                tid   = item["id"]
                trans = translations.get(tid)
                if trans is None:
                    continue

                source_el, trans_unit_el = id_map[tid]

                # Placeholder check (compare against plain text form)
                src_plain = item["text"]
                missing_ph = _validate_placeholders(src_plain, re.sub(r"<[^>]+>", "", trans))
                if missing_ph:
                    placeholder_warnings.append(
                        {
                            "id":          tid,
                            "source":      src_plain[:120],
                            "translation": trans[:120],
                            "missing":     missing_ph,
                        }
                    )

                _set_target_content(trans_unit_el, trans, source_el)
                translated_count += 1

        except Exception as e:
            _log(f"Batch failed ({e}), retrying individually…")
            for item in batch:
                try:
                    single = _call_model_xliff(
                        [item], model, target_lang=target_lang, domain_context=domain_context, glossary=glossary
                    )
                    trans = single.get(item["id"])
                    if trans is None:
                        continue
                    source_el, trans_unit_el = id_map[item["id"]]
                    _set_target_content(trans_unit_el, trans, source_el)
                    translated_count += 1
                except Exception as single_e:
                    failed_items.append(
                        {"id": item["id"], "text": item["text"], "error": str(single_e)}
                    )

        if progress_callback:
            progress_callback(translated_count, total_to_translate)

    # ── Write output ─────────────────────────────────────────────────────────
    # Preserve the original XML declaration and namespace attributes by
    # writing with explicit encoding declaration.
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    tree.write(
        output_path,
        encoding="unicode",
        xml_declaration=False,   # no redundant <?xml?> — the original doesn't have one
        short_empty_elements=True,
    )

    _log(f"Saved: {output_path}")

    return {
        "translated":       translated_count,
        "total_entries":    total_entries,
        "total_to_translate": total_to_translate,
        "placeholder_warnings": placeholder_warnings,
        "failed":           failed_items,
        "output_path":      output_path,
    }


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    defaults = get_defaults()

    parser = argparse.ArgumentParser(description="Translate XLIFF (.xlf) files using OpenAI")
    parser.add_argument("input_xlf",  help="Input .xlf file path")
    parser.add_argument("output_xlf", help="Output .xlf file path")
    parser.add_argument("--model",      default=defaults["model"],
                        help=f"OpenAI model (default: {defaults['model']})")
    parser.add_argument("--batch-size", type=int, default=min(defaults["batch_size"], 10),
                        help="Trans-units per API call (default: 10)")
    parser.add_argument("--target-lang",
                        choices=tuple(TARGET_LANGUAGES.keys()),
                        default=defaults["target_lang"],
                        help=f"Target language (default: {defaults['target_lang']})")
    parser.add_argument("--source-lang",
                        choices=tuple(SOURCE_LANGUAGES),
                        default=defaults["source_lang"])
    parser.add_argument("--context-file", default=defaults["context_file"],
                        help="Domain context file (.json/.txt)")
    parser.add_argument("--force", action="store_true",
                        help="Re-translate entries that already have a <target>")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    def _log(msg: str) -> None:
        if args.verbose:
            print(msg)

    result = translate_xliff_file(
        args.input_xlf,
        args.output_xlf,
        model=args.model,
        batch_size=args.batch_size,
        target_lang=args.target_lang,
        source_lang=args.source_lang,
        force=args.force,
        context_file=args.context_file or None,
        log_callback=_log,
    )

    print(
        f"Done — translated {result['translated']} / {result['total_to_translate']} "
        f"trans-units  ({result['total_entries']} total in file)"
    )
    if result["placeholder_warnings"]:
        print(f"  ⚠  {len(result['placeholder_warnings'])} placeholder warning(s)")
    if result["failed"]:
        print(f"  ✗  {len(result['failed'])} failed item(s)")


if __name__ == "__main__":
    main()

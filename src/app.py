"""
Streamlit frontend for the PO File Translator.

Run with:
    streamlit run src/app.py
"""

import os
import sys
import tempfile
from pathlib import Path

import streamlit as st

# Ensure the src package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.po_translate_en_to_nb import (
    AVAILABLE_MODELS,
    TARGET_LANGUAGES,
    SOURCE_LANGUAGES,
    translate_po_file,
    build_work_items,
    load_context,
    get_defaults,
)
import polib

# ─── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PO File Translator",
    page_icon="🌍",
    layout="wide",
)

# ─── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { max-width: 1200px; margin: 0 auto; }
    div[data-testid="stMetric"] {
        background-color: #f0f2f6;
        border-radius: 8px;
        padding: 12px 16px;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeeba;
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
    }
</style>
""", unsafe_allow_html=True)


def main():
    st.title("🌍 PO File Translator")
    st.caption("Translate .po (Poedit) files using OpenAI — preserving placeholders, HTML tags, and formatting.")

    # Load user defaults from .env
    defaults = get_defaults()

    # ─── Sidebar: Settings ─────────────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Settings")

        # API key
        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            value=os.getenv("OPENAI_API_KEY", ""),
            help="Your OpenAI API key. Also reads from OPENAI_API_KEY env var.",
        )
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key

        st.divider()

        # Model selection — default from .env
        default_model_idx = AVAILABLE_MODELS.index(defaults["model"]) if defaults["model"] in AVAILABLE_MODELS else 0
        model = st.selectbox(
            "Model",
            options=AVAILABLE_MODELS,
            index=default_model_idx,
            help="gpt-4.1 recommended for quality. gpt-5.2 for best quality. gpt-4.1-mini/nano for lower cost.",
        )

        # Target language — default from .env
        target_keys = list(TARGET_LANGUAGES.keys())
        default_target_idx = target_keys.index(defaults["target_lang"]) if defaults["target_lang"] in target_keys else 0
        target_lang = st.selectbox(
            "Target language",
            options=target_keys,
            format_func=lambda k: f"{TARGET_LANGUAGES[k]} ({k})",
            index=default_target_idx,
        )

        # Source language — default from .env
        default_source_idx = SOURCE_LANGUAGES.index(defaults["source_lang"]) if defaults["source_lang"] in SOURCE_LANGUAGES else 0
        source_lang = st.selectbox(
            "Source language detection",
            options=SOURCE_LANGUAGES,
            index=default_source_idx,
            help="'auto' detects English vs German per entry. Use 'en' or 'de' to force.",
        )

        # Batch size — default from .env
        batch_size = st.slider(
            "Batch size",
            min_value=5,
            max_value=50,
            value=min(max(defaults["batch_size"], 5), 50),
            step=5,
            help="Items per API call. Smaller = better quality, larger = faster.",
        )

        # Force translate
        force = st.checkbox(
            "Force translate all entries",
            value=True,
            help="Translate every entry, even if it already has a translation.",
        )

        st.divider()

        # Context file
        st.subheader("📋 Domain context")
        context_mode = st.radio(
            "Context source",
            ["None", "Upload file", "Paste text"],
            horizontal=True,
        )
        context_text = ""
        if context_mode == "Upload file":
            ctx_file = st.file_uploader("Context file", type=["json", "txt", "md"])
            if ctx_file:
                context_text = ctx_file.read().decode("utf-8")
                st.success(f"Loaded {len(context_text)} chars")
        elif context_mode == "Paste text":
            context_text = st.text_area(
                "Domain instructions",
                height=120,
                placeholder="e.g. Translate technical language related to lawn and garden machinery…",
            )

        st.divider()
        st.caption("CLI equivalent shown after translation.")

    # ─── Main area: File upload & action ───────────────────────────────────
    col_upload, col_info = st.columns([2, 1])

    with col_upload:
        uploaded_file = st.file_uploader(
            "Upload a .po file",
            type=["po"],
            help="Upload the .po file you want to translate.",
        )

    # If a file is uploaded, show a preview
    if uploaded_file is not None:
        # Save to temp file so polib can read it
        with tempfile.NamedTemporaryFile(delete=False, suffix=".po", mode="wb") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_input = tmp.name

        try:
            po = polib.pofile(tmp_input, encoding="utf-8")
        except Exception as e:
            st.error(f"Failed to parse PO file: {e}")
            return

        work_items, id_map, total_entries = build_work_items(
            po, source_lang=source_lang, force=force
        )

        # File stats
        with col_info:
            st.metric("Total entries", total_entries)
            st.metric("To translate", len(work_items))
            estimated_calls = (len(work_items) + batch_size - 1) // batch_size
            st.metric("API calls (est.)", estimated_calls)

        # Preview tab
        with st.expander("📄 Preview entries to translate", expanded=False):
            preview_data = []
            for item in work_items[:100]:
                entry_obj, src_field = id_map[item["id"]]
                preview_data.append({
                    "Source lang": item["lang"],
                    "Source field": src_field,
                    "Text": item["text"][:120],
                    "Current msgstr": entry_obj.msgstr[:120] if entry_obj.msgstr else "—",
                })
            st.dataframe(preview_data, use_container_width=True, hide_index=True)
            if len(work_items) > 100:
                st.caption(f"Showing first 100 of {len(work_items)} entries.")

        # ─── Translate button ──────────────────────────────────────────────
        st.divider()

        if not api_key:
            st.warning("⚠️ Enter your OpenAI API key in the sidebar to translate.")
            return

        col_btn, col_cli = st.columns([1, 2])
        with col_btn:
            translate_btn = st.button(
                "🚀 Translate",
                type="primary",
                use_container_width=True,
                disabled=(len(work_items) == 0),
            )

        with col_cli:
            cli_cmd = (
                f'python src/po_translate_en_to_nb.py "{uploaded_file.name}" "output.po"'
                f" --model {model} --batch-size {batch_size}"
                f" --target-lang {target_lang} --source-lang {source_lang}"
            )
            if force:
                cli_cmd += " --force"
            if context_text:
                cli_cmd += ' --context-file "context.json"'
            st.code(cli_cmd, language="powershell")

        if translate_btn:
            _run_translation(
                tmp_input, model, batch_size, target_lang, source_lang,
                force, context_text, uploaded_file.name,
            )

    else:
        st.info("👆 Upload a `.po` file to get started.")

        # Show sample usage
        with st.expander("ℹ️ How it works"):
            st.markdown("""
1. **Upload** your `.po` file (exported from Poedit or your build system).
2. **Configure** model, target language, and batch size in the sidebar.
3. **Optionally** add domain context for better terminology.
4. Click **Translate** and wait for the progress bar to complete.
5. **Download** the translated `.po` file and open it in Poedit for review.

Placeholders (`%s`, `{name}`, HTML tags, URLs) are automatically validated after translation.
            """)


def _run_translation(
    tmp_input, model, batch_size, target_lang, source_lang,
    force, context_text, original_filename,
):
    """Execute the translation and display results."""

    # Write context to a temp file if provided
    context_file = None
    if context_text:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as ctx_tmp:
            ctx_tmp.write(context_text)
            context_file = ctx_tmp.name

    # Create temp output path
    with tempfile.NamedTemporaryFile(delete=False, suffix=".po") as out_tmp:
        tmp_output = out_tmp.name

    # Progress bar and log area
    progress_bar = st.progress(0, text="Starting translation…")
    log_container = st.empty()
    log_messages = []

    def on_progress(translated, total):
        pct = translated / total if total > 0 else 1.0
        progress_bar.progress(pct, text=f"Translated {translated} / {total} entries")

    def on_log(msg):
        log_messages.append(msg)
        log_container.text("\n".join(log_messages[-5:]))

    # Run
    try:
        result = translate_po_file(
            tmp_input,
            tmp_output,
            model=model,
            batch_size=batch_size,
            target_lang=target_lang,
            source_lang=source_lang,
            force=force,
            context_file=context_file,
            progress_callback=on_progress,
            log_callback=on_log,
        )
    except Exception as e:
        st.error(f"❌ Translation failed: {e}")
        return

    progress_bar.progress(1.0, text="✅ Translation complete!")

    # ─── Results ───────────────────────────────────────────────────────────
    st.divider()
    st.subheader("📊 Results")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("✅ Translated", result["translated"])
    col2.metric("📄 Total entries", result["total_entries"])
    col3.metric("⚠️ Placeholder issues", len(result["placeholder_warnings"]))
    col4.metric("❌ Failed", len(result["failed"]))

    # Placeholder warnings
    if result["placeholder_warnings"]:
        with st.expander(f"⚠️ {len(result['placeholder_warnings'])} placeholder warning(s)", expanded=True):
            pw_data = []
            for pw in result["placeholder_warnings"]:
                pw_data.append({
                    "ID": pw["id"],
                    "Missing": ", ".join(pw["missing"]),
                    "Source": pw["source"][:80],
                    "Translation": pw["translation"][:80],
                })
            st.dataframe(pw_data, use_container_width=True, hide_index=True)

    # Failed items
    if result["failed"]:
        with st.expander(f"❌ {len(result['failed'])} failed item(s)"):
            for fi in result["failed"]:
                st.text(f"ID {fi['id']}: {fi['text'][:60]} — {fi['error']}")

    # Translation preview
    with st.expander("📋 Translation preview (first 50)", expanded=False):
        try:
            po_out = polib.pofile(tmp_output, encoding="utf-8")
            preview = []
            count = 0
            for entry in po_out:
                if entry.msgid == "":
                    continue
                preview.append({
                    "msgid": entry.msgid[:80],
                    "msgstr": entry.msgstr[:80] if entry.msgstr else "—",
                })
                count += 1
                if count >= 50:
                    break
            st.dataframe(preview, use_container_width=True, hide_index=True)
        except Exception:
            st.warning("Could not load preview.")

    # Download button
    st.divider()
    try:
        output_bytes = Path(tmp_output).read_bytes()
        stem = Path(original_filename).stem
        download_name = f"translated_{target_lang}_{stem}.po"
        st.download_button(
            label=f"⬇️ Download translated .po",
            data=output_bytes,
            file_name=download_name,
            mime="application/x-gettext",
            type="primary",
            use_container_width=True,
        )
    except Exception as e:
        st.error(f"Could not prepare download: {e}")


if __name__ == "__main__":
    main()

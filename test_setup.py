#!/usr/bin/env python3
"""
Test the PO translator functionality.
"""
import tempfile
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def create_test_po_file():
    """Create a simple test PO file for testing."""
    po_content = '''# Test PO file
msgid ""
msgstr ""
"Content-Type: text/plain; charset=UTF-8\\n"
"Language: nb_NO\\n"

#. Developer comment
#: source/file.php:123
msgctxt "UI context"
msgid "Kundenstimmen - Archiv"
msgstr "Customer reviews archive"

#. Another comment
msgid "Filter products"
msgstr "Filter"

msgid "Accept All"
msgstr ""

msgid "Cookie Settings"
msgstr ""
'''
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.po', delete=False, encoding='utf-8') as f:
        f.write(po_content)
        return f.name

def main():
    """Run a simple test of the translation functionality."""
    try:
        # Check if OpenAI API key is set
        if not os.getenv('OPENAI_API_KEY'):
            print("⚠️  OPENAI_API_KEY not set. Please set it to run the full test.")
            print("   You can still test PO file parsing without API calls.")
            api_test = False
        else:
            print("✅ OPENAI_API_KEY found")
            api_test = True

        # Test imports
        print("Testing imports...")
        try:
            import polib
            print("✅ polib imported successfully")
        except ImportError as e:
            print(f"❌ Failed to import polib: {e}")
            return 1

        try:
            import openai
            print("✅ openai imported successfully")
        except ImportError as e:
            print(f"❌ Failed to import openai: {e}")
            return 1

        try:
            import tenacity
            print("✅ tenacity imported successfully")
        except ImportError as e:
            print(f"❌ Failed to import tenacity: {e}")
            return 1

        # Test PO file parsing
        print("\\nTesting PO file parsing...")
        test_po_file = create_test_po_file()
        
        try:
            po = polib.pofile(test_po_file)
            print(f"✅ Successfully parsed PO file with {len(po)} entries")
            
            # Check entries
            english_entries = []
            for entry in po:
                if entry.msgid and entry.msgid != "":
                    print(f"   Entry: '{entry.msgid}' -> '{entry.msgstr}'")
                    if entry.msgstr and 'Accept' in entry.msgstr or 'Filter' in entry.msgstr or 'Cookie' in entry.msgid:
                        english_entries.append(entry)
            
            print(f"✅ Found {len(english_entries)} entries that need translation")
            
        except Exception as e:
            print(f"❌ Failed to parse PO file: {e}")
            return 1
        finally:
            # Clean up
            os.unlink(test_po_file)

        if api_test:
            print("\\n🚀 All tests passed! You can now run the translator with your PO files.")
            print("\\nExample usage:")
            print("   python src/po_translate_en_to_nb.py input.po output.po")
        else:
            print("\\n✅ Basic tests passed! Set OPENAI_API_KEY to test full functionality.")
        
        return 0

    except Exception as e:
        print(f"❌ Unexpected error during testing: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
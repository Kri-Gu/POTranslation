from src.po_translate_en_to_nb import TARGET_LANGUAGES, _normalise_lang, make_system_prompt


def test_new_target_languages_exist():
    assert "de" in TARGET_LANGUAGES
    assert "fr_CA" in TARGET_LANGUAGES
    assert "en_US" in TARGET_LANGUAGES
    assert "en_GB" in TARGET_LANGUAGES


def test_locale_normalisation_preserves_supported_variants():
    assert _normalise_lang("fr_CA") == "fr_CA"
    assert _normalise_lang("fr-ca") == "fr_CA"
    assert _normalise_lang("en_US") == "en_US"
    assert _normalise_lang("en-us") == "en_US"
    assert _normalise_lang("en_GB") == "en_GB"
    assert _normalise_lang("en-gb") == "en_GB"


def test_aliases_for_new_locales():
    assert _normalise_lang("german") == "de"
    assert _normalise_lang("canadian french") == "fr_CA"
    assert _normalise_lang("uk english") == "en_GB"
    assert _normalise_lang("american english") == "en_US"


def test_system_prompt_uses_locale_name_and_guidance():
    prompt_ca = make_system_prompt("fr_CA")
    prompt_us = make_system_prompt("en_US")
    prompt_uk = make_system_prompt("en_GB")

    assert "French (Canada)" in prompt_ca
    assert "US English" in prompt_us
    assert "UK English" in prompt_uk

import io
from types import SimpleNamespace

from openpyxl import Workbook

from src.app import _dedupe_glossary, _parse_glossary_text, _parse_glossary_upload


def _upload(name: str, data: bytes):
    return SimpleNamespace(name=name, getvalue=lambda: data)


def test_parse_glossary_text_supports_multiple_separators():
    text = """
    lawn mower -> gressklipper
    blade speed = knivhastighet
    throttle → gasspedal
    """
    rows = _parse_glossary_text(text)

    assert len(rows) == 3
    assert rows[0] == {"source": "lawn mower", "target": "gressklipper"}
    assert rows[1] == {"source": "blade speed", "target": "knivhastighet"}
    assert rows[2] == {"source": "throttle", "target": "gasspedal"}


def test_dedupe_glossary_is_case_insensitive_and_drops_invalid_rows():
    rows = [
        {"source": "Throttle", "target": "gasspedal"},
        {"source": "throttle", "target": "gass"},
        {"source": "", "target": "invalid"},
        {"source": "blade", "target": ""},
    ]

    deduped = _dedupe_glossary(rows)

    assert deduped == [{"source": "Throttle", "target": "gasspedal"}]


def test_parse_glossary_upload_csv_with_headers():
    csv_data = b"source,target\nuser manual,brukermanual\ncertificate,sertifikat\n"
    rows = _parse_glossary_upload(_upload("terms.csv", csv_data))

    assert rows == [
        {"source": "user manual", "target": "brukermanual"},
        {"source": "certificate", "target": "sertifikat"},
    ]


def test_parse_glossary_upload_csv_without_headers_uses_first_two_columns():
    csv_data = b"spare part,reservedel\nservice manual,servicehandbok\n"
    rows = _parse_glossary_upload(_upload("terms.csv", csv_data))

    assert rows == [
        {"source": "spare part", "target": "reservedel"},
        {"source": "service manual", "target": "servicehandbok"},
    ]


def test_parse_glossary_upload_xlsx_with_headers():
    wb = Workbook()
    ws = wb.active
    ws.append(["source", "target"])
    ws.append(["safety label", "sikkerhetsmerking"])
    ws.append(["torque", "dreiemoment"])

    bio = io.BytesIO()
    wb.save(bio)

    rows = _parse_glossary_upload(_upload("terms.xlsx", bio.getvalue()))

    assert rows == [
        {"source": "safety label", "target": "sikkerhetsmerking"},
        {"source": "torque", "target": "dreiemoment"},
    ]

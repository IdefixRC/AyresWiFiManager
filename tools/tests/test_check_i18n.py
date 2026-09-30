"""Tests for tools/check_i18n.py."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import check_i18n  # noqa: E402

CORE = "/* i18n-core:begin */\n    var AWMI18n = {};\n    /* i18n-core:end */"
GOOD = {
    "en": {"_name": "English", "page_title": "Setup", "greeting": "Hello {name}"},
    "es": {"_name": "Español", "page_title": "Configuración", "greeting": "Hola {name}"},
}
BODY = '<h1 data-i18n="greeting">Hello</h1>'


def make_page(tmp_path, tables=GOOD, body=BODY, script="", core=CORE, name="page.html"):
    html = (
        '<!doctype html><html lang="en"><head>'
        '<title data-i18n="page_title">Setup</title></head><body>'
        f"{body}"
        f'<script type="application/json" id="i18n">{json.dumps(tables, ensure_ascii=False)}</script>'
        f"<script>\n    {core}\n</script><script>{script}</script></body></html>"
    )
    path = tmp_path / name
    path.write_text(html, encoding="utf-8")
    return path


def test_valid_page_has_no_problems(tmp_path):
    assert check_i18n.check_page(make_page(tmp_path)) == []


def test_missing_table_is_reported(tmp_path):
    path = tmp_path / "page.html"
    path.write_text("<html></html>", encoding="utf-8")
    assert any("no i18n table" in p for p in check_i18n.check_page(path))


def test_invalid_json_is_reported(tmp_path):
    path = tmp_path / "page.html"
    path.write_text('<script type="application/json" id="i18n">{"en": </script>', encoding="utf-8")
    assert any("not valid JSON" in p for p in check_i18n.check_page(path))


def test_missing_english_table_is_reported(tmp_path):
    problems = check_i18n.check_page(make_page(tmp_path, tables={"es": GOOD["es"]}))
    assert any("no 'en' table" in p for p in problems)


def test_missing_key_in_one_language(tmp_path):
    tables = {"en": GOOD["en"], "es": {k: v for k, v in GOOD["es"].items() if k != "greeting"}}
    assert "page.html: 'es' is missing key 'greeting'" in check_i18n.check_page(make_page(tmp_path, tables=tables))


def test_extra_key_in_one_language(tmp_path):
    tables = {"en": GOOD["en"], "es": {**GOOD["es"], "extra": "x"}}
    assert "page.html: 'es' has key 'extra' that 'en' does not" in check_i18n.check_page(make_page(tmp_path, tables=tables))


def test_missing_name(tmp_path):
    tables = {"en": GOOD["en"], "es": {**GOOD["es"], "_name": " "}}
    assert "page.html: 'es' has no _name" in check_i18n.check_page(make_page(tmp_path, tables=tables))


def test_used_but_undefined_key(tmp_path):
    body = BODY + '<p data-i18n-html="missing_key"></p>'
    assert "page.html: key 'missing_key' is used but not defined" in check_i18n.check_page(make_page(tmp_path, body=body))


def test_key_used_from_script_counts(tmp_path):
    tables = {lang: {**table, "done": "ok"} for lang, table in GOOD.items()}
    assert check_i18n.check_page(make_page(tmp_path, tables=tables, script="setStatus('done');")) == []


def test_defined_but_unused_key(tmp_path):
    tables = {lang: {**table, "orphan": "x"} for lang, table in GOOD.items()}
    assert "page.html: key 'orphan' is defined but never used" in check_i18n.check_page(make_page(tmp_path, tables=tables))


def test_placeholder_mismatch(tmp_path):
    tables = {"en": GOOD["en"], "es": {**GOOD["es"], "greeting": "Hola {nombre}"}}
    problems = check_i18n.check_page(make_page(tmp_path, tables=tables))
    assert any("'greeting' placeholders differ in 'es'" in p for p in problems)


def test_confirm_word_must_differ(tmp_path):
    tables = {lang: {**table, "erase_all_confirm_word": "ERASE ALL"} for lang, table in GOOD.items()}
    body = BODY + '<input data-i18n-placeholder="erase_all_confirm_word">'
    problems = check_i18n.check_page(make_page(tmp_path, tables=tables, body=body))
    assert "page.html: 'erase_all_confirm_word' must differ between languages" in problems


def test_identical_core_blocks_pass(tmp_path):
    a = make_page(tmp_path, name="a.html")
    b = make_page(tmp_path, name="b.html")
    assert check_i18n.check_core([a, b]) == []


def test_different_core_blocks_fail(tmp_path):
    a = make_page(tmp_path, name="a.html")
    b = make_page(tmp_path, name="b.html", core=CORE.replace("{}", "{ x: 1 }"))
    assert "b.html: i18n-core block differs from a.html" in check_i18n.check_core([a, b])


def test_missing_core_block_fails(tmp_path):
    a = make_page(tmp_path, name="a.html")
    b = make_page(tmp_path, name="b.html", core="")
    assert "b.html: no i18n-core block" in check_i18n.check_core([a, b])


def test_main_returns_nonzero_on_problems(tmp_path, capsys):
    bad = tmp_path / "bad.html"
    bad.write_text("<html></html>", encoding="utf-8")
    assert check_i18n.main([str(bad)]) == 1
    assert "FAIL" in capsys.readouterr().out


ROOT = Path(__file__).resolve().parents[2]


def test_real_pages_pass():
    pages = [ROOT / "data" / name for name in ("index.html", "success.html", "error.html")]
    problems = [p for page in pages for p in check_i18n.check_page(page)] + check_i18n.check_core(pages)
    assert problems == []

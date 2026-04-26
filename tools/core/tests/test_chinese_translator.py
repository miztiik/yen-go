"""Tests for Chinese Go term translator (tools.core.chinese_translator)."""

import json
import re
from pathlib import Path

import pytest

from tools.core.chinese_translator import (
    ChineseTranslator,
    TranslationError,
    TranslationResult,
    get_chinese_translator,
    translate_chinese_text,
)


class TestChineseTranslator:
    """Core translator functionality."""

    def test_basic_term(self):
        t = ChineseTranslator()
        r = t.translate("手筋")
        assert r.translated == "tesuji"
        assert not r.has_missing_terms

    def test_phrase_translation(self):
        t = ChineseTranslator()
        r = t.translate("黑先 做活")
        assert "Black to play" in r.translated
        assert "make life" in r.translated

    def test_longest_first_greedy(self):
        """死活题 should match before 死 or 活 separately."""
        t = ChineseTranslator()
        r = t.translate("死活题")
        assert r.translated == "life and death problem"

    def test_author_name(self):
        t = ChineseTranslator()
        r = t.translate("赵治勋")
        assert r.translated == "Cho Chikun"

    def test_classical_book(self):
        t = ChineseTranslator()
        r = t.translate("官子谱")
        assert r.translated == "Guanzi Pu"

    def test_empty_input(self):
        t = ChineseTranslator()
        r = t.translate("")
        assert r.translated == ""
        assert not r.has_missing_terms

    def test_english_passthrough(self):
        t = ChineseTranslator()
        r = t.translate("hello world")
        assert r.translated == "hello world"
        assert not r.has_missing_terms

    def test_mixed_text(self):
        t = ChineseTranslator()
        r = t.translate("The 手筋 is important")
        assert "tesuji" in r.translated
        assert "The" in r.translated

    def test_punctuation(self):
        t = ChineseTranslator()
        r = t.translate("（好手）")
        assert "(" in r.translated
        assert ")" in r.translated

    def test_puzzle_categories_complete(self):
        """All 14 puzzle categories from 101weiqi must be translatable."""
        t = ChineseTranslator()
        categories = [
            "死活题", "手筋", "布局", "定式", "官子",
            "对杀", "对杀题", "综合", "中盘", "吃子",
            "骗招", "实战", "棋理", "模仿",
        ]
        for cat in categories:
            r = t.translate(cat)
            assert not r.has_missing_terms, f"Category '{cat}' has missing terms"
            assert r.translated != cat, f"Category '{cat}' was not translated"


class TestAliasResolution:
    """Traditional->simplified alias resolution."""

    def test_traditional_to_simplified(self):
        t = ChineseTranslator()
        r = t.translate("對殺")
        assert r.translated == "capturing race"

    def test_alias_chain(self):
        """Traditional form resolved then translated."""
        t = ChineseTranslator()
        r = t.translate("詰棋")  # traditional for 诘棋
        assert "tsumego" in r.translated

    def test_mixed_traditional_simplified(self):
        t = ChineseTranslator()
        r = t.translate("棋經衆妙")  # traditional
        # Should resolve to 棋经众妙, then translate
        assert not r.has_missing_terms or r.translated != "棋經衆妙"


class TestStrictMode:
    """Strict mode raises on missing terms."""

    def test_strict_raises_on_unknown(self):
        t = ChineseTranslator(strict=True)
        with pytest.raises(TranslationError) as exc_info:
            t.translate("这个词不在字典里")
        assert exc_info.value.term

    def test_lenient_collects_missing(self):
        t = ChineseTranslator(strict=False)
        r = t.translate("罕见围棋术语测试")
        # Some chars may remain untranslated
        assert isinstance(r.missing_terms, list)

    def test_missing_terms_accumulated(self):
        t = ChineseTranslator(strict=False)
        t.translate("罕见词甲")
        t.translate("罕见词乙")
        missing = t.get_all_missing_terms()
        assert len(missing) >= 1

    def test_reset_missing_terms(self):
        t = ChineseTranslator(strict=False)
        t.translate("罕见词甲")
        t.reset_missing_terms()
        assert len(t.get_all_missing_terms()) == 0


class TestTranslationResult:
    """TranslationResult data class."""

    def test_has_missing_terms_false(self):
        r = TranslationResult(original="test", translated="test")
        assert not r.has_missing_terms

    def test_has_missing_terms_true(self):
        r = TranslationResult(original="x", translated="x", missing_terms=["y"])
        assert r.has_missing_terms


class TestModuleFunctions:
    """Module-level convenience functions."""

    def test_get_chinese_translator_singleton(self):
        # Reset global state
        import tools.core.chinese_translator as mod
        mod._translator = None
        t1 = get_chinese_translator()
        t2 = get_chinese_translator()
        assert t1 is t2

    def test_translate_chinese_text(self):
        result = translate_chinese_text("手筋")
        assert result == "tesuji"

    def test_translate_chinese_text_with_context(self):
        result = translate_chinese_text("官子", context="puzzle-123")
        assert result == "endgame"


class TestDictionaryIntegrity:
    """Validate dictionary file structure and content."""

    def test_dictionary_loads(self):
        t = ChineseTranslator()
        assert len(t._dictionary) > 400

    def test_has_aliases(self):
        t = ChineseTranslator()
        assert len(t._aliases) > 50

    def test_no_empty_translations(self):
        with open(Path(__file__).parent.parent.parent.parent / "config" / "cn-en-dictionary.json", encoding="utf-8") as f:
            data = json.load(f)
        for cat_key, cat_val in data.items():
            if cat_key.startswith("_"):
                continue
            for cn, en in cat_val.items():
                assert en.strip(), f"Empty translation for '{cn}' in {cat_key}"

    def test_metadata_present(self):
        with open(Path(__file__).parent.parent.parent.parent / "config" / "cn-en-dictionary.json", encoding="utf-8") as f:
            data = json.load(f)
        assert "_metadata" in data
        assert re.match(r"^\d+\.\d+$", data["_metadata"]["schema_version"])
        assert data["_metadata"]["language"] == "zh"

    def test_all_categories_non_empty(self):
        with open(Path(__file__).parent.parent.parent.parent / "config" / "cn-en-dictionary.json", encoding="utf-8") as f:
            data = json.load(f)
        for key, val in data.items():
            if key.startswith("_"):
                continue
            assert len(val) > 0, f"Empty category: {key}"

    def test_schema_validation(self):
        """Dictionary validates against dictionary.schema.json."""
        try:
            import jsonschema
        except ImportError:
            pytest.skip("jsonschema not installed")

        base = Path(__file__).parent.parent.parent.parent / "config"
        schema = json.loads((base / "schemas" / "dictionary.schema.json").read_text(encoding="utf-8"))
        data = json.loads((base / "cn-en-dictionary.json").read_text(encoding="utf-8"))
        jsonschema.validate(data, schema)

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from agents.researcher import scrape_note_articles, analyze_longevity, save_research


def test_analyze_longevity_returns_scored_articles():
    articles = [
        {"title": "副業で月10万稼ぐ方法", "likes": 50, "url": "/foo", "price": 500},
        {"title": "2026年トレンドまとめ", "likes": 30, "url": "/bar", "price": 500},
    ]
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps([
        {"title": "副業で月10万稼ぐ方法", "longevity_score": 8.5, "reason": "普遍的な副業需要"},
        {"title": "2026年トレンドまとめ", "longevity_score": 2.0, "reason": "時事性が高い"},
    ]))]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    result = analyze_longevity(articles, mock_client)

    assert result[0]["longevity_score"] == 8.5
    assert result[1]["longevity_score"] == 2.0
    assert mock_client.messages.create.call_count == 1


def test_save_research_creates_json(tmp_path):
    articles = [{"title": "test", "likes": 10, "longevity_score": 7.0}]
    output_path = save_research(articles, tmp_path)
    assert output_path.exists()
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved[0]["title"] == "test"


def test_parse_int_handles_plain_number():
    from agents.researcher import _parse_int
    assert _parse_int("120") == 120


def test_parse_int_handles_empty():
    from agents.researcher import _parse_int
    assert _parse_int("") == 0


def test_parse_int_handles_mixed():
    from agents.researcher import _parse_int
    assert _parse_int("1,234件") == 1234


def test_analyze_longevity_fallback_on_title_mismatch():
    articles = [{"title": "マッチしないタイトル", "likes": 10, "url": "/x", "price": 500}]
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps([
        {"title": "全く別のタイトル", "longevity_score": 9.0, "reason": "テスト"}
    ]))]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    result = analyze_longevity(articles, mock_client)
    assert result[0]["longevity_score"] == 5.0
    assert result[0]["longevity_reason"] == "評価不明"


def test_analyze_longevity_handles_invalid_json():
    articles = [{"title": "テスト記事", "likes": 5, "url": "/y", "price": 500}]
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="これはJSONではありません")]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    result = analyze_longevity(articles, mock_client)
    # エラーで落ちず、フォールバック値が設定されること
    assert result[0]["longevity_score"] == 5.0

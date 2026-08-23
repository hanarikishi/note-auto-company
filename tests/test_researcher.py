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

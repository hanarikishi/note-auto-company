import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from agents.planner import load_research_history, generate_proposals, save_proposals


def test_load_research_history(tmp_path):
    (tmp_path / "2026-08-01.json").write_text(
        json.dumps([{"title": "A", "longevity_score": 8.0}]), encoding="utf-8"
    )
    (tmp_path / "2026-08-08.json").write_text(
        json.dumps([{"title": "B", "longevity_score": 7.0}]), encoding="utf-8"
    )
    result = load_research_history(tmp_path)
    assert len(result) == 2


def test_generate_proposals_returns_markdown():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="# 企画提案\n\n1. テーマA\n2. テーマB")]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    result = generate_proposals(
        research_history=[{"title": "A", "longevity_score": 8.0}],
        sales_history=[],
        client=mock_client,
    )
    assert "企画提案" in result


def test_save_proposals_creates_file(tmp_path):
    path = save_proposals("# テスト提案\n\n1. テーマ", tmp_path)
    assert path.exists()
    assert "テスト提案" in path.read_text(encoding="utf-8")

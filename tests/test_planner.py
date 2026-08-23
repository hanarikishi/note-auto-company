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


def test_load_research_history_empty_dir(tmp_path):
    result = load_research_history(tmp_path)
    assert result == []


def test_load_research_history_nonexistent_dir(tmp_path):
    result = load_research_history(tmp_path / "nonexistent")
    assert result == []


def test_load_sales_history_file_not_found(tmp_path):
    from agents.planner import load_sales_history
    result = load_sales_history(tmp_path / "no_such.csv")
    assert result == []


def test_load_sales_history_header_only(tmp_path):
    from agents.planner import load_sales_history
    csv_path = tmp_path / "sales.csv"
    csv_path.write_text("date,title,theme,sales_count,revenue,longevity_score\n", encoding="utf-8")
    result = load_sales_history(csv_path)
    assert result == []


def test_generate_proposals_includes_research_data():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="# 企画提案")]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    generate_proposals(
        research_history=[{"title": "副業テーマ", "longevity_score": 8.0}],
        sales_history=[],
        client=mock_client,
    )
    call_args = mock_client.messages.create.call_args
    prompt = call_args[1]["messages"][0]["content"]
    assert "副業テーマ" in prompt

import pytest
from pathlib import Path
from unittest.mock import MagicMock
from agents.inspector import inspect_article, save_final


def test_inspect_article_returns_revised_text():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="修正後の本文\n\n体温のある文章になりました")]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    result = inspect_article("AIっぽい文章です。〜となっています。", mock_client)
    assert "修正後の本文" in result
    mock_client.messages.create.assert_called_once()


def test_inspect_article_passes_ng_words_in_prompt():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="修正済み")]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    inspect_article("元の文章", mock_client)
    call_args = mock_client.messages.create.call_args
    # systemプロンプトにNG表現が含まれているか確認
    system_prompt = call_args[1]["system"]
    assert "〜となっています" in system_prompt


def test_inspect_article_preserves_paid_boundary():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="---ここから有料---が残っています")]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    result = inspect_article("冒頭\n\n---ここから有料---\n\n有料部分", mock_client)
    call_args = mock_client.messages.create.call_args
    prompt = call_args[1]["messages"][0]["content"]
    assert "---ここから有料---" in prompt


def test_inspect_article_uses_sonnet():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="修正済み")]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    inspect_article("元の文章", mock_client)
    call_args = mock_client.messages.create.call_args
    assert call_args[1]["model"] == "claude-sonnet-4-6"


def test_save_final_creates_file(tmp_path):
    path = save_final("修正済み記事", tmp_path)
    assert path.exists()
    assert path.name.endswith("-final.md")
    assert "修正済み記事" in path.read_text(encoding="utf-8")

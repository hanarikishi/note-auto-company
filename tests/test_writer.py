import pytest
from pathlib import Path
from unittest.mock import MagicMock
from agents.writer import load_top_proposal, write_article, save_draft


SAMPLE_PROPOSALS = """# 企画提案 2026-08-23

## 推奨順位

### 1位: 副業初心者が最初の1万円を稼ぐ完全ロードマップ
- **想定読者**: 副業を始めたいが何から手を付ければいいかわからない会社員
- **無料部分で見せること**: 副業の種類と初月に稼げる現実的な金額
- **有料部分で解決すること**: 具体的な0→1万円のステップと失敗回避ポイント
- **longevityスコア根拠**: 副業ニーズは年々増加、普遍的テーマ

### 2位: ダミーテーマ
"""


def test_load_top_proposal_extracts_first_rank():
    result = load_top_proposal(SAMPLE_PROPOSALS)
    assert "副業初心者が最初の1万円" in result["title"]
    assert result["target_reader"] != ""
    assert result["free_hook"] != ""
    assert result["paid_content"] != ""


def test_load_top_proposal_raises_on_invalid_format():
    with pytest.raises(ValueError):
        load_top_proposal("# 提案なし\n\n内容がない")


def test_write_article_calls_claude():
    proposal = {
        "title": "副業初心者が最初の1万円を稼ぐ完全ロードマップ",
        "free_hook": "副業の種類と初月に稼げる現実的な金額",
        "paid_content": "具体的な0→1万円のステップと失敗回避ポイント",
        "target_reader": "副業を始めたいが何から手を付ければいいかわからない会社員",
    }
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="記事本文テスト" * 100)]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    result = write_article(proposal, mock_client)
    assert len(result) > 100
    mock_client.messages.create.assert_called_once()


def test_write_article_prompt_contains_free_paid_boundary():
    proposal = {
        "title": "テストタイトル",
        "free_hook": "無料フック",
        "paid_content": "有料コンテンツ",
        "target_reader": "テスト読者",
    }
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="本文")]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    write_article(proposal, mock_client)
    call_args = mock_client.messages.create.call_args
    prompt = call_args[1]["messages"][0]["content"]
    assert "---ここから有料---" in prompt


def test_save_draft_creates_file(tmp_path):
    path = save_draft("# テスト記事\n\n本文", tmp_path)
    assert path.exists()
    assert path.name.endswith("-draft.md")

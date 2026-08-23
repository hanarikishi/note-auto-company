import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from agents.marketer import load_final_article, generate_posts, save_posts


def test_load_final_article_returns_title_and_body(tmp_path):
    final_dir = tmp_path / "final"
    final_dir.mkdir()
    (final_dir / "2026-08-23-final.md").write_text(
        "# 副業で月5万円稼ぐ方法\n\n本文の内容です。\n詳細説明。",
        encoding="utf-8",
    )
    title, body = load_final_article(final_dir)
    assert title == "副業で月5万円稼ぐ方法"
    assert "本文の内容です" in body


def test_load_final_article_raises_when_no_files(tmp_path):
    empty_dir = tmp_path / "final"
    empty_dir.mkdir()
    with pytest.raises(FileNotFoundError):
        load_final_article(empty_dir)


def test_load_final_article_picks_latest(tmp_path):
    final_dir = tmp_path / "final"
    final_dir.mkdir()
    (final_dir / "2026-08-20-final.md").write_text("# 古い記事\n\n本文", encoding="utf-8")
    (final_dir / "2026-08-23-final.md").write_text("# 新しい記事\n\n本文", encoding="utf-8")
    title, _ = load_final_article(final_dir)
    assert title == "新しい記事"


def test_generate_posts_calls_api():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="### 投稿1（告知）\nテスト投稿文")]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    result = generate_posts("テストタイトル", "テスト本文", mock_client)

    assert "投稿1" in result
    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["model"] == "claude-haiku-4-5"


def test_save_posts_creates_file(tmp_path):
    posts_dir = tmp_path / "posts"
    path = save_posts("### 投稿1\nテスト", posts_dir)
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "X投稿文" in content
    assert "投稿1" in content

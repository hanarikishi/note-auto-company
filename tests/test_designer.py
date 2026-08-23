import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from agents.designer import create_design, export_design, generate_images


def test_create_design_raises_on_empty_template_id():
    with pytest.raises(ValueError, match="未設定"):
        create_design("token", "", "タイトル", "要約")


def test_create_design_calls_api(tmp_path):
    mock_post = MagicMock()
    mock_post.return_value.json.side_effect = [
        {"design": {"id": "design_123"}},
        {},  # autofill response
    ]
    mock_post.return_value.raise_for_status = MagicMock()

    with patch("agents.designer.requests.post", mock_post):
        design_id = create_design("token", "template_abc", "タイトル", "要約")

    assert design_id == "design_123"
    assert mock_post.call_count == 2


def test_export_design_returns_url():
    responses = [
        MagicMock(**{"json.return_value": {"job": {"id": "job_001"}}, "raise_for_status": MagicMock()}),
        MagicMock(**{"json.return_value": {"job": {"status": "success", "urls": ["https://cdn.canva.com/img.png"]}}, "raise_for_status": MagicMock()}),
    ]

    with patch("agents.designer.requests.post", return_value=responses[0]), \
         patch("agents.designer.requests.get", return_value=responses[1]), \
         patch("agents.designer.time.sleep"):
        url = export_design("token", "design_123")

    assert url == "https://cdn.canva.com/img.png"


def test_generate_images_raises_on_missing_template_ids(tmp_path):
    # config.ymlのtemplate_idが空文字のため ValueError になるはず
    with pytest.raises(ValueError, match="cover_template_id"):
        generate_images(
            title="テスト",
            summary="要約",
            client_id="dummy_id",
            client_secret="dummy_secret",
            covers_dir=tmp_path / "covers",
            social_dir=tmp_path / "social",
        )

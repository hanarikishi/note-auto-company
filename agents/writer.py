import re
from datetime import date
from pathlib import Path

import anthropic
import yaml

CONFIG = yaml.safe_load(Path("config.yml").read_text(encoding="utf-8"))
MIN_CHARS = CONFIG["writing"]["target_chars_min"]
MAX_CHARS = CONFIG["writing"]["target_chars_max"]
FREE_CHARS = CONFIG["writing"]["free_section_chars"]


def load_top_proposal(proposals_text: str) -> dict:
    """proposals.mdから1位のテーマ情報を抽出する。"""
    match = re.search(
        r"### 1位: (.+?)\n"
        r"- \*\*想定読者\*\*: (.+?)\n"
        r"- \*\*無料部分で見せること\*\*: (.+?)\n"
        r"- \*\*有料部分で解決すること\*\*: (.+?)(?:\n|$)",
        proposals_text,
    )
    if not match:
        raise ValueError("proposals.mdから1位のテーマを抽出できませんでした")

    return {
        "title": match.group(1).strip(),
        "target_reader": match.group(2).strip(),
        "free_hook": match.group(3).strip(),
        "paid_content": match.group(4).strip(),
    }


def write_article(proposal: dict, client: anthropic.Anthropic) -> str:
    """Claude APIで4,000〜5,000字の記事を生成する（無料/有料構成込み）。"""
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        thinking={"type": "adaptive"},
        messages=[{
            "role": "user",
            "content": (
                f"あなたはnoteで人気の書き手です。以下の仕様で記事を執筆してください。\n\n"
                f"## タイトル\n{proposal['title']}\n\n"
                f"## 想定読者\n{proposal['target_reader']}\n\n"
                f"## 構成指示\n"
                f"- 全体: {MIN_CHARS}〜{MAX_CHARS}字\n"
                f"- 冒頭約{FREE_CHARS}字（無料公開部分）: {proposal['free_hook']} を扱い、読者を引き込む。具体的なエピソードや数字で始める\n"
                f"- 残り（有料部分）: {proposal['paid_content']} を具体的なステップで解説する\n\n"
                f"## 記事スタイル\n"
                f"- 一人称は「私」または「ぼく」\n"
                f"- 読者に語りかける口調（です・ます調）\n"
                f"- 体験談・失敗談を交える\n"
                f"- 無料/有料の境界には「---ここから有料---」を挿入\n\n"
                f"記事本文のみを出力してください（タイトルは含めない）。"
            ),
        }],
    )
    # thinking ブロックを除いてテキストブロックを返す
    for block in reversed(response.content):
        if hasattr(block, "text"):
            return block.text
    raise RuntimeError("テキストブロックが見つかりませんでした")


def save_draft(content: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{date.today().isoformat()}-draft.md"
    path.write_text(content, encoding="utf-8")
    return path


def main():
    plans_dir = Path("plans")
    if not plans_dir.exists():
        raise FileNotFoundError("plans/ ディレクトリが存在しません")
    proposals_files = sorted(plans_dir.glob("*-proposals.md"))
    if not proposals_files:
        raise FileNotFoundError("plans/ にproposals.mdが見つかりません")

    proposals_text = proposals_files[-1].read_text(encoding="utf-8")
    proposal = load_top_proposal(proposals_text)

    client = anthropic.Anthropic()
    article = write_article(proposal, client)
    path = save_draft(article, Path("articles/drafts"))
    print(f"記事を保存: {path} ({len(article)}字)")


if __name__ == "__main__":
    main()

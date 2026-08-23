from datetime import date
from pathlib import Path

import anthropic
import yaml

CONFIG = yaml.safe_load(Path("config.yml").read_text(encoding="utf-8"))
NG_WORDS = CONFIG["ng_words"]


def inspect_article(draft: str, client: anthropic.Anthropic) -> str:
    """辛口編集者ペルソナでAI臭い表現を体温のある文体に修正する。"""
    ng_words_list = "\n".join(f"- {w}" for w in NG_WORDS)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        thinking={"type": "adaptive"},
        system=(
            "あなたは辛口な編集者です。AIが書いた文章を人間らしい文章に修正するプロです。\n"
            "読者に「これ人間が書いたな」と感じさせる文章に変換してください。\n"
            "記事の構成・内容・事実は変えない。表現・言い回しだけを修正する。\n\n"
            f"## 必ず修正するNG表現\n{ng_words_list}\n\n"
            "## 修正方針\n"
            "- 「〜となっています」→「〜です」「〜なんですよね」\n"
            "- 「〜することができます」→「〜できます」「〜できるんです」\n"
            "- 体言止め・会話的表現・感情表現を積極的に使う\n"
            "- 「---ここから有料---」の区切り線はそのまま残す\n"
        ),
        messages=[{
            "role": "user",
            "content": (
                f"以下の記事を修正してください。\n\n"
                f"## 元の記事\n{draft}\n\n"
                f"修正後の記事本文のみを出力してください（コメント不要）。"
            ),
        }],
    )
    for block in reversed(response.content):
        if hasattr(block, "text"):
            return block.text
    raise RuntimeError("テキストブロックが見つかりませんでした")


def save_final(content: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{date.today().isoformat()}-final.md"
    path.write_text(content, encoding="utf-8")
    return path


def main():
    drafts_dir = Path("articles/drafts")
    if not drafts_dir.exists():
        raise FileNotFoundError("articles/drafts/ ディレクトリが存在しません")
    draft_files = sorted(drafts_dir.glob("*-draft.md"))
    if not draft_files:
        raise FileNotFoundError("articles/drafts/ にdraft.mdが見つかりません")

    draft = draft_files[-1].read_text(encoding="utf-8")
    client = anthropic.Anthropic()
    final = inspect_article(draft, client)
    path = save_final(final, Path("articles/final"))
    print(f"検品完了: {path}")


if __name__ == "__main__":
    main()

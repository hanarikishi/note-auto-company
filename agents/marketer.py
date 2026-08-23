from datetime import date
from pathlib import Path

import anthropic
import yaml

CONFIG = yaml.safe_load(Path("config.yml").read_text(encoding="utf-8"))


def load_final_article(articles_dir: Path) -> tuple[str, str]:
    """最新のfinal.mdを読み込み (title, body) を返す。"""
    files = sorted(articles_dir.glob("*-final.md"))
    if not files:
        raise FileNotFoundError(f"{articles_dir} にfinal.mdが見つかりません")
    content = files[-1].read_text(encoding="utf-8")
    lines = [l for l in content.split("\n") if l.strip()]
    title = lines[0].lstrip("# ").strip() if lines else "タイトル未設定"
    body = "\n".join(lines[1:])
    return title, body


def generate_posts(title: str, body: str, client: anthropic.Anthropic) -> str:
    """X投稿文30本をMarkdown形式で生成して返す。"""
    patterns = CONFIG["x_post"]["patterns"]  # ["告知", "共感", "引用", "ネタバレなし"]
    total = CONFIG["x_post"]["total_posts"]  # 30

    pattern_cycle = [patterns[i % len(patterns)] for i in range(total)]
    pattern_list = "\n".join(
        f"{i+1}. {p}パターン" for i, p in enumerate(pattern_cycle)
    )

    summary = body[:500]

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=4000,
        messages=[
            {
                "role": "user",
                "content": (
                    f"noteで販売中の記事「{title}」のX（Twitter）投稿文を30本作成してください。\n\n"
                    f"## 記事の要約\n{summary}\n\n"
                    f"## 投稿パターン（順番通りに作成）\n{pattern_list}\n\n"
                    "## 制約\n"
                    "- 各投稿は140字以内\n"
                    "- 末尾に「#note #副業」などの関連ハッシュタグを1〜2個\n"
                    "- 販売URLのプレースホルダーは「[note記事URL]」と記載\n"
                    "- 以下のフォーマットで出力:\n\n"
                    "### 投稿1（告知）\n[本文]\n\n### 投稿2（共感）\n[本文]\n\n..."
                ),
            }
        ],
    )
    return response.content[0].text


def save_posts(content: str, output_dir: Path) -> Path:
    """data/posts/YYYY-MM-DD-posts.md に保存してパスを返す。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    path = output_dir / f"{today}-posts.md"
    path.write_text(f"# X投稿文 {today}\n\n{content}", encoding="utf-8")
    return path


def main():
    import os

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    title, body = load_final_article(Path("articles/final"))
    posts = generate_posts(title, body, client)
    out = save_posts(posts, Path("data/posts"))
    print(f"✅ 投稿文保存: {out}")


if __name__ == "__main__":
    main()

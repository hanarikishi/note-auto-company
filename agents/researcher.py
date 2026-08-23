import json
import re
from datetime import date
from pathlib import Path

import anthropic
import requests
import yaml
from bs4 import BeautifulSoup

CONFIG = yaml.safe_load(Path("config.yml").read_text(encoding="utf-8"))


def scrape_note_articles(max_pages: int = 3) -> list[dict]:
    """note.comから500円記事をスクレイピングする。"""
    articles = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; note-research-bot/1.0)"}

    for page in range(1, max_pages + 1):
        url = f"https://note.com/search?q=&context=note&mode=search&price=paid&page={page}"
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # ※ CSSセレクターはnote.comのDOM変更に応じて要調整
        for card in soup.select("article.p-articleCard"):
            price_elem = card.select_one("[class*='price']")
            if not price_elem or "500" not in price_elem.text:
                continue

            title_elem = card.select_one("h3, [class*='title']")
            likes_elem = card.select_one("[class*='like'] span, [class*='count']")
            link_elem = card.select_one("a[href^='/']")

            if not title_elem:
                continue

            articles.append({
                "title": title_elem.text.strip(),
                "likes": _parse_int(likes_elem.text if likes_elem else "0"),
                "url": link_elem["href"] if link_elem else "",
                "price": 500,
            })

    return articles


def analyze_longevity(articles: list[dict], client: anthropic.Anthropic) -> list[dict]:
    """Claude APIで各記事の1年後の需要を0〜10でスコアリングする。"""
    if not articles:
        return []

    articles_text = "\n".join(
        f"- {a['title']} (いいね: {a['likes']})" for a in articles
    )

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": (
                "以下のnote記事タイトルを評価してください。\n"
                "「1年後も売れるか」の観点でlongevity_scoreを0〜10で付けてください。\n"
                "流行・時事ネタは低スコア、普遍的な悩み・スキル・ノウハウは高スコア。\n\n"
                f"記事一覧:\n{articles_text}\n\n"
                "JSON配列のみで回答（説明文不要）:\n"
                '[{"title": "タイトル", "longevity_score": 8.5, "reason": "理由20字以内"}]'
            ),
        }],
    )

    raw = response.content[0].text
    # マークダウンフェンスを除去して JSON 部分を抽出
    match = re.search(r'\[.*\]', raw, re.DOTALL)
    try:
        scores = json.loads(match.group() if match else raw)
    except json.JSONDecodeError:
        scores = []
    score_map = {s["title"]: s for s in scores}

    for article in articles:
        match = score_map.get(article["title"], {})
        article["longevity_score"] = match.get("longevity_score", 5.0)
        article["longevity_reason"] = match.get("reason", "評価不明")

    return articles


def save_research(articles: list[dict], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{date.today().isoformat()}.json"
    output_path.write_text(
        json.dumps(articles, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return output_path


def _parse_int(text: str) -> int:
    cleaned = "".join(c for c in text if c.isdigit())
    return int(cleaned) if cleaned else 0


def main():
    client = anthropic.Anthropic()
    articles = scrape_note_articles(max_pages=CONFIG["research"]["max_pages"])
    articles = analyze_longevity(articles, client)
    articles.sort(key=lambda a: a.get("longevity_score", 0), reverse=True)
    path = save_research(articles, Path("data/research"))
    print(f"✅ {len(articles)}件を保存: {path}")


if __name__ == "__main__":
    main()

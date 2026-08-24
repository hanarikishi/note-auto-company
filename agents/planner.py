import csv
import json
from datetime import date
from pathlib import Path

import anthropic
import yaml

CONFIG = yaml.safe_load(Path("config.yml").read_text(encoding="utf-8"))


def load_research_history(research_dir: Path) -> list[dict]:
    """過去の全リサーチJSONを読み込む。"""
    if not research_dir.exists():
        return []
    articles = []
    for json_file in sorted(research_dir.glob("*.json")):
        data = json.loads(json_file.read_text(encoding="utf-8"))
        articles.extend(data)
    return articles


def load_sales_history(csv_path: Path) -> list[dict]:
    if not csv_path.exists():
        return []
    with csv_path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def generate_proposals(
    research_history: list[dict],
    sales_history: list[dict],
    client: anthropic.Anthropic,
) -> str:
    """Claude APIで次に書くべきテーマ10本をMarkdown形式で提案する。"""
    research_summary = "\n".join(
        f"- {a['title']} (longevity: {a.get('longevity_score', '?')})"
        for a in research_history[-50:]
    )
    sales_summary = (
        "\n".join(f"- {s['title']}: {s['sales_count']}部" for s in sales_history)
        if sales_history
        else "（販売実績なし）"
    )

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=3000,
        messages=[{
            "role": "user",
            "content": (
                "あなたはnoteコンテンツ企画のプロです。\n"
                "以下のリサーチデータと販売実績を参考に、次に書くべき500円noteのテーマを10本提案してください。\n"
                "リサーチデータが空の場合は、副業・転職・節約・生産性・人間関係など普遍的なテーマから提案してください。\n"
                "必ず10本、指定フォーマット通りに出力してください。\n\n"
                f"## 著者情報\n"
                f"- ジャンル: {CONFIG['author']['genre'] or '未設定（普遍的テーマで提案）'}\n"
                f"- ターゲット読者: {CONFIG['author']['target_reader'] or '未設定'}\n"
                f"- 文体: {CONFIG['author']['tone']}\n"
                f"- 強み: {CONFIG['author']['strengths'] or '未設定'}\n\n"
                f"## リサーチデータ（直近50件）\n{research_summary if research_summary else '（データなし：一般的なテーマで提案）'}\n\n"
                f"## 販売実績\n{sales_summary}\n\n"
                "## 出力形式（このフォーマットを厳守）\n"
                f"# 企画提案 {date.today().isoformat()}\n\n"
                "## 推奨順位\n\n"
                "### 1位: [タイトル案]\n"
                "- **想定読者**: [具体的な読者像]\n"
                "- **無料部分で見せること**: [無料公開する内容]\n"
                "- **有料部分で解決すること**: [有料で解決する悩み]\n"
                "- **longevityスコア根拠**: [なぜ1年後も売れるか]\n\n"
                "### 2位: [タイトル案]\n"
                "- **想定読者**: \n"
                "- **無料部分で見せること**: \n"
                "- **有料部分で解決すること**: \n"
                "- **longevityスコア根拠**: \n\n"
                "（3位〜10位も同じ形式で必ず出力）"
            ),
        }],
    )
    return response.content[0].text


def save_proposals(content: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{date.today().isoformat()}-proposals.md"
    path.write_text(content, encoding="utf-8")
    return path


def main():
    client = anthropic.Anthropic()
    research_history = load_research_history(Path("data/research"))
    sales_history = load_sales_history(Path("data/sales_history.csv"))
    proposals = generate_proposals(research_history, sales_history, client)
    path = save_proposals(proposals, Path("plans"))
    print(f"✅ 企画提案を保存: {path}")


if __name__ == "__main__":
    main()

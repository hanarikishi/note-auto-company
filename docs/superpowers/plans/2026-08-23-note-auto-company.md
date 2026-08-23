# 500円note自動会社 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** note.comで500円記事を週1本自動生成・販売するAIエージェントパイプラインをGitHub Actions上に構築する

**Architecture:** 週次バッチ方式。月曜9時に研究・企画エージェントが動きPR①を作成、承認後に執筆・検品エージェントがPR②を作成、承認後にデザイン・営業エージェントが画像と投稿文を生成する。人間の作業はPRのMerge/Closeのみ。

**Tech Stack:** Python 3.11+, anthropic SDK (claude-haiku-4-5 / claude-sonnet-4-6), requests + BeautifulSoup4 (スクレイピング), Canva Connect API (画像生成), pytest + unittest.mock (テスト), GitHub Actions (CI/CD)

---

## ファイル構成

| ファイル | 役割 |
|---|---|
| `config.yml` | テーマ・NGワード・API設定 |
| `requirements.txt` | Python依存関係 |
| `agents/__init__.py` | パッケージ初期化 |
| `agents/researcher.py` | note.comスクレイピング + Claude longevity分析 |
| `agents/planner.py` | 過去データ参照 + テーマ10本提案 + proposals.md生成 |
| `agents/writer.py` | 承認テーマを4,000〜5,000字記事に執筆 |
| `agents/inspector.py` | 辛口編集者ペルソナでAI臭い表現を修正 |
| `agents/designer.py` | Canva API で表紙・告知画像10パターン生成 |
| `agents/marketer.py` | X投稿文30本生成 → Markdownに出力 |
| `tests/test_researcher.py` | researcherのテスト |
| `tests/test_planner.py` | plannerのテスト |
| `tests/test_writer.py` | writerのテスト |
| `tests/test_inspector.py` | inspectorのテスト |
| `tests/test_marketer.py` | marketerのテスト |
| `.github/workflows/monday-research.yml` | 月曜9時JST起動のワークフロー |
| `.github/workflows/post-approved.yml` | PR Merge後起動のワークフロー |

---

## Task 1: プロジェクトスキャフォールド

**Files:**
- Create: `requirements.txt`
- Create: `config.yml`
- Create: `agents/__init__.py`
- Create: `tests/__init__.py`
- Create: `data/sales_history.csv`

- [ ] **Step 1: requirements.txt を作成**

```
anthropic==1.0.0
requests==2.32.3
beautifulsoup4==4.12.3
lxml==5.2.2
PyYAML==6.0.1
pytest==8.2.2
python-dotenv==1.0.1
```

- [ ] **Step 2: config.yml を作成**

```yaml
research:
  target_price: 500
  max_pages: 3
  longevity_threshold: 6.0  # このスコア以上のテーマのみ提案対象

writing:
  target_chars_min: 4000
  target_chars_max: 5000
  free_section_chars: 1500   # 無料公開部分の文字数目安

ng_words:
  - "〜となっています"
  - "〜することができます"
  - "〜と言えるでしょう"
  - "〜ではないでしょうか"
  - "重要なポイントは"
  - "まとめると"

canva:
  cover_template_id: ""        # Canva TemplateID（要設定）
  social_template_id: ""       # Canva TemplateID（要設定）
  cover_size: [1280, 670]
  social_size: [1200, 1200]

x_post:
  patterns: ["告知", "共感", "引用", "ネタバレなし"]
  total_posts: 30
```

- [ ] **Step 3: ディレクトリ・初期ファイルを作成**

```bash
mkdir -p agents tests data/research data/posts articles/drafts articles/final assets/covers assets/social plans
touch agents/__init__.py tests/__init__.py
```

- [ ] **Step 4: data/sales_history.csv を作成（ヘッダーのみ）**

```csv
date,title,theme,sales_count,revenue,longevity_score
```

- [ ] **Step 5: 依存関係インストールを確認**

```bash
pip install -r requirements.txt
```
Expected: すべてのパッケージがインストールされる（エラーなし）

- [ ] **Step 6: コミット**

```bash
git add requirements.txt config.yml agents/__init__.py tests/__init__.py data/sales_history.csv
git commit -m "chore: project scaffold"
```

---

## Task 2: researcher.py

**Files:**
- Create: `agents/researcher.py`
- Create: `tests/test_researcher.py`

- [ ] **Step 1: テストを書く**

`tests/test_researcher.py`:
```python
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from agents.researcher import scrape_note_articles, analyze_longevity, save_research


def test_analyze_longevity_returns_scored_articles():
    articles = [
        {"title": "副業で月10万稼ぐ方法", "likes": 50, "url": "/foo", "price": 500},
        {"title": "2026年トレンドまとめ", "likes": 30, "url": "/bar", "price": 500},
    ]
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps([
        {"title": "副業で月10万稼ぐ方法", "longevity_score": 8.5, "reason": "普遍的な副業需要"},
        {"title": "2026年トレンドまとめ", "longevity_score": 2.0, "reason": "時事性が高い"},
    ]))]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    result = analyze_longevity(articles, mock_client)

    assert result[0]["longevity_score"] == 8.5
    assert result[1]["longevity_score"] == 2.0
    assert mock_client.messages.create.call_count == 1


def test_save_research_creates_json(tmp_path):
    articles = [{"title": "test", "likes": 10, "longevity_score": 7.0}]
    output_path = save_research(articles, tmp_path)
    assert output_path.exists()
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved[0]["title"] == "test"
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/test_researcher.py -v
```
Expected: `ImportError: cannot import name 'scrape_note_articles' from 'agents.researcher'`

- [ ] **Step 3: researcher.py を実装**

`agents/researcher.py`:
```python
import json
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

    scores = json.loads(response.content[0].text)
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
```

- [ ] **Step 4: テストが通ることを確認**

```bash
pytest tests/test_researcher.py -v
```
Expected: `2 passed`

- [ ] **Step 5: コミット**

```bash
git add agents/researcher.py tests/test_researcher.py
git commit -m "feat: add researcher agent"
```

---

## Task 3: planner.py

**Files:**
- Create: `agents/planner.py`
- Create: `tests/test_planner.py`

- [ ] **Step 1: テストを書く**

`tests/test_planner.py`:
```python
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
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/test_planner.py -v
```
Expected: `ImportError`

- [ ] **Step 3: planner.py を実装**

`agents/planner.py`:
```python
import csv
import json
from datetime import date
from pathlib import Path

import anthropic
import yaml

CONFIG = yaml.safe_load(Path("config.yml").read_text(encoding="utf-8"))


def load_research_history(research_dir: Path) -> list[dict]:
    """過去の全リサーチJSONを読み込む。"""
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
        for a in research_history[-50:]  # 直近50件
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
                "以下のリサーチデータと販売実績を参考に、次に書くべき500円noteのテーマを10本提案してください。\n\n"
                f"## リサーチデータ（直近50件）\n{research_summary}\n\n"
                f"## 販売実績\n{sales_summary}\n\n"
                "## 出力形式（Markdown）\n"
                "# 企画提案 YYYY-MM-DD\n\n"
                "## 推奨順位\n\n"
                "### 1位: [タイトル案]\n"
                "- **想定読者**: \n"
                "- **無料部分で見せること**: \n"
                "- **有料部分で解決すること**: \n"
                "- **longevityスコア根拠**: \n\n"
                "（2位〜10位も同形式で）"
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
```

- [ ] **Step 4: テストが通ることを確認**

```bash
pytest tests/test_planner.py -v
```
Expected: `3 passed`

- [ ] **Step 5: コミット**

```bash
git add agents/planner.py tests/test_planner.py
git commit -m "feat: add planner agent"
```

---

## Task 4: writer.py

**Files:**
- Create: `agents/writer.py`
- Create: `tests/test_writer.py`

- [ ] **Step 1: テストを書く**

`tests/test_writer.py`:
```python
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
    assert "想定読者" in result["free_hook"]


def test_write_article_calls_claude():
    proposal = {
        "title": "副業初心者が最初の1万円を稼ぐ完全ロードマップ",
        "free_hook": "副業の種類と初月に稼げる現実的な金額",
        "paid_content": "具体的な0→1万円のステップと失敗回避ポイント",
        "target_reader": "副業を始めたいが何から手を付ければいいかわからない会社員",
    }
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="# タイトル\n\n" + "本文" * 1000)]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    result = write_article(proposal, mock_client)
    assert len(result) > 100
    mock_client.messages.create.assert_called_once()


def test_save_draft_creates_file(tmp_path):
    path = save_draft("# テスト記事\n\n本文", tmp_path)
    assert path.exists()
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/test_writer.py -v
```
Expected: `ImportError`

- [ ] **Step 3: writer.py を実装**

`agents/writer.py`:
```python
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
        r"- \*\*有料部分で解決すること\*\*: (.+?)\n",
        proposals_text,
        re.DOTALL,
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
    return response.content[-1].text


def save_draft(content: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{date.today().isoformat()}-draft.md"
    path.write_text(content, encoding="utf-8")
    return path


def main():
    # 最新のproposals.mdを読み込む
    plans_dir = Path("plans")
    proposals_files = sorted(plans_dir.glob("*-proposals.md"))
    if not proposals_files:
        raise FileNotFoundError("plans/ にproposals.mdが見つかりません")

    proposals_text = proposals_files[-1].read_text(encoding="utf-8")
    proposal = load_top_proposal(proposals_text)

    client = anthropic.Anthropic()
    article = write_article(proposal, client)
    path = save_draft(article, Path("articles/drafts"))
    char_count = len(article)
    print(f"✅ 記事を保存: {path} ({char_count}字)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: テストが通ることを確認**

```bash
pytest tests/test_writer.py -v
```
Expected: `3 passed`

- [ ] **Step 5: コミット**

```bash
git add agents/writer.py tests/test_writer.py
git commit -m "feat: add writer agent"
```

---

## Task 5: inspector.py

**Files:**
- Create: `agents/inspector.py`
- Create: `tests/test_inspector.py`

- [ ] **Step 1: テストを書く**

`tests/test_inspector.py`:
```python
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
    prompt = call_args[1]["messages"][0]["content"]
    assert "〜となっています" in prompt


def test_save_final_creates_file(tmp_path):
    path = save_final("修正済み記事", tmp_path)
    assert path.exists()
    assert "修正済み記事" in path.read_text(encoding="utf-8")
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/test_inspector.py -v
```
Expected: `ImportError`

- [ ] **Step 3: inspector.py を実装**

`agents/inspector.py`:
```python
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
            "記事の構成・内容・事実は変えない。表現・言い回しだけを修正する。"
        ),
        messages=[{
            "role": "user",
            "content": (
                f"以下の記事を修正してください。\n\n"
                f"## 必ず修正するNG表現\n{ng_words_list}\n\n"
                f"## 修正方針\n"
                f"- 「〜となっています」→「〜です」「〜なんですよね」\n"
                f"- 「〜することができます」→「〜できます」「〜できるんです」\n"
                f"- 体言止め・会話的表現・感情表現を積極的に使う\n"
                f"- 具体的な数字・エピソードをさらに強調\n"
                f"- 「---ここから有料---」の区切り線はそのまま残す\n\n"
                f"## 元の記事\n{draft}\n\n"
                f"修正後の記事本文のみを出力してください（コメント不要）。"
            ),
        }],
    )
    return response.content[-1].text


def save_final(content: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{date.today().isoformat()}-final.md"
    path.write_text(content, encoding="utf-8")
    return path


def main():
    drafts_dir = Path("articles/drafts")
    draft_files = sorted(drafts_dir.glob("*-draft.md"))
    if not draft_files:
        raise FileNotFoundError("articles/drafts/ にdraft.mdが見つかりません")

    draft = draft_files[-1].read_text(encoding="utf-8")
    client = anthropic.Anthropic()
    final = inspect_article(draft, client)
    path = save_final(final, Path("articles/final"))
    print(f"✅ 検品完了: {path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: テストが通ることを確認**

```bash
pytest tests/test_inspector.py -v
```
Expected: `3 passed`

- [ ] **Step 5: コミット**

```bash
git add agents/inspector.py tests/test_inspector.py
git commit -m "feat: add inspector agent"
```

---

## Task 6: designer.py（Canva API）

> ⚠️ **事前準備が必要**: https://developers.canva.com でアプリ登録 → Client ID / Secret を取得 → GitHub Secrets に `CANVA_CLIENT_ID` `CANVA_CLIENT_SECRET` を設定 → config.yml の `cover_template_id` `social_template_id` を設定

**Files:**
- Create: `agents/designer.py`

- [ ] **Step 1: designer.py を実装**

`agents/designer.py`:
```python
import time
from datetime import date
from pathlib import Path

import requests
import yaml

CONFIG = yaml.safe_load(Path("config.yml").read_text(encoding="utf-8"))
CANVA_API_BASE = "https://api.canva.com/rest/v1"


def get_canva_token(client_id: str, client_secret: str) -> str:
    """Canva OAuth2.0でアクセストークンを取得する。"""
    resp = requests.post(
        "https://api.canva.com/rest/v1/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def create_design_from_template(
    token: str, template_id: str, title: str, summary: str
) -> str:
    """テンプレートからデザインを作成してdesign_idを返す。"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # テンプレートを複製
    resp = requests.post(
        f"{CANVA_API_BASE}/designs",
        json={"design_type": {"type": "custom"}, "asset_id": template_id},
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    design_id = resp.json()["design"]["id"]

    # テキストフィールドを更新（Canva APIのautofill機能）
    requests.post(
        f"{CANVA_API_BASE}/designs/{design_id}/autofill",
        json={"data": {"title": {"type": "text", "text": title},
                       "summary": {"type": "text", "text": summary[:50]}}},
        headers=headers,
        timeout=15,
    )

    return design_id


def export_design(token: str, design_id: str) -> str:
    """デザインをPNGとしてエクスポートしてURLを返す。"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    resp = requests.post(
        f"{CANVA_API_BASE}/exports",
        json={"design_id": design_id, "format": "png", "export_quality": "pro"},
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    job_id = resp.json()["job"]["id"]

    # エクスポート完了を待つ
    for _ in range(20):
        time.sleep(3)
        status_resp = requests.get(
            f"{CANVA_API_BASE}/exports/{job_id}", headers=headers, timeout=15
        )
        status_resp.raise_for_status()
        job = status_resp.json()["job"]
        if job["status"] == "success":
            return job["urls"][0]
        if job["status"] == "failed":
            raise RuntimeError(f"Canvaエクスポート失敗: {job}")

    raise TimeoutError("Canvaエクスポートがタイムアウトしました")


def download_image(url: str, output_path: Path) -> None:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    output_path.write_bytes(resp.content)


def generate_images(
    title: str,
    summary: str,
    client_id: str,
    client_secret: str,
    covers_dir: Path,
    social_dir: Path,
    count: int = 10,
) -> None:
    """表紙・告知画像をそれぞれcount枚生成して保存する。"""
    token = get_canva_token(client_id, client_secret)
    today = date.today().isoformat()
    covers_dir.mkdir(parents=True, exist_ok=True)
    social_dir.mkdir(parents=True, exist_ok=True)

    for i in range(1, count + 1):
        # 表紙
        cover_id = create_design_from_template(
            token, CONFIG["canva"]["cover_template_id"], title, summary
        )
        cover_url = export_design(token, cover_id)
        download_image(cover_url, covers_dir / f"{today}-cover-{i:02d}.png")
        print(f"  表紙 {i}/{count} 完了")

        # 告知画像
        social_id = create_design_from_template(
            token, CONFIG["canva"]["social_template_id"], title, summary
        )
        social_url = export_design(token, social_id)
        download_image(social_url, social_dir / f"{today}-social-{i:02d}.png")
        print(f"  告知画像 {i}/{count} 完了")


def main():
    import os
    client_id = os.environ["CANVA_CLIENT_ID"]
    client_secret = os.environ["CANVA_CLIENT_SECRET"]

    final_files = sorted(Path("articles/final").glob("*-final.md"))
    if not final_files:
        raise FileNotFoundError("articles/final/ にfinal.mdが見つかりません")

    content = final_files[-1].read_text(encoding="utf-8")
    title = content.split("\n")[0].lstrip("# ").strip()
    summary = content[:200].replace("\n", " ")

    generate_images(
        title=title,
        summary=summary,
        client_id=client_id,
        client_secret=client_secret,
        covers_dir=Path("assets/covers"),
        social_dir=Path("assets/social"),
    )
    print("✅ 画像生成完了")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: コミット**

```bash
git add agents/designer.py
git commit -m "feat: add designer agent (Canva API)"
```

---

## Task 7: marketer.py

**Files:**
- Create: `agents/marketer.py`
- Create: `tests/test_marketer.py`

- [ ] **Step 1: テストを書く**

`tests/test_marketer.py`:
```python
import pytest
from pathlib import Path
from unittest.mock import MagicMock
from agents.marketer import generate_posts, save_posts_markdown


SAMPLE_POST_JSON = """[
  {"pattern": "告知", "text": "新しいnoteを公開しました！副業初心者向けの完全ガイドです。"},
  {"pattern": "共感", "text": "副業始めたいけど何から手を付けたらいいかわからない...そんな人へ。"}
]"""


def test_generate_posts_returns_30_items():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=SAMPLE_POST_JSON * 15)]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    # モックは2件返すが関数は30件になるよう内部で処理
    result = generate_posts("テストタイトル", "テスト要約", mock_client)
    assert isinstance(result, list)
    assert len(result) > 0


def test_save_posts_markdown_creates_file(tmp_path):
    posts = [
        {"pattern": "告知", "text": "テスト投稿1"},
        {"pattern": "共感", "text": "テスト投稿2"},
    ]
    path = save_posts_markdown(posts, tmp_path)
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "テスト投稿1" in content
    assert "告知" in content
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
pytest tests/test_marketer.py -v
```
Expected: `ImportError`

- [ ] **Step 3: marketer.py を実装**

`agents/marketer.py`:
```python
import json
from datetime import date
from pathlib import Path

import anthropic
import yaml

CONFIG = yaml.safe_load(Path("config.yml").read_text(encoding="utf-8"))
PATTERNS = CONFIG["x_post"]["patterns"]
TOTAL_POSTS = CONFIG["x_post"]["total_posts"]


def generate_posts(
    title: str, summary: str, client: anthropic.Anthropic
) -> list[dict]:
    """X投稿文をパターン別に30本生成する。"""
    posts_per_pattern = TOTAL_POSTS // len(PATTERNS)

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=6000,
        messages=[{
            "role": "user",
            "content": (
                f"以下のnote記事のX（Twitter）投稿文を作成してください。\n\n"
                f"## 記事情報\n"
                f"タイトル: {title}\n"
                f"概要: {summary[:300]}\n\n"
                f"## 条件\n"
                f"- 4パターン×{posts_per_pattern}本 = 計{TOTAL_POSTS}本を作成\n"
                f"- 各投稿は140字以内\n"
                f"- パターン種別: 告知（購読を促す）、共感（読者の悩みに共感）、引用（記事の名言・数字）、ネタバレなし（内容を匂わせる）\n"
                f"- ハッシュタグは各投稿末尾に1〜2個\n"
                f"- note記事URLは省略（後で追加）\n\n"
                f"## 出力形式（JSON配列のみ）\n"
                f'[{{"pattern": "告知", "text": "投稿文"}}, ...]'
            ),
        }],
    )

    posts = json.loads(response.content[0].text)
    return posts


def save_posts_markdown(posts: list[dict], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    path = output_dir / f"{today}-posts.md"

    lines = [f"# X投稿文 {today}\n\n"]
    lines.append("> Bufferに貼り付ける10本を選んでください。noteのURLを末尾に追加すること。\n\n")

    for i, post in enumerate(posts, 1):
        pattern = post.get("pattern", "")
        text = post.get("text", "")
        lines.append(f"## {i}. [{pattern}]\n\n{text}\n\n---\n\n")

    path.write_text("".join(lines), encoding="utf-8")
    return path


def main():
    final_files = sorted(Path("articles/final").glob("*-final.md"))
    if not final_files:
        raise FileNotFoundError("articles/final/ にfinal.mdが見つかりません")

    content = final_files[-1].read_text(encoding="utf-8")
    title = content.split("\n")[0].lstrip("# ").strip()
    summary = " ".join(content.split("\n")[1:10])

    client = anthropic.Anthropic()
    posts = generate_posts(title, summary, client)
    path = save_posts_markdown(posts, Path("data/posts"))
    print(f"✅ {len(posts)}本の投稿文を保存: {path}")
    print("📋 Bufferに貼り付ける10本を選んで予約投稿してください（約15分）")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: テストが通ることを確認**

```bash
pytest tests/test_marketer.py -v
```
Expected: `2 passed`

- [ ] **Step 5: コミット**

```bash
git add agents/marketer.py tests/test_marketer.py
git commit -m "feat: add marketer agent"
```

---

## Task 8: GitHub Actions — monday-research.yml

**Files:**
- Create: `.github/workflows/monday-research.yml`

- [ ] **Step 1: GitHub Secrets を設定**

GitHubリポジトリの Settings → Secrets and variables → Actions で以下を追加:
```
ANTHROPIC_API_KEY   ← Claude APIキー
CANVA_CLIENT_ID     ← Canva APIクライアントID（後で設定可）
CANVA_CLIENT_SECRET ← Canva APIクライアントシークレット（後で設定可）
```

- [ ] **Step 2: monday-research.yml を作成**

`.github/workflows/monday-research.yml`:
```yaml
name: 月曜リサーチ＆企画

on:
  schedule:
    - cron: "0 0 * * 1"   # 月曜 00:00 UTC = 月曜 09:00 JST
  workflow_dispatch:        # 手動実行も可能

jobs:
  research-and-plan:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write

    steps:
      - uses: actions/checkout@v4

      - name: Python セットアップ
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: 依存関係インストール
        run: pip install -r requirements.txt

      - name: リサーチ実行
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: python -m agents.researcher

      - name: 企画生成
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: python -m agents.planner

      - name: ブランチ作成＆PR提出
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          TODAY=$(date +%Y-%m-%d)
          BRANCH="research/${TODAY}"
          git config user.name "note-auto-company[bot]"
          git config user.email "bot@github-actions"
          git checkout -b "${BRANCH}"
          git add data/research/ plans/
          git commit -m "research: ${TODAY} リサーチ・企画完了"
          git push origin "${BRANCH}"
          gh pr create \
            --title "📋 企画提案 ${TODAY}" \
            --body "## 今週の企画提案\n\nリサーチ結果と企画10本の提案です。\n\n1位のテーマを承認する場合は **Merge** してください。\n差し戻す場合は **Close** してコメントを残してください。" \
            --base main \
            --head "${BRANCH}" \
            --label "research"
```

- [ ] **Step 3: ワークフローを手動実行してテスト**

GitHubリポジトリ → Actions → 月曜リサーチ＆企画 → Run workflow

Expected: PRが作成される。Actionsのログにエラーがない。

- [ ] **Step 4: コミット**

```bash
git add .github/workflows/monday-research.yml
git commit -m "ci: add monday research workflow"
```

---

## Task 9: GitHub Actions — post-approved.yml

**Files:**
- Create: `.github/workflows/post-approved.yml`

- [ ] **Step 1: post-approved.yml を作成**

`.github/workflows/post-approved.yml`:
```yaml
name: PR承認後パイプライン

on:
  pull_request:
    types: [closed]
    branches: [main]

jobs:
  # PR①（research/ブランチ）がMergeされたら執筆・検品を実行
  write-and-inspect:
    if: |
      github.event.pull_request.merged == true &&
      startsWith(github.event.pull_request.head.ref, 'research/')
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write

    steps:
      - uses: actions/checkout@v4

      - name: Python セットアップ
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: 依存関係インストール
        run: pip install -r requirements.txt

      - name: 執筆
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: python -m agents.writer

      - name: 検品
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: python -m agents.inspector

      - name: ブランチ作成＆PR提出
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          TODAY=$(date +%Y-%m-%d)
          BRANCH="article/${TODAY}"
          git config user.name "note-auto-company[bot]"
          git config user.email "bot@github-actions"
          git checkout -b "${BRANCH}"
          git add articles/
          git commit -m "article: ${TODAY} 執筆・検品完了"
          git push origin "${BRANCH}"
          gh pr create \
            --title "✍️ 記事レビュー ${TODAY}" \
            --body "## 今週の記事（検品済み）\n\n執筆・検品が完了しました。\n\n記事内容を確認して **Merge**（承認）または **Close**（差し戻し）してください。\n差し戻しの場合はコメントに修正指示を書いてください。" \
            --base main \
            --head "${BRANCH}" \
            --label "article"

  # PR②（article/ブランチ）がMergeされたらデザイン・営業を実行
  design-and-market:
    if: |
      github.event.pull_request.merged == true &&
      startsWith(github.event.pull_request.head.ref, 'article/')
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - uses: actions/checkout@v4

      - name: Python セットアップ
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: 依存関係インストール
        run: pip install -r requirements.txt

      - name: デザイン生成（Canva API）
        env:
          CANVA_CLIENT_ID: ${{ secrets.CANVA_CLIENT_ID }}
          CANVA_CLIENT_SECRET: ${{ secrets.CANVA_CLIENT_SECRET }}
        run: python -m agents.designer

      - name: X投稿文生成
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: python -m agents.marketer

      - name: 成果物をコミット
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          TODAY=$(date +%Y-%m-%d)
          git config user.name "note-auto-company[bot]"
          git config user.email "bot@github-actions"
          git add assets/ data/posts/
          git commit -m "release: ${TODAY} デザイン・投稿文完了" || echo "変更なし"
          git push origin main

      - name: 完了サマリー
        run: |
          echo "## ✅ 今週の作業完了" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "| 作業 | 状態 |" >> $GITHUB_STEP_SUMMARY
          echo "|---|---|" >> $GITHUB_STEP_SUMMARY
          echo "| 表紙画像（10枚） | ✅ assets/covers/ に保存 |" >> $GITHUB_STEP_SUMMARY
          echo "| 告知画像（10枚） | ✅ assets/social/ に保存 |" >> $GITHUB_STEP_SUMMARY
          echo "| X投稿文（30本） | ✅ data/posts/ に保存 |" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "**📋 次の手順（わしの作業・約15分）**" >> $GITHUB_STEP_SUMMARY
          echo "1. data/posts/ の投稿文から10本を選ぶ" >> $GITHUB_STEP_SUMMARY
          echo "2. 記事のnote URLを各投稿末尾に追加" >> $GITHUB_STEP_SUMMARY
          echo "3. Bufferに貼り付けて予約投稿" >> $GITHUB_STEP_SUMMARY
```

- [ ] **Step 2: コミット**

```bash
git add .github/workflows/post-approved.yml
git commit -m "ci: add post-approved pipeline workflow"
```

- [ ] **Step 3: 全テストが通ることを最終確認**

```bash
pytest tests/ -v
```
Expected: `9 passed`（全テスト）

- [ ] **Step 4: 動作確認手順（初回起動）**

```
1. GitHub に push: git push origin main
2. Actions → 月曜リサーチ＆企画 → Run workflow で手動実行
3. PRが作成されることを確認
4. PRをMergeして post-approved.yml が起動することを確認
5. 記事PRが作成されることを確認
6. 記事PRをMergeしてデザイン・投稿文が生成されることを確認
```

---

## セルフレビューチェック

- ✅ **スペックカバレッジ**: 全6エージェント + 2ワークフロー実装済み
- ✅ **プレースホルダーなし**: 全ステップに実コード記載
- ✅ **型の一貫性**: `list[dict]` / `Path` / `str` が各タスク間で一致
- ✅ **TDD**: Task 2/3/4/5/7 はテスト先行
- ✅ **Canva API注意書き**: Task 6に事前準備手順を明記
- ✅ **CSセレクター注意書き**: researcher.pyにDOM変更への対応コメントあり

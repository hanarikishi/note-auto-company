# 500円note放置自動会社 設計書

**作成日**: 2026-08-23  
**ステータス**: 設計承認済み

---

## 概要

noteで500円記事を自動生成・販売するシステム。6つのAIエージェントが週次バッチで動作し、人間（オーナー）はGitHub PRの承認・差し戻しのみを行う。

---

## 技術スタック

| 項目 | 選択 |
|---|---|
| 実行環境 | GitHub Actions（クラウド） |
| リサーチ手法 | note.com スクレイピング |
| AI | Claude API（Haiku 4.5：軽量タスク、Sonnet 4.6：執筆・検品） |
| SNS投稿 | Buffer無料プラン（10投稿/月）→ 軌道後にX API v2へ移行 |
| 画像生成 | Canva API |
| 承認フロー | GitHub Pull Request（Merge=承認、Close=差し戻し） |
| データ保存 | GitHubリポジトリ内（JSON / CSV / Markdown） |
| 月額コスト | 約220円（Claude APIのみ。GitHub・Bufferは無料枠） |

---

## アーキテクチャ（週次バッチ方式）

### フェーズ1：月曜朝9時（自動起動）

```
GitHub Actions (monday-research.yml)
  └─ researcher.py   ← note.com スクレイピング → 500円売れ筋テーマ抽出
  └─ planner.py      ← 過去売れ行きDB参照 → テーマ10本提案（優先スコア付き）
  └─ PR①自動作成     ← plans/YYYY-MM-DD-proposals.md
```

**人間の作業**: PR①を確認 → Merge（承認）or Close（差し戻し）

---

### フェーズ2：PR① Merge後（自動起動）

```
GitHub Actions (post-approved.yml)
  └─ writer.py       ← 承認テーマ1位を執筆（4,000〜5,000字）
  └─ inspector.py    ← 辛口編集者ペルソナでAI臭い表現を修正
  └─ PR②自動作成     ← articles/final/YYYY-MM-DD-final.md
```

**人間の作業**: PR②を確認 → Merge（承認）or Close（差し戻し）

---

### フェーズ3：PR② Merge後（自動起動）

```
  └─ designer.py     ← Canva API → 表紙10パターン + 告知画像10パターン
  └─ marketer.py     ← Claude API → X投稿文30本生成 → data/posts/に出力
  └─ 完了通知        ← GitHub Actions サマリーに出力
```

**人間の作業**: data/posts/から10本選んでBufferに貼り付け予約（約15分）

---

## エージェント詳細仕様

### 🔍 リサーチ担当（researcher.py）

- **モデル**: claude-haiku-4-5
- **実行**: 毎週月曜 09:00 JST
- **処理**:
  1. note.comの「売れている記事」ページをスクレイピング
  2. 500円記事を抽出（タイトル・いいね数・販売数推定）
  3. Claude APIで「1年後も需要があるか」を判定・スコアリング
- **出力**: `data/research/YYYY-MM-DD.json`

```json
{
  "date": "2026-08-23",
  "articles": [
    {
      "title": "記事タイトル",
      "likes": 120,
      "theme": "副業",
      "longevity_score": 8.5
    }
  ]
}
```

---

### 📋 企画担当（planner.py）

- **モデル**: claude-haiku-4-5
- **実行**: researcher.py完了後
- **処理**:
  1. `data/research/*.json`（過去全件）を参照
  2. `data/sales_history.csv`（過去の自分の売れ行き）を参照
  3. Claude APIで次に書くべきテーマ10本を優先スコア付きで提案
- **出力**: `plans/YYYY-MM-DD-proposals.md`（PR①として提出）

---

### ✍️ 執筆担当（writer.py）

- **モデル**: claude-sonnet-4-6
- **実行**: PR① Merge後
- **処理**:
  1. 承認されたテーマ（proposals.mdの1位）を取得
  2. 構成設計：冒頭1,500字＝無料公開部分（読者を引き込む）、残り2,500〜3,500字＝有料部分
  3. Claude APIで4,000〜5,000字の記事を生成
- **出力**: `articles/drafts/YYYY-MM-DD-draft.md`

---

### 🔬 検品担当（inspector.py）

- **モデル**: claude-sonnet-4-6
- **実行**: writer.py完了後
- **処理**:
  1. 別システムプロンプト（辛口な編集者ペルソナ）でClaude APIを呼び出し
  2. AI臭い表現（「〜となっています」「〜することができます」等）を検出・修正
  3. 体温のある文体に変換
- **出力**: `articles/final/YYYY-MM-DD-final.md`（PR②として提出）

---

### 🎨 デザイン担当（designer.py）

- **モデル**: Canva API
- **実行**: PR② Merge後
- **処理**:
  1. 記事タイトルと本文要約をCanva APIに渡す
  2. note表紙（1280×670px）10パターンを生成
  3. X告知用正方形画像（1200×1200px）10パターンを生成
- **出力**: `assets/covers/` と `assets/social/`

---

### 📣 営業担当（marketer.py）

- **モデル**: claude-haiku-4-5
- **実行**: designer.py完了後
- **処理**:
  1. 記事タイトル・本文要約・画像パスを受け取る
  2. X投稿文30本を生成（告知・共感・引用・ネタバレなしの4パターンをローテーション）
  3. Markdownファイルに出力（Bufferへの手動貼り付け用）
- **出力**: `data/posts/YYYY-MM-DD-posts.md`

---

## ディレクトリ構成

```
note-auto-company/
├── .github/
│   └── workflows/
│       ├── monday-research.yml    # 月曜9時：リサーチ+企画
│       └── post-approved.yml      # PR Merge後：執筆→検品→デザイン→営業
├── agents/
│   ├── researcher.py
│   ├── planner.py
│   ├── writer.py
│   ├── inspector.py
│   ├── designer.py
│   └── marketer.py
├── data/
│   ├── research/                  # YYYY-MM-DD.json
│   ├── sales_history.csv          # 過去売れ行きDB
│   └── posts/                     # YYYY-MM-DD-posts.md（投稿30本）
├── articles/
│   ├── drafts/                    # 執筆担当の出力
│   └── final/                     # 検品済み記事
├── assets/
│   ├── covers/                    # note表紙画像
│   └── social/                    # X告知画像
├── plans/
│   └── YYYY-MM-DD-proposals.md   # 企画10本提案
├── config.yml                     # テーマ・NGワード等の設定
└── requirements.txt
```

---

## 人間の週次作業（目標：合計30分以内）

| タイミング | 作業 | 所要時間 |
|---|---|---|
| 月曜午前 | PR①確認（テーマ10本）→ Merge or Close | 5分 |
| 月曜〜火曜 | PR②確認（記事本文）→ Merge or Close | 10分 |
| 週内任意 | 投稿30本からBufferに10本コピペして予約 | 15分 |
| **合計** | | **約30分/週** |

---

## スケールアップ計画

| フェーズ | 条件 | 変更内容 |
|---|---|---|
| 現状 | 立ち上げ期 | Buffer無料10本/月 |
| Phase 2 | 月5万円売上達成 | X API Basic（$100/月）で自動予約投稿 |
| Phase 3 | 月10万円売上達成 | 週2本ペースに増産（並列エージェント化） |

---

## 環境変数（GitHub Actions Secrets）

```
ANTHROPIC_API_KEY      # Claude API
CANVA_API_KEY          # Canva Connect API
NOTE_SESSION_COOKIE    # noteスクレイピング用（必要な場合）
```

---

## 未確認事項（実装前に要確認）

1. **Canva Connect API** の無料枠でのテンプレート生成可否
2. **note.com利用規約** のスクレイピング許可範囲（公開情報の個人利用）
3. **Buffer無料プラン** のAPI連携の有無（なければ手動コピペのみ）

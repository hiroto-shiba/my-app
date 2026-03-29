## Mandatory Rules for Claude Code
- 必ず日本語で回答

- Do NOT modify any files unless explicitly instructed.
- Do NOT refactor existing code unless clearly requested.
- Prefer minimal, localized changes over large improvements.
- Stability and existing behavior are more important than code cleanliness.

## Change Proposal Requirement

Before making any code changes:
- Explain what will be changed
- Explain why it is necessary
- Describe potential risks or side effects

Wait for explicit approval before proceeding.

## Cost Awareness

- Keep responses concise.
- Avoid repeating large code blocks unless necessary.
- Prefer explanation over full implementation when possible.

## Model Usage Policy

- Use the Default (recommended) model for all tasks.
- The Default model is currently Sonnet 4.5.
- Do NOT switch to Opus unless explicitly instructed by the user.
- Prefer lower-cost models unless higher capability is required.

## プロジェクト概要

Zaim APIとClaude APIを使った個人家計管理Webアプリ。収入・支出の日次/月次ビューとカテゴリ別分析を提供する。

## セットアップ

```bash
pip install -r requirements.txt
```

`.env` に以下を設定（gitignore済み）:
```
ZAIM_CONSUMER_KEY=...
ZAIM_CONSUMER_SECRET=...
ANTHROPIC_API_KEY=...
```

## アプリ起動

```bash
streamlit run app.py
```

初回起動後、UIから「Zaimで認証する」をクリックしてOAuth連携を行う。

## アーキテクチャ

- **app.py** — Streamlit UI。4タブ構成（日次・月次・カテゴリ・収入）。OAuth callbackの処理もここで行う。
- **zaim_client.py** — Zaim APIクライアント。OAuth 1.0a認証フロー・トークン管理・データ取得。トークンは `.zaim_tokens.json` にローカル保存。
- **categorizer.py** — Claude API (`claude-sonnet-4-6`) を使った取引名→支出カテゴリの一括推定。カテゴリは固定14種。
- **.env** — 認証情報（gitignore済み）

## データフロー

1. Zaimに金融機関（ゆうちょ・イオンカード・楽天カード）を連携済みであることが前提
2. アプリからZaim APIで取引データを取得（`/v2/home/money`）
3. 支出レコードの取引名をClaudeで一括カテゴリ分類（セッション内キャッシュあり）
4. Streamlit UIで可視化
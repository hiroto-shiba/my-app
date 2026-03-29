import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

CATEGORIES = [
    "食費",
    "外食・カフェ",
    "交通費",
    "日用品",
    "衣服・美容",
    "医療・健康",
    "娯楽・趣味",
    "教育・書籍",
    "通信費",
    "光熱費・水道",
    "家賃・住居",
    "保険",
    "給与・収入",
    "その他",
]

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def classify_transactions(names: list[str]) -> list[str]:
    """取引名のリストからカテゴリを一括推定する"""
    if not names:
        return []

    prompt = f"""以下の取引名それぞれについて、最も適切な支出カテゴリを1つ選んでください。

カテゴリ一覧:
{json.dumps(CATEGORIES, ensure_ascii=False)}

取引名リスト:
{json.dumps(names, ensure_ascii=False)}

回答はJSON配列で、取引名と同じ順序でカテゴリ名のみを返してください。
例: ["食費", "交通費", "外食・カフェ"]"""

    client = _get_client()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    text = message.content[0].text.strip()
    # JSONブロックが含まれる場合は抽出
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)

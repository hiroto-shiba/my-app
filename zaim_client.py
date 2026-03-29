import os
import json
from typing import Optional
from requests_oauthlib import OAuth1Session
from dotenv import load_dotenv

load_dotenv()

CONSUMER_KEY = os.getenv("ZAIM_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("ZAIM_CONSUMER_SECRET")
REQUEST_TOKEN_URL = "https://api.zaim.net/v2/auth/request"
AUTH_URL = "https://auth.zaim.net/users/auth"
ACCESS_TOKEN_URL = "https://api.zaim.net/v2/auth/access"
CALLBACK_URL = "http://localhost:8501/"
TOKEN_FILE = ".zaim_tokens.json"
REQUEST_TOKEN_FILE = ".zaim_request_token.json"


def get_authorization_url() -> str:
    """OAuth認証URLを取得し、リクエストトークンをファイルに保存する"""
    oauth = OAuth1Session(
        CONSUMER_KEY,
        client_secret=CONSUMER_SECRET,
        callback_uri=CALLBACK_URL,
    )
    fetch_response = oauth.fetch_request_token(REQUEST_TOKEN_URL)
    with open(REQUEST_TOKEN_FILE, "w") as f:
        json.dump({
            "oauth_token": fetch_response.get("oauth_token"),
            "oauth_token_secret": fetch_response.get("oauth_token_secret"),
        }, f)
    return oauth.authorization_url(AUTH_URL)


def load_request_token() -> Optional[dict]:
    """保存済みリクエストトークンを読み込んで削除する"""
    if not os.path.exists(REQUEST_TOKEN_FILE):
        return None
    with open(REQUEST_TOKEN_FILE) as f:
        data = json.load(f)
    os.remove(REQUEST_TOKEN_FILE)
    return data


def fetch_access_token(
    resource_owner_key: str,
    resource_owner_secret: str,
    oauth_verifier: str,
) -> dict:
    """アクセストークンを取得して保存する"""
    oauth = OAuth1Session(
        CONSUMER_KEY,
        client_secret=CONSUMER_SECRET,
        resource_owner_key=resource_owner_key,
        resource_owner_secret=resource_owner_secret,
        verifier=oauth_verifier,
    )
    tokens = oauth.fetch_access_token(ACCESS_TOKEN_URL)
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f)
    return tokens


def load_tokens() -> Optional[dict]:
    """保存済みトークンを読み込む"""
    if not os.path.exists(TOKEN_FILE):
        return None
    with open(TOKEN_FILE) as f:
        return json.load(f)


def get_session() -> Optional[OAuth1Session]:
    """認証済みOAuthセッションを返す"""
    tokens = load_tokens()
    if not tokens:
        return None
    return OAuth1Session(
        CONSUMER_KEY,
        client_secret=CONSUMER_SECRET,
        resource_owner_key=tokens["oauth_token"],
        resource_owner_secret=tokens["oauth_token_secret"],
    )


def fetch_money(start_date: str, end_date: str) -> list[dict]:
    """支出・収入データを取得する (YYYY-MM-DD形式)"""
    session = get_session()
    if not session:
        raise RuntimeError("未認証です。先にZaimと連携してください。")

    all_records = []
    page = 1
    while True:
        resp = session.get(
            "https://api.zaim.net/v2/home/money",
            params={
                "start_date": start_date,
                "end_date": end_date,
                "limit": 100,
                "page": page,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        records = data.get("money", [])
        if not records:
            break
        all_records.extend(records)
        if len(records) < 100:
            break
        page += 1

    return all_records


def verify_user() -> dict:
    """ログインユーザー情報を取得して認証確認"""
    session = get_session()
    if not session:
        raise RuntimeError("未認証")
    resp = session.get("https://api.zaim.net/v2/home/user")
    resp.raise_for_status()
    return resp.json()

# app/services/gemini_client.py
from google import genai
from google.genai import types
import json

from app.config import settings


client = genai.Client(api_key=settings.gemini_api_key)


def analyze_commits(parsed_log: str) -> dict:
    """Geminiにgit logを渡してスコアとレポートを取得"""
    
    # JSONスキーマを定義
    schema = {
        "type": "object",
        "properties": {
            "scores": {
                "type": "object",
                "properties": {
                    "test": {"type": "integer"},
                    "comment": {"type": "integer"},
                    "commit_size": {"type": "integer"},
                    "commit_frequency": {"type": "integer"},
                    "commit_message": {"type": "integer"},
                    "activity": {"type": "integer"},
                },
                "required": ["test", "comment", "commit_size", "commit_frequency", "commit_message", "activity"],
            },
            "report": {
                "type": "object",
                "properties": {
                    "test": {"type": "string"},
                    "comment": {"type": "string"},
                    "commit_size": {"type": "string"},
                    "commit_frequency": {"type": "string"},
                    "commit_message": {"type": "string"},
                    "activity": {"type": "string"},
                },
                "required": ["test", "comment", "commit_size", "commit_frequency", "commit_message", "activity"],
            },
        },
        "required": ["scores", "report"],
    }
    
    prompt = f"""
以下のgit logを分析して、開発者の評価をしてください。

【git log】
{parsed_log}

【評価項目（各0〜100点）】
- test: テストコードの有無・割合
- comment: コメントの質・量
- commit_size: 1コミットの適切さ（小さいほど高評価）
- commit_frequency: コミット頻度
- commit_message: メッセージの質（Conventional Commits準拠など）
- activity: 稼働の安定性
"""
    
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    
    result = json.loads(response.text)
    
    return result
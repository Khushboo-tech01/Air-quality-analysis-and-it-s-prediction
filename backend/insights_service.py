"""AI Insights — natural language explanation of pollution trends via Claude Sonnet."""
import os
import json
from emergentintegrations.llm.chat import LlmChat, UserMessage


SYSTEM_MSG = (
    "You are an environmental data-science analyst. Given a JSON summary of an air-quality "
    "dataset (statistics, trends, dominant pollutants), write a concise 3-paragraph insight "
    "for a general audience. Paragraph 1: overall air-quality picture. Paragraph 2: notable "
    "trends & correlations. Paragraph 3: practical recommendations. Do NOT use markdown "
    "headings, bullet points or emoji. Plain prose only. Around 180 words total."
)


async def generate_insight(summary: dict, session_id: str) -> str:
    api_key = os.environ["EMERGENT_LLM_KEY"]
    chat = (
        LlmChat(api_key=api_key, session_id=session_id, system_message=SYSTEM_MSG)
        .with_model("anthropic", "claude-sonnet-4-5-20250929")
    )
    payload = json.dumps(summary, default=str)[:6000]
    msg = UserMessage(text=f"Dataset summary:\n{payload}\n\nWrite the 3-paragraph insight.")
    reply = await chat.send_message(msg)
    if isinstance(reply, str):
        return reply.strip()
    return str(reply).strip()

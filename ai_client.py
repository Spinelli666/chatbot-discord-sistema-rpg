import os
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = (
    "Você é um especialista no sistema de RPG Cardigan. "
    "Responda apenas com base nas regras fornecidas no contexto abaixo. "
    "Não invente regras. Se a informação não estiver no contexto, diga que não encontrou "
    "nas regras do Cardigan. Seja claro e direto."
)


def get_response(question: str, context: str) -> str:
    provider = os.getenv("AI_PROVIDER", "anthropic").lower()
    if provider == "openai":
        return _openai(question, context)
    return _anthropic(question, context)


def _anthropic(question: str, context: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    msg = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", "claude-opus-4-7"),
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": f"Contexto das regras:\n{context}\n\nPergunta: {question}",
            }
        ],
    )
    return msg.content[0].text


def _openai(question: str, context: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Contexto das regras:\n{context}\n\nPergunta: {question}",
            },
        ],
    )
    return resp.choices[0].message.content

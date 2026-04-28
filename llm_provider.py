import os


_SYSTEM_PROMPT = (
    "Você é um especialista no sistema de RPG Cardigan. "
    "Responda com base no contexto fornecido das regras. "
    "Seja objetivo, claro e cite os valores numéricos exatos quando presentes. "
    "Se a resposta não estiver no contexto, diga que não encontrou nas regras."
)


class OfflineProvider:
    def generate_response(self, context: str, question: str) -> str:
        if not context.strip():
            return (
                "Não encontrei informações sobre isso nas regras do Cardigan.\n"
                "Tente usar `!buscar [termo]` com palavras-chave diferentes."
            )
        return context


class OnlineProvider:
    def __init__(self) -> None:
        self._provider = os.getenv("AI_PROVIDER", "anthropic").lower()

    def generate_response(self, context: str, question: str) -> str:
        if not context.strip():
            return (
                "Não encontrei informações relevantes nas regras para responder sua pergunta."
            )
        if self._provider == "openai":
            return self._openai(context, question)
        return self._anthropic(context, question)

    def _anthropic(self, context: str, question: str) -> str:
        import anthropic  # type: ignore

        client = anthropic.Anthropic()
        message = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Contexto das regras:\n{context}\n\n"
                        f"Pergunta: {question}"
                    ),
                }
            ],
        )
        return message.content[0].text

    def _openai(self, context: str, question: str) -> str:
        from openai import OpenAI  # type: ignore

        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Contexto das regras:\n{context}\n\n"
                        f"Pergunta: {question}"
                    ),
                },
            ],
            max_tokens=1024,
        )
        return response.choices[0].message.content


def get_provider() -> OfflineProvider | OnlineProvider:
    if os.getenv("USE_LLM", "false").lower() == "true":
        return OnlineProvider()
    return OfflineProvider()

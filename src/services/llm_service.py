import logging
import os
from abc import ABC, abstractmethod

import tiktoken
from dotenv import load_dotenv

load_dotenv()


class BaseLLMService(ABC):
    def __init__(self, model_name: str, encoding_name: str = "o200k_base"):
        self.model_name = model_name
        try:
            self.encoder = tiktoken.encoding_for_model(model_name)
        except Exception as e:
            logging.warning(
                f"Não foi possível carregar a codificação para o modelo {model_name}: {e}. Usando 'cl100k_base' como padrão."
            )
            self.encoder = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, prompt: str) -> int:
        tokens_list = self.encoder.encode(prompt)

        return len(tokens_list)

    def prompt(self, question: str, search_results: list) -> str:
        context_block = []

        for search in search_results:
            block = (
                f"### TRECHO DE DOCUMENTO {search.payload['filename']}\n"
                f"**LOCALIZAÇÃO:** Página {search.payload['page_numbers']}\n"
                f"**CONTEÚDO:** {search.payload['content']}"
            )
            context_block.append(block)

        context_str = "---".join(context_block)

        final_prompt = (
            f"Responda com base no seguinte contexto:"
            f"\n\n{context_str}\n\nPergunta: {question}"
        )

        return final_prompt

    @abstractmethod
    def ask_llm(self, prompt: str) -> str:
        pass


class OpenAILLMService(BaseLLMService):
    def __init__(self):
        super().__init__(model_name=os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini"))
        from openai import OpenAI

        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "api_key_not_set"))

    def ask_llm(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": "Você é um assistente que responde apenas com base no contexto fornecido. Se não souber, diga que não sabe.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
            n=1,
            stop=None,
            temperature=0,
        )

        message = response.choices[0].message
        answer = getattr(message, "content", "") or ""

        return answer.strip()


class GroqLLMService(BaseLLMService):
    def __init__(self):
        super().__init__(
            model_name=os.getenv("GROQ_MODEL_NAME", "gpt-oss-120b"),
            encoding_name="o200k_harmony",
        )
        from groq import Groq

        self.client = Groq(api_key=os.getenv("GROQ_API_KEY", "api_key_not_set"))

    def ask_llm(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {
                    "role": "system",
                    "content": "Você é um assistente que responde apenas com base no contexto fornecido. Se não souber, diga que não sabe.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
            n=1,
            stop=None,
            temperature=0,
        )
        message = response.choices[0].message
        answer = getattr(message, "content", "") or ""
        return answer.strip()


def get_llm_service() -> BaseLLMService:
    try:
        llm_provider = os.getenv("LLM_PROVIDER")
        if llm_provider.lower() == "groq":
            return GroqLLMService()
        elif llm_provider.lower() == "openai":
            return OpenAILLMService()
        else:
            raise ValueError(
                "Provedor LLM inválido. Use 'openai' ou 'groq' na variável de ambiente LLM_PROVIDER."
            )
    except Exception as e:
        logging.warning(f"Erro ao obter o provedor LLM: {e}")
        return GroqLLMService()

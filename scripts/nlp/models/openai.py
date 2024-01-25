from models.llm import LLM
from openai import OpenAI
from openai.types.chat import ChatCompletion
import os
import sys
import time

class GPT(LLM):
    def __init__(self, model: str, timeout: int, top_p: float, **kwargs):
        self.model = model
        self.client = OpenAI(api_key = os.getenv("OPENAI_API_KEY"))
        self.timeout = timeout
        self.top_p = top_p

    def run(self, header: str, questions, max_tokens: int, num_responses: int, combine_responses: bool, escape: bool):
        print(header, "query", "responses", "input token count", "output token count", "question number", sep="\t")
        for i, (input, question) in enumerate(questions):
            # See https://platform.openai.com/docs/api-reference/chat/create
            response = self.query_openai(question, n=num_responses, top_p=self.top_p, max_tokens=max_tokens, timeout=self.timeout)
            answers = [choice.message.content for choice in response.choices]
            if combine_responses:
                answers = [" ".join(answers)]
            for answer in answers:
                print(input, repr(question), repr(answer) if escape else answer, response.usage.prompt_tokens, response.usage.completion_tokens, i, sep="\t", flush=True)

    # For kwargs see https://platform.openai.com/docs/api-reference/chat/create
    def query_openai(self, query: str, **kwargs) -> ChatCompletion:
        while (True):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": query}],
                    **kwargs
                )
                return response
            except Exception as e:
                print("Request failed:", e, file=sys.stderr)
                time.sleep(5)
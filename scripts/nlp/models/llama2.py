from models.llm import LLM
from transformers import LlamaTokenizer, LlamaForCausalLM
import torch
from typing import Iterable


class Llama2(LLM):
    def __init__(
        self,
        model: str,
        max_tokens: int,
        num_responses: int,
        top_p: float,
        top_k: int,
        api_access_key: str,
        **kwargs,
    ):
        self.max_tokens = max_tokens
        self.num_responses = num_responses
        self.top_p = top_p
        self.top_k = top_k
        self.input_query_buffer = list()

        self.tokenizer = LlamaTokenizer.from_pretrained(model, token=api_access_key)
        self.tokenizer.pad_token = "[PAD]"
        self.tokenizer.padding_side = "left"

        self.model = LlamaForCausalLM.from_pretrained(
            model, token=api_access_key, device_map="auto", torch_dtype=torch.bfloat16
        )
        self.model.tie_weights()

    def run(
        self,
        queries: Iterable[tuple[str, str]],
        num_responses: int,
        combine_responses: bool,
        escape: bool,
    ):
        question_number = 0
        compile_output = lambda input, output: (
            input,
            output | {"question number": question_number},
        )

        for input1, query in queries:
            # Collect inputs to run in batches
            self.input_query_buffer += [(input1, query)]

            # Check if any results are ready
            for result in self.query_llama2():
                question_number += 1
                yield compile_output(*result)

        # Force the LLM to run even if we don't have a full batch
        for result in self.query_llama2(flush=True):
            question_number += 1
            yield compile_output(*result)

    def query_llama2(self, flush=False, **kwargs):
        if self.num_responses <= 1:
            return self.query_llama2_once(flush, **kwargs)
        else:
            return self.query_llama2_with_sampling(flush, **kwargs)
    
    def combine_responses(self, query: str, sequences: torch.Tensor) -> list[str]:
        responses = []
        for sequence in sequences:
            response = self.tokenizer.decode(sequence, skip_special_tokens=True).removeprefix(query).strip().split()[0].replace(",", "")
            responses += [response]
        return responses
        
    def query_llama2_with_sampling(self, flush=False, **kwargs):
        TARGET_INPUT_SIZE = 35 * 10  # By trial-and-error

        if len(self.input_query_buffer) > 0:
            queries = [q for i, q in self.input_query_buffer]
            input_ids = self.tokenizer(
                queries, return_tensors="pt", padding=True
            ).input_ids.to("cuda")

            if True: #flush or input_ids.numel() >= TARGET_INPUT_SIZE:
                input_length = input_ids.shape[1] * self.num_responses
                max_completion_length = input_length + self.max_tokens
                outputs = self.model.generate(
                    input_ids,
                    max_length=max_completion_length,
                    return_dict_in_generate=True,
                    output_scores=True,
                    low_memory=True,
                    do_sample=True,
                    top_p=self.top_p,
                    top_k=self.top_k,
                    num_return_sequences=self.num_responses
                )

                for sequence_index, (input, query) in enumerate(
                    self.input_query_buffer
                ):
                    first_response = sequence_index * self.num_responses
                    next_first_response = (sequence_index + 1) * self.num_responses
                    responses = self.combine_responses(query, outputs.sequences[first_response:next_first_response])

                    yield (
                        input,
                        {
                            "query": repr(query),
                            "responses": ",".join(responses)
                        }
                    )

                self.input_query_buffer.clear()

    def query_llama2_once(self, flush=False, **kwargs):
        TARGET_INPUT_SIZE = 35 * 100  # By trial-and-error

        if len(self.input_query_buffer) > 0:
            queries = [q for i, q in self.input_query_buffer]
            input_ids = self.tokenizer(
                queries, return_tensors="pt", padding=True
            ).input_ids.to("cuda")

            if flush or input_ids.numel() >= TARGET_INPUT_SIZE:
                input_length = input_ids.shape[1]
                max_completion_length = input_length + self.max_tokens
                outputs = self.model.generate(
                    input_ids,
                    max_length=max_completion_length,
                    return_dict_in_generate=True,
                    output_scores=True,
                    low_memory=True
                )

                for sequence_index, (input, query) in enumerate(
                    self.input_query_buffer
                ):
                    response = outputs.sequences[sequence_index][input_length:]
                    response_string = self.tokenizer.decode(
                        response, skip_special_tokens=True
                    )

                    token_index = self.index_of_first_non_whitespace_token(response)

                    top_k_results = outputs.scores[token_index][sequence_index].topk(
                        self.top_k
                    )
                    top_k_token_scores = [f"{x:.5g}" for x in top_k_results.values]
                    top_k_token_strings = [
                        self.tokenizer.decode([t], skip_special_tokens=True).lstrip()
                        for t in top_k_results.indices
                    ]

                    yield (
                        input,
                        {
                            "query": repr(query),
                            "response": repr(response_string),
                            "first token top strings": repr(top_k_token_strings),
                            "first token top scores": repr(top_k_token_scores),
                        }
                    )

                self.input_query_buffer.clear()

    def index_of_first_non_whitespace_token(self, sequence: torch.Tensor):
        for i, token in enumerate(sequence):
            token_string = self.tokenizer.decode(sequence[i].unsqueeze(0))
            if not token_string.isspace():
                return i

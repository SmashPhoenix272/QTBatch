import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_fixed

class GoogleGenerativeAIProvider:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.configure_genai()

    def configure_genai(self):
        genai.configure(api_key=self.api_key)

    def estimate_token_count(self, text: str) -> int:
        model = genai.GenerativeModel(self.model)
        return model.count_tokens(text).total_tokens

    def get_usage_metadata(self, response) -> Dict[str, int]:
        return {
            "prompt_token_count": response.usage_metadata.prompt_token_count,
            "candidates_token_count": response.usage_metadata.candidates_token_count,
            "total_token_count": response.usage_metadata.total_token_count
        }

    def calculate_cost(self, input_tokens: int, output_tokens: int, context_length: int = 0) -> float:
        input_cost = 0
        output_cost = 0

        if self.model == "gemini-1.5-flash":
            if context_length <= 128000:
                input_cost = input_tokens * 0.00001875 / 1000
                output_cost = output_tokens * 0.000075 / 1000
            else:
                input_cost = input_tokens * 0.0000375 / 1000
                output_cost = output_tokens * 0.00015 / 1000
        elif self.model == "gemini-1.5-pro":
            if context_length <= 128000:
                input_cost = input_tokens * 0.00125 / 1000
                output_cost = output_tokens * 0.00375 / 1000
            else:
                input_cost = input_tokens * 0.0025 / 1000
                output_cost = output_tokens * 0.0075 / 1000
        elif self.model == "gemini-1.0-pro":
            input_cost = input_tokens * 0.000125 / 1000
            output_cost = output_tokens * 0.000375 / 1000

        return input_cost + output_cost

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def generate_content(self, prompt: str, safety_settings: Optional[Dict] = None, generation_config: Optional[Dict] = None) -> Any:
        model = genai.GenerativeModel(self.model)
        
        if safety_settings is None:
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }

        if generation_config is None:
            generation_config = genai.types.GenerationConfig(
                candidate_count=1,
                stop_sequences=["</TL>"],
                max_output_tokens=8192,
            )

        response = model.generate_content(
            prompt,
            safety_settings=safety_settings,
            generation_config=generation_config
        )

        return response
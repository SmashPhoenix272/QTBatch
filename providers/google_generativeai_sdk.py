import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.generativeai import caching
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_fixed
import datetime

class GoogleGenerativeAIProvider:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.configure_genai()
        self.cached_content = None

    def configure_genai(self):
        genai.configure(api_key=self.api_key)

    def estimate_token_count(self, text: str) -> int:
        model = genai.GenerativeModel(self.model)
        return model.count_tokens(text).total_tokens

    def get_usage_metadata(self, response) -> Dict[str, int]:
        return {
            "prompt_token_count": response.usage_metadata.prompt_token_count,
            "candidates_token_count": response.usage_metadata.candidates_token_count,
            "total_token_count": response.usage_metadata.total_token_count,
            "cached_content_token_count": response.usage_metadata.cached_content_token_count if hasattr(response.usage_metadata, 'cached_content_token_count') else 0
        }

    def calculate_cost(self, input_tokens: int, output_tokens: int, context_length: int = 0, cache_tokens: int = 0) -> float:
        input_cost = 0
        output_cost = 0
        cache_cost = 0

        if self.model == "gemini-1.5-flash":
            if context_length <= 128000:
                input_cost = input_tokens * 0.000075 / 1000000
                output_cost = output_tokens * 0.00030 / 1000000
                cache_cost = cache_tokens * 0.00001875 / 1000000
            else:
                input_cost = input_tokens * 0.00015 / 1000000
                output_cost = output_tokens * 0.00060 / 1000000
                cache_cost = cache_tokens * 0.0000375 / 1000000
            # Add storage cost for context caching
            cache_cost += cache_tokens * 0.000001 / 1000000  # $1.00 per million tokens per hour
        elif self.model == "gemini-1.5-pro":
            if context_length <= 128000:
                input_cost = input_tokens * 0.00350 / 1000000
                output_cost = output_tokens * 0.01050 / 1000000
                cache_cost = cache_tokens * 0.000875 / 1000000
            else:
                input_cost = input_tokens * 0.00700 / 1000000
                output_cost = output_tokens * 0.02100 / 1000000
                cache_cost = cache_tokens * 0.00175 / 1000000
            # Add storage cost for context caching
            cache_cost += cache_tokens * 0.0000045 / 1000000  # $4.50 per million tokens per hour
        elif self.model == "gemini-1.0-pro":
            input_cost = input_tokens * 0.00050 / 1000000
            output_cost = output_tokens * 0.00150 / 1000000
            # Context caching not available for Gemini 1.0 Pro

        return input_cost + output_cost + cache_cost

    def create_context_cache(self, display_name: str, system_instruction: str, contents: List[Any], ttl: int = 5):
        self.cached_content = caching.CachedContent.create(
            model=self.model,
            display_name=display_name,
            system_instruction=system_instruction,
            contents=contents,
            ttl=datetime.timedelta(minutes=ttl)
        )

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def generate_content(self, prompt: str, safety_settings: Optional[Dict] = None, generation_config: Optional[Dict] = None) -> Any:
        if self.cached_content:
            model = genai.GenerativeModel.from_cached_content(cached_content=self.cached_content)
        else:
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

    def update_context_cache(self, translated_text: str):
        self.create_context_cache(
            display_name="Proofreading Context",
            system_instruction="You are an expert in proofreading Sino-Vietnamese translations. Use the provided context to improve your proofreading results.",
            contents=[translated_text],
            ttl=10  # Cache for 10 minutes
        )
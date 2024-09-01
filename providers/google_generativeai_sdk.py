import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.generativeai import caching
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_fixed
import datetime
import logging

# Initialize logger
logger = logging.getLogger('google_generativeai_sdk')
logger.setLevel(logging.DEBUG)
log_handler = logging.FileHandler('google_generativeai_sdk.log', encoding='utf-8')
log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(log_handler)

class GoogleGenerativeAIProvider:
    def __init__(self, api_key: str, model: str, context_caching: bool = True):
        self.api_key = api_key
        self.model = model
        self.context_caching = context_caching
        logger.info(f"Initializing GoogleGenerativeAIProvider with model: {self.model}, context_caching: {self.context_caching}")
        self.configure_genai()
        self.cached_content = None

    def configure_genai(self):
        logger.info(f"Configuring genai with API key: {self.api_key[:5]}...")
        genai.configure(api_key=self.api_key)

    def estimate_token_count(self, text: str) -> int:
        logger.debug(f"Estimating token count for text: {text[:50]}...")
        model = genai.GenerativeModel(self.model)
        return model.count_tokens(text).total_tokens

    def get_usage_metadata(self, response) -> Dict[str, int]:
        logger.debug("Getting usage metadata from response")
        return {
            "prompt_token_count": response.usage_metadata.prompt_token_count,
            "candidates_token_count": response.usage_metadata.candidates_token_count,
            "total_token_count": response.usage_metadata.total_token_count,
            "cached_content_token_count": response.usage_metadata.cached_content_token_count if hasattr(response.usage_metadata, 'cached_content_token_count') else 0
        }

    def calculate_cost(self, input_tokens: int, output_tokens: int, context_length: int = 0, cache_tokens: int = 0) -> float:
        logger.debug(f"Calculating cost for input_tokens: {input_tokens}, output_tokens: {output_tokens}, context_length: {context_length}, cache_tokens: {cache_tokens}")
        input_cost = 0
        output_cost = 0
        cache_cost = 0

        if self.model == "gemini-1.5-flash-001":
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
        elif self.model == "gemini-1.5-pro-001":
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

        total_cost = input_cost + output_cost + cache_cost
        logger.debug(f"Calculated cost: {total_cost}")
        return total_cost

    def create_context_cache(self, display_name: str, system_instruction: str, contents: List[Any], ttl: int = 5):
        logger.info(f"Creating context cache for model: {self.model}")
        logger.debug(f"Display name: {display_name}")
        logger.debug(f"System instruction: {system_instruction}")
        logger.debug(f"Contents: {contents[:50]}...")
        logger.debug(f"TTL: {ttl} minutes")

        if self.context_caching and self.model in ["gemini-1.5-pro-001", "gemini-1.5-flash-001"]:
            try:
                self.cached_content = caching.CachedContent.create(
                    model=self.model,
                    display_name=display_name,
                    system_instruction=system_instruction,
                    contents=contents,
                    ttl=datetime.timedelta(minutes=ttl)
                )
                logger.info(f"Context cache created successfully for model: {self.model}")
            except Exception as e:
                logger.error(f"Error creating context cache for model {self.model}: {str(e)}", exc_info=True)
                self.cached_content = None
        else:
            logger.info(f"Context caching not enabled or not supported for model: {self.model}")
            self.cached_content = None

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def generate_content(self, prompt: str, safety_settings: Optional[Dict] = None, generation_config: Optional[Dict] = None) -> Any:
        logger.info(f"Generating content with model: {self.model}")
        if self.context_caching and self.cached_content:
            logger.info("Using cached content for generation")
            model = genai.GenerativeModel.from_cached_content(cached_content=self.cached_content)
        else:
            logger.info("Creating new GenerativeModel instance")
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
                temperature=0.3,
                top_p=0.9,
            )

        logger.debug(f"Prompt: {prompt[:100]}...")  # Log the first 100 characters of the prompt
        logger.debug(f"Safety settings: {safety_settings}")
        logger.debug(f"Generation config: {generation_config}")

        try:
            response = model.generate_content(
                prompt,
                safety_settings=safety_settings,
                generation_config=generation_config
            )
            logger.info("Content generated successfully")
            logger.debug(f"Response: {response.text[:100]}...")  # Log the first 100 characters of the response
            return response
        except Exception as e:
            logger.error(f"Error generating content: {str(e)}", exc_info=True)
            raise

    def update_context_cache(self, translated_text: str):
        logger.info("Updating context cache")
        if self.context_caching:
            self.create_context_cache(
                display_name="Proofreading Context",
                system_instruction="You are an expert in proofreading Sino-Vietnamese translations. Use the provided context to improve your proofreading results.",
                contents=[translated_text],
                ttl=10  # Cache for 10 minutes
            )
        else:
            logger.info("Context caching is disabled, skipping update")

    def set_context_caching(self, enabled: bool):
        logger.info(f"Setting context caching to: {enabled}")
        self.context_caching = enabled
        if not enabled:
            self.cached_content = None
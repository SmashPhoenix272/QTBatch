from typing import List, Dict, Any, Optional, Callable
import os
import yaml
import logging
import re
from tenacity import retry, stop_after_attempt, wait_fixed
from proofread_cache import ProofreadCache
from providers.google_generativeai_sdk import GoogleGenerativeAIProvider
from providers.vertex_ai_sdk import VertexAIProvider
from config import (
    AI_PROOFREAD_API_KEY,
    AI_PROOFREAD_MODEL,
    AI_PROOFREAD_CONTEXT_CACHING,
    AI_PROOFREAD_BATCH_PREDICTIONS,
    AI_PROOFREAD_PROMPT_TEMPLATE,
    AI_PROOFREAD_PROVIDER,
)
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue

# Initialize logger at module level
logger = logging.getLogger('ai_proofread')
logger.setLevel(logging.DEBUG)
log_handler = logging.FileHandler('ai_proofread.log', encoding='utf-8')
log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(log_handler)

class AIProofreader:
    def __init__(self, main_gui, update_settings_callback: Callable):
        self.main_gui = main_gui
        self.update_settings_callback = update_settings_callback
        self.settings = {
            "api_key": AI_PROOFREAD_API_KEY,
            "model": AI_PROOFREAD_MODEL,
            "context_caching": AI_PROOFREAD_CONTEXT_CACHING,
            "batch_predictions": AI_PROOFREAD_BATCH_PREDICTIONS,
            "prompt_template": AI_PROOFREAD_PROMPT_TEMPLATE,
            "context_aware": False,
            "adaptive_learning": False,
            "provider": AI_PROOFREAD_PROVIDER,
            "max_workers": 4,  # Default number of parallel processing threads
        }
        self.cache = ProofreadCache()
        self.context = []
        self.learned_patterns = {}
        self.cumulative_input_tokens = 0
        self.cumulative_output_tokens = 0
        self.cumulative_total_tokens = 0
        self.cumulative_total_cost = 0
        self.proofreading_queue = queue.Queue()
        self.total_chunks = 0
        self.processed_chunks = 0

        # Log initialization
        logger.info("Initializing AIProofreader")

        # Create provider after logger is initialized
        self.provider = self.create_provider()

    def create_provider(self):
        logger.info(f"Creating provider: {self.settings['provider']}")
        if self.settings["provider"] == "Google GenerativeAI":
            return GoogleGenerativeAIProvider(self.settings["api_key"], self.settings["model"])
        elif self.settings["provider"] == "Vertex AI":
            return VertexAIProvider(self.settings["api_key"], "us-central1", self.settings["model"])
        else:
            raise ValueError(f"Unknown provider: {self.settings['provider']}")

    def update_settings(self, new_settings: Dict[str, Any]):
        logger.info(f"Updating settings: {new_settings}")
        self.settings.update(new_settings)
        self.provider = self.create_provider()
        self.save_settings_to_config()

    def save_settings_to_config(self):
        logger.info("Saving settings to config")
        config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
        with open(config_path, 'r', encoding='utf-8') as config_file:
            config = yaml.safe_load(config_file)
        
        config['ai_proofread'] = self.settings
        
        with open(config_path, 'w', encoding='utf-8') as config_file:
            yaml.dump(config, config_file, allow_unicode=True)

    def proofread_chunk(self, chinese_text: str, sino_vietnamese_text: str, names: List[str], filename: str) -> str:
        logger.info(f"Proofreading chunk for file: {filename}")
        
        # Check for empty inputs
        if not chinese_text or not sino_vietnamese_text:
            logger.warning("Empty input detected. Skipping proofreading.")
            return sino_vietnamese_text  # Return the original text (which might be empty)
        
        logger.debug(f"Chinese text: {chinese_text[:100]}...")
        logger.debug(f"Sino-Vietnamese text: {sino_vietnamese_text[:100]}...")
        logger.debug(f"Names: {names}")

        cache_key = self.cache.get_cache_key(chinese_text, sino_vietnamese_text, names)
        logger.debug(f"Cache key: {cache_key}")

        cached_result = self.cache.get_cached_result(filename, chinese_text, sino_vietnamese_text, names)
        if cached_result:
            logger.info(f"Using cached result for key: {cache_key}")
            return cached_result

        logger.info(f"No cached result found for key: {cache_key}. Proceeding with AI proofreading.")

        try:
            result = self._proofread_text(chinese_text, sino_vietnamese_text, names)
            if result:  # Check if the result is not empty
                logger.info(f"Caching result for key: {cache_key}")
                self.cache.cache_result(filename, chinese_text, sino_vietnamese_text, names, result)
            else:
                logger.warning("Empty proofread result. Using original Sino-Vietnamese text.")
                result = sino_vietnamese_text
            return result
        except Exception as e:
            logger.error(f"Error in proofread_chunk: {str(e)}", exc_info=True)
            logger.info("Starting recursive splitting for proofreading.")
            return self._proofread_split_chunk(chinese_text, sino_vietnamese_text, names, filename)

    def _proofread_split_chunk(self, chinese_text: str, sino_vietnamese_text: str, names: List[str], filename: str) -> str:
        result = self._proofread_recursive(chinese_text, sino_vietnamese_text, names, filename, 3)
        if result:  # Check if the result is not empty
            logger.info(f"Caching result for original chunk")
            self.cache.cache_result(filename, chinese_text, sino_vietnamese_text, names, result)
        else:
            logger.warning("Empty result from recursive proofreading. Using original Sino-Vietnamese text.")
            result = sino_vietnamese_text
        return result

    def _proofread_recursive(self, chinese_text: str, sino_vietnamese_text: str, names: List[str], filename: str, remaining_splits: int) -> str:
        if remaining_splits == 0:
            logger.info("Reached maximum split depth. Proofreading paragraphs individually.")
            return self._proofread_paragraphs(chinese_text, sino_vietnamese_text, names, filename)

        try:
            return self._proofread_text(chinese_text, sino_vietnamese_text, names)
        except Exception as e:
            logger.error(f"Error in recursive proofreading: {str(e)}", exc_info=True)
            logger.info(f"Splitting text in half. Remaining splits: {remaining_splits-1}")

            zh_parts = self._split_into_parts(chinese_text, 2)
            vi_parts = self._split_into_parts(sino_vietnamese_text, 2)

            proofread_parts = []
            for zh_part, vi_part in zip(zh_parts, vi_parts):
                proofread_part = self._proofread_recursive(zh_part, vi_part, names, filename, remaining_splits-1)
                proofread_parts.append(proofread_part)

            return '\n\n'.join(proofread_parts)

    def _split_into_parts(self, text: str, num_parts: int) -> List[str]:
        paragraphs = text.split('\n\n')
        total_paragraphs = len(paragraphs)
        paragraphs_per_part = max(1, total_paragraphs // num_parts)
        
        parts = []
        for i in range(0, total_paragraphs, paragraphs_per_part):
            part = paragraphs[i:i + paragraphs_per_part]
            parts.append('\n\n'.join(part))
        
        # If we have fewer parts than requested, duplicate the last part
        while len(parts) < num_parts:
            parts.append(parts[-1])
        
        # If we have more parts than requested, combine the last parts
        if len(parts) > num_parts:
            parts[num_parts-1:] = ['\n\n'.join(parts[num_parts-1:])]
        
        return parts

    def _split_text(self, text: str) -> List[str]:
        return [para.strip() for para in text.split('\n\n') if para.strip()]

    def _is_chinese(self, text: str) -> bool:
        # This function checks if the text contains Chinese characters
        return bool(re.search(r'[\u4e00-\u9fff]', text))

    def _get_context(self, chinese_text: str, sino_vietnamese_text: str) -> str:
        context = ""
        if self.context:
            context = (
                "Ngữ cảnh trước đó (Vui lòng xem xét khi dịch đoạn văn hiện tại trong cặp thẻ <ZH></ZH>):\n"
                f"Tiếng Trung: {self.context[-1]['chinese']}\n"
                f"Bản dịch Hán Việt: {self.context[-1]['sino_vietnamese']}\n"
                f"Bản dịch đã hiệu đính: {self.context[-1]['proofread']}\n\n"
            )
        return context

    def _proofread_text(self, chinese_text: str, sino_vietnamese_text: str, names: List[str]) -> str:
        if not chinese_text or not sino_vietnamese_text:
            logger.warning("Empty input in _proofread_text. Skipping proofreading.")
            return sino_vietnamese_text

        context = self._get_context(chinese_text, sino_vietnamese_text) if self.settings["context_aware"] else ""
        prompt = self.settings["prompt_template"] + f"\n\n{context}<ZH>{chinese_text}</ZH>\n<NA>{', '.join(names)}</NA>\n<VI>{sino_vietnamese_text}</VI>"
        logger.debug(f"Generated prompt: {prompt}...")
        
        max_attempts = 3
        attempt = 0
        while True:
            attempt += 1
            logger.info(f"Sending request to AI provider (Attempt {attempt})")
            try:
                response = self.provider.generate_content(prompt)
                
                # Log prompt feedback
                logger.info(f"Prompt feedback: {response.prompt_feedback}")
                
                # Check if the prompt was blocked
                if "block" in str(response.prompt_feedback).lower():
                    logger.error("Prompt blocked. Retrying with the same prompt.")
                    continue  # Try again with the same prompt
                
                # Extract the content from the response
                result = response.text
                logger.debug(f"Raw response from AI: {result[:200]}...")
                
                # Extract the translated text from the <TL></TL> tags or <TL> tag
                translated_text = None
                # First, try to find text between <TL> and </TL> tags
                match = re.search(r'<TL>(.*?)</TL>', result, re.DOTALL)
                if match:
                    translated_text = match.group(1)
                    logger.info("Successfully extracted translated text from <TL></TL> tags")
                else:
                    # If not found, try to find text after <TL> tag
                    match = re.search(r'<TL>(.*)', result, re.DOTALL)
                    if match:
                        translated_text = match.group(1)
                        logger.info("Successfully extracted translated text from <TL> tag")
                    else:
                        logger.warning(f"No <TL> tags found in the response. Full response: {result}")
                        if attempt < max_attempts:
                            logger.info(f"Retrying proofreading (Attempt {attempt + 1}/{max_attempts})")
                            continue
                        else:
                            logger.warning("Max attempts reached. Using Sino-Vietnamese text.")
                            return sino_vietnamese_text
                
                if translated_text:
                    result = translated_text.strip()
                    
                    # Check if the result is still in Chinese
                    if self._is_chinese(result):
                        if attempt < max_attempts:
                            logger.info(f"Result still in Chinese. Retrying proofreading (Attempt {attempt + 1}/{max_attempts})")
                            continue
                        else:
                            logger.warning("Max attempts reached. Using Sino-Vietnamese text.")
                            return sino_vietnamese_text
                else:
                    if attempt < max_attempts:
                        logger.warning("No translated text found. Retrying.")
                        continue
                    else:
                        logger.warning("Max attempts reached. Using Sino-Vietnamese text.")
                        return sino_vietnamese_text
                
                # Update token counts and cost
                usage = self.provider.get_usage_metadata(response)
                self.update_cumulative_stats(usage)
                logger.info(f"Token usage - Input: {usage['prompt_token_count']}, Output: {usage['candidates_token_count']}, Total: {usage['total_token_count']}")
                logger.info(f"Current cumulative total cost: {self.cumulative_total_cost}")

                if self.settings["adaptive_learning"]:
                    logger.info("Applying adaptive learning patterns")
                    for pattern, correction in self.learned_patterns.items():
                        result = result.replace(pattern, correction)
                
                # Update context if context_aware is enabled
                if self.settings["context_aware"]:
                    self.context.append({
                        "chinese": chinese_text,
                        "sino_vietnamese": sino_vietnamese_text,
                        "proofread": result
                    })
                    if len(self.context) > 3:  # Keep only the last 3 contexts
                        self.context.pop(0)
                
                return result
            
            except Exception as e:
                logger.error(f"Error during content generation: {str(e)}", exc_info=True)
                if attempt < max_attempts:
                    logger.info(f"Retrying due to error (Attempt {attempt + 1}/{max_attempts})")
                else:
                    logger.warning("Max attempts reached. Starting recursive splitting.")
                    return self._proofread_split_chunk(chinese_text, sino_vietnamese_text, names, "")

    def _proofread_paragraphs(self, chinese_text: str, sino_vietnamese_text: str, names: List[str], filename: str) -> str:
        chinese_paragraphs = self._split_text(chinese_text)
        sino_vietnamese_paragraphs = self._split_text(sino_vietnamese_text)
        
        if len(chinese_paragraphs) != len(sino_vietnamese_paragraphs):
            logger.error("Mismatch in number of paragraphs between Chinese and Sino-Vietnamese text")
            return sino_vietnamese_text
        
        proofread_paragraphs = []
        for zh_para, vi_para in zip(chinese_paragraphs, sino_vietnamese_paragraphs):
            if not zh_para or not vi_para:
                logger.warning("Empty paragraph detected. Skipping proofreading for this paragraph.")
                proofread_paragraphs.append(vi_para)
                continue
            try:
                proofread_para = self._proofread_text(zh_para, vi_para, names)
                proofread_paragraphs.append(proofread_para)
            except Exception as e:
                logger.error(f"Error proofreading paragraph: {str(e)}")
                proofread_paragraphs.append(vi_para)  # Use original text if proofreading fails
        
        return '\n\n'.join(proofread_paragraphs)

    def proofread_batch(self, chunks: List[Dict[str, Any]], names: List[str], filename: str) -> List[str]:
        logger.info(f"Proofreading batch for file: {filename}")
        logger.debug(f"Number of chunks: {len(chunks)}")
        self.total_chunks = len(chunks)
        self.processed_chunks = 0
        results = [None] * len(chunks)  # Pre-allocate list to maintain order
        with ThreadPoolExecutor(max_workers=self.settings["max_workers"]) as executor:
            future_to_index = {executor.submit(self.proofread_chunk, chunk["chinese"], chunk["sino_vietnamese"], names, filename): i for i, chunk in enumerate(chunks)}
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    result = future.result()
                    results[index] = result
                    self.processed_chunks += 1
                    self.update_cache_percentage(filename)
                except Exception as e:
                    logger.error(f"Error proofreading chunk {index}: {str(e)}", exc_info=True)
                    results[index] = chunks[index]["sino_vietnamese"]  # Use original text if proofreading fails
                    self.processed_chunks += 1
                    self.update_cache_percentage(filename)
        logger.info(f"Batch proofreading completed. Processed {len(results)} chunks.")
        return results

    def add_to_proofreading_queue(self, chunk: Dict[str, Any]):
        logger.debug("Adding chunk to proofreading queue")
        self.proofreading_queue.put(chunk)

    def process_proofreading_queue(self, names: List[str], filename: str) -> List[str]:
        logger.info(f"Processing proofreading queue for file: {filename}")
        chunks = []
        while not self.proofreading_queue.empty():
            chunks.append(self.proofreading_queue.get())
        logger.debug(f"Queue size: {len(chunks)}")
        return self.proofread_batch(chunks, names, filename)

    def update_learned_patterns(self, chinese_text: str, sino_vietnamese_text: str, proofread_result: str):
        logger.info("Updating learned patterns")
        if not chinese_text or not sino_vietnamese_text or not proofread_result:
            logger.warning("Empty input in update_learned_patterns. Skipping pattern update.")
            return
        words = chinese_text.split()
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            if bigram in sino_vietnamese_text and bigram not in proofread_result:
                correction = proofread_result.split()[i:i+2]
                self.learned_patterns[bigram] = " ".join(correction)
                logger.debug(f"New learned pattern: '{bigram}' -> '{' '.join(correction)}'")

    def clear_cache(self, filename: str):
        logger.info(f"Clearing cache for file: {filename}")
        self.cache.clear_cache(filename)
        self.context = []
        self.learned_patterns = {}
        self.total_chunks = 0
        self.processed_chunks = 0
        self.update_cache_percentage(filename)

    def get_stats(self) -> Dict[str, Any]:
        stats = {
            "total_tokens": self.cumulative_total_tokens,
            "prompt_tokens": self.cumulative_input_tokens,
            "candidates_tokens": self.cumulative_output_tokens,
            "total_cost": self.cumulative_total_cost,
        }
        logger.info(f"Current cumulative stats: {stats}")
        return stats

    def get_cache_percentage(self, filename: str) -> float:
        if self.total_chunks == 0:
            return 0.0
        percentage = (self.processed_chunks / self.total_chunks) * 100
        logger.debug(f"Cache percentage for {filename}: {percentage}%")
        return percentage

    def update_cache_percentage(self, filename: str):
        cache_percentage = self.get_cache_percentage(filename)
        logger.info(f"Updating cache percentage for {filename}: {cache_percentage}%")
        self.main_gui.update_ai_proofread_cache_percentage(cache_percentage)

    def update_cumulative_stats(self, usage: Dict[str, int]):
        self.cumulative_input_tokens += usage["prompt_token_count"]
        self.cumulative_output_tokens += usage["candidates_token_count"]
        self.cumulative_total_tokens += usage["total_token_count"]
        self.cumulative_total_cost += self.provider.calculate_cost(usage["prompt_token_count"], usage["candidates_token_count"])

def load_names_from_file(file_path: str) -> List[str]:
    logger.info(f"Loading names from file: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        names = [line.strip() for line in f if '=' in line]
    logger.debug(f"Loaded {len(names)} names")
    return names
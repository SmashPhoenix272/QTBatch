import yaml
import os

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_path, 'r', encoding='utf-8') as config_file:
        config = yaml.safe_load(config_file)
    return config

CONFIG = load_config()

# Font configuration
FONT_DIR = "fonts"
CHINESE_FONT_FILENAME = CONFIG['fonts'][1]['filename']
VIETNAMESE_FONT_FILENAME = CONFIG['fonts'][0]['filename']
CHINESE_FONT_PATH = os.path.join(FONT_DIR, CHINESE_FONT_FILENAME)
VIETNAMESE_FONT_PATH = os.path.join(FONT_DIR, VIETNAMESE_FONT_FILENAME)
CHINESE_FONT_URL = CONFIG['fonts'][1]['url']
VIETNAMESE_FONT_URL = CONFIG['fonts'][0]['url']

# GUI configuration
WINDOW_WIDTH = CONFIG['gui']['window_width']
WINDOW_HEIGHT = CONFIG['gui']['window_height']
FONT_SIZE = 20  # This value is not in the YAML, so we're keeping it hardcoded for now

# HanLP configuration
HANLP_MODEL = CONFIG['hanlp']['model']
HANLP_LANGUAGE = CONFIG['hanlp']['language']

# Processing configuration
CHUNK_SIZE = CONFIG['processing']['chunk_size']

# File paths (these were not in the YAML, so we're keeping them as they were)
NAMES2_PATH = "Names2.txt"
NAMES_PATH = "Names.txt"
CHINESE_PHIEN_AM_PATH = "ChinesePhienAmWords.txt"
VIET_PHRASE_PATH = "VietPhrase.txt"

# AI Proofread configuration
AI_PROOFREAD_CONFIG = CONFIG.get('ai_proofread', {})
AI_PROOFREAD_API_KEY = AI_PROOFREAD_CONFIG.get('api_key', '')
AI_PROOFREAD_MODEL = AI_PROOFREAD_CONFIG.get('model', 'gemini-1.5-flash')
AI_PROOFREAD_CONTEXT_CACHING = AI_PROOFREAD_CONFIG.get('context_caching', True)
AI_PROOFREAD_BATCH_PREDICTIONS = AI_PROOFREAD_CONFIG.get('batch_predictions', True)
AI_PROOFREAD_PROMPT_TEMPLATE = AI_PROOFREAD_CONFIG.get('prompt_template', 'Your default prompt template here')
AI_PROOFREAD_PROVIDER = AI_PROOFREAD_CONFIG.get('provider', 'Google GenerativeAI')
AI_PROOFREAD_CONTEXT_AWARE = AI_PROOFREAD_CONFIG.get('context_aware', True)
AI_PROOFREAD_ADAPTIVE_LEARNING = AI_PROOFREAD_CONFIG.get('adaptive_learning', True)
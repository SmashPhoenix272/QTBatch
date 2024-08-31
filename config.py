import yaml
import os

def create_default_config():
    return {
        'ai_proofread': {
            'adaptive_learning': False,
            'api_key': '',
            'batch_predictions': False,
            'context_aware': False,
            'context_caching': False,
            'max_workers': 4,
            'model': 'gemini-1.5-flash',
            'prompt_template': '''Vai trò: Bạn là một dịch giả chuyên nghiệp, xuất sắc trong việc dịch từ tiếng Trung sang tiếng Việt.

Kỹ năng 1: Phiên dịch từ tiếng Trung sang tiếng Việt
Khi nhận được văn bản trong cặp thẻ <ZH></ZH>, bạn cần dịch sang tiếng Việt một cách chính xác và trôi chảy nhưng nhất thiết phải tham khảo tên riêng và ngữ nghĩa theo bản dịch thô tiếng Việt trong cặp thẻ <VI></VI> để đảm bảo tính chính xác và phù hợp.
Đối với tên riêng hãy ưu tiên tham khảo tên trong cặp thẻ <NA></NA>, và dịch theo kiểu Hán Việt.
Với tên người tiếng Trung, hãy dịch theo kiểu Hán Việt. Đối với tên người Nhật, sử dụng cách phiên âm Romaji.
Đảm bảo không bỏ sót câu nào và giữ nguyên định dạng cũng như số dòng so với bản gốc.
Giữ lại các đại từ nhân xưng ví dụ như: ta, ngươi, chúng ta, các ngươi, hắn, nàng, v.v..
Tốt nhất là không thay đổi đại từ nhân xưng.
Bạn chỉ có thể trả lời bằng tiếng Việt và tuyệt đối không được phép sử dụng tiếng Trung trong câu trả lời.

Kỹ năng 2: Biên tập lại nội dung phiên dịch
Sau khi dịch, bạn cần biên tập lại nội dung để đảm bảo văn phong mượt mà, sinh động và giàu cảm xúc.
Tránh sự khô khan, máy móc, đồng thời trung thành với nội dung gốc.
Đặc biệt chú ý đến các đoạn đối thoại giữa các nhân vật, làm cho chúng trở nên tự nhiên và cảm xúc hơn.
Tránh lặp từ, sửa lỗi ngữ pháp và làm rõ nghĩa nội dung.
Đảm bảo rằng bản dịch cuối cùng là tiếng Việt và đặt trong cặp thẻ <TL></TL>.

Kết quả:
Đặt kết quả dịch trong cặp thẻ <TL></TL>. Đảm bảo rằng bản dịch đã được biên tập, không bỏ sót câu nào và giữ nguyên định dạng cũng như số dòng so với bản gốc.''',
            'provider': 'Google GenerativeAI'
        },
        'fonts': [
            {
                'filename': 'Montserrat-Medium.ttf',
                'name': 'Montserrat-Medium',
                'url': 'https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat-Medium.ttf'
            },
            {
                'filename': 'NotoSansSC-Medium.ttf',
                'name': 'NotoSansSC-Medium',
                'url': 'https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Chinese-Simplified/NotoSansCJKsc-Medium.otf'
            }
        ],
        'gui': {
            'theme': 'Dark',
            'window_height': 800,
            'window_width': 1204
        },
        'hanlp': {
            'language': 'zh',
            'model': 'large'
        },
        'processing': {
            'chunk_size': 1000
        }
    }

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    if not os.path.exists(config_path):
        default_config = create_default_config()
        with open(config_path, 'w', encoding='utf-8') as config_file:
            yaml.dump(default_config, config_file, default_flow_style=False)
        print(f"Created default config file at {config_path}")
        return default_config
    
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
GUI_THEME = CONFIG['gui']['theme']
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
AI_PROOFREAD_MAX_WORKERS = AI_PROOFREAD_CONFIG.get('max_workers', 4)
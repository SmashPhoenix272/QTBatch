import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from ReplaceChar import SPECIAL_CHARS
import time
import os
import cProfile
from concurrent.futures import ThreadPoolExecutor, as_completed

LATIN_CHARS = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')

class TrieNode:
    __slots__ = ['children', 'is_end_of_word', 'value']
    def __init__(self):
        self.children: Dict[str, 'TrieNode'] = {}
        self.is_end_of_word: bool = False
        self.value: Optional[str] = None

class Trie:
    def __init__(self):
        self.root: TrieNode = TrieNode()
        self.word_count: int = 0

    def insert(self, word: str, value: str) -> None:
        current = self.root
        for char in word:
            if char not in current.children:
                current.children[char] = TrieNode()
            current = current.children[char]
        current.is_end_of_word = True
        current.value = value
        self.word_count += 1

    def batch_insert(self, words: List[Tuple[str, str]]) -> None:
        for word, value in words:
            self.insert(word, value)

    def count(self) -> int:
        return self.word_count

    def find_longest_prefix(self, text: str) -> Tuple[str, Optional[str]]:
        current = self.root
        longest_prefix = ""
        longest_value = None
        prefix = []
        for i, char in enumerate(text):
            if char not in current.children:
                break
            current = current.children[char]
            prefix.append(char)
            if current.is_end_of_word:
                longest_prefix = ''.join(prefix)
                longest_value = current.value
        return longest_prefix, longest_value

def profile_function(func):
    def wrapper(*args, **kwargs):
        pr = cProfile.Profile()
        pr.enable()
        result = func(*args, **kwargs)
        pr.disable()
        
        stats = pr.getstats()
        total_calls = sum(stat.callcount for stat in stats)
        total_time = sum(stat.totaltime for stat in stats)
        
        logging.info(f"Performance profile for {func.__name__}:")
        logging.info(f"Total function calls: {total_calls}")
        logging.info(f"Total time: {total_time:.6f} seconds")
        
        return result
    return wrapper

@profile_function
def load_data() -> Tuple[Trie, Trie, Trie, Dict[str, str], Dict[str, Dict[str, Any]]]:
    names2 = Trie()
    names = Trie()
    viet_phrase = Trie()
    chinese_phien_am: Dict[str, str] = {}
    
    loading_info: Dict[str, Dict[str, Any]] = {
        "names2": {"loaded": False, "count": 0, "time": 0},
        "names": {"loaded": False, "count": 0, "time": 0},
        "chinese_words": {"loaded": False, "count": 0, "time": 0},
        "viet_phrase": {"loaded": False, "count": 0, "time": 0}
    }

    def load_file(file_name: str, trie: Trie, info_key: str, split_values: bool = False):
        try:
            start_time = time.time()
            with open(file_name, 'r', encoding='utf-8') as f:
                entries = []
                for line in f:
                    parts = line.strip().split('=')
                    if len(parts) == 2:
                        key, value = parts
                        if split_values:
                            first_value = value.replace("|", "/").split("/")[0]
                            entries.append((key, first_value))
                        else:
                            entries.append((key, value))
            trie.batch_insert(entries)
            loading_info[info_key]["loaded"] = True
            loading_info[info_key]["count"] = trie.count()
            loading_info[info_key]["time"] = time.time() - start_time
            logging.info(f"Loaded {trie.count()} entries from {file_name} in {loading_info[info_key]['time']:.2f} seconds")
        except FileNotFoundError:
            logging.error(f"{file_name} not found. Proceeding without {info_key} data.")
        except Exception as e:
            logging.error(f"Error loading {file_name}: {str(e)}")

    # Load Names2.txt
    load_file('Names2.txt', names2, "names2")

    # Load Names.txt with split_values=True
    load_file('Names.txt', names, "names", split_values=True)

    # Load ChinesePhienAmWords.txt
    try:
        start_time = time.time()
        with open('ChinesePhienAmWords.txt', 'r', encoding='utf-8') as f:
            chinese_phien_am = dict(line.strip().split('=') for line in f if len(line.strip().split('=')) == 2)
        loading_info["chinese_words"]["loaded"] = True
        loading_info["chinese_words"]["count"] = len(chinese_phien_am)
        loading_info["chinese_words"]["time"] = time.time() - start_time
        logging.info(f"Loaded {len(chinese_phien_am)} Chinese words in {loading_info['chinese_words']['time']:.2f} seconds")
    except FileNotFoundError:
        logging.error("ChinesePhienAmWords.txt not found.")
    except Exception as e:
        logging.error(f"Error loading ChinesePhienAmWords.txt: {str(e)}")

    # Load VietPhrase.txt with split_values=True
    load_file('VietPhrase.txt', viet_phrase, "viet_phrase", split_values=True)

    return names2, names, viet_phrase, chinese_phien_am, loading_info

def read_novel_file(file_path: str) -> Tuple[str, str]:
    encodings_to_try = ['utf-8', 'gbk', 'gb2312', 'big5']
    for encoding in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                novel_text = file.read()
            logging.info(f"Successfully read the novel file using {encoding} encoding.")
            return novel_text, encoding
        except UnicodeDecodeError:
            logging.warning(f"Failed to read with {encoding} encoding.")
    raise ValueError("Unable to read the novel file with any of the attempted encodings.")

def replace_special_chars(text: str) -> str:
    for han, viet in SPECIAL_CHARS.items():
        text = text.replace(han, viet)
    return text

@profile_function
def convert_to_sino_vietnamese(text: str, names2: Trie, names: Trie, viet_phrase: Trie, chinese_phien_am: Dict[str, str]) -> str:
    text = replace_special_chars(text)
    
    tokens = []
    i = 0
    chunk_size = 1000  # Process text in chunks of 1000 characters internally
    
    while i < len(text):
        chunk = text[i:i+chunk_size]
        j = 0
        
        while j < len(chunk):
            # Check for a sequence of Latin characters
            latin_start = j
            while j < len(chunk) and chunk[j] in LATIN_CHARS:
                j += 1
            if j > latin_start:
                latin_text = chunk[latin_start:j]
                tokens.append(latin_text)
                continue
            
            # Check Names2 first
            name2_match, value = names2.find_longest_prefix(chunk[j:])
            if name2_match:
                tokens.append(value)
                j += len(name2_match)
                continue
            
            # Then check Names
            name_match, value = names.find_longest_prefix(chunk[j:])
            if name_match:
                tokens.append(value)
                j += len(name_match)
                continue
            
            # Try to find the longest prefix in VietPhrase
            max_prefix, value = viet_phrase.find_longest_prefix(chunk[j:])
            if max_prefix:
                if value != "":
                    tokens.append(value)
                j += len(max_prefix)
            else:
                # If no match found, fallback to ChinesePhienAmWord
                char = chunk[j]
                fallback_value = chinese_phien_am.get(char, char)
                tokens.append(fallback_value)
                j += 1
        
        i += chunk_size
    
    result = rephrase(tokens)
    return result

def rephrase(tokens):
    non_word = set('"[{ ,!?;\'.')
    result = []
    upper = False
    last_token_empty = False

    for i, token in enumerate(tokens):
        if token.strip():  # Non-empty token
            if i == 0 or (not upper and token not in non_word):
                if result and not last_token_empty:
                    result.append(' ')
                if not token[0].isupper():  # Only capitalize if not already capitalized
                    token = token.capitalize()
                upper = True
            elif token not in non_word and not last_token_empty:
                result.append(' ')
            result.append(token)
            last_token_empty = False
        else:  # Empty token
            if not last_token_empty and i > 0:
                result.append(' ')
            result.append(token)
            last_token_empty = True

    text = ''.join(result).strip()
    # Remove spaces after left quotation marks and capitalize first word
    text = re.sub(r'([\[\“\‘])\s*(\w)', lambda m: m.group(1) + m.group(2).upper(), text)
    # Remove spaces before right quotation marks
    text = re.sub(r'\s+([”\’\]])', r'\1', text)
    # Capitalize first word after ? and ! marks
    text = re.sub(r'([?!⟨:«])\s+(\w)', lambda m: m.group(1) + ' ' + m.group(2).upper(), text)
    # Remove spaces before colon and semicolon
    text = re.sub(r'\s+([;:?!.])', r'\1', text)
    # Capitalize first word after a single dot, but not after triple dots
    text = re.sub(r'(?<!\.)\.(?!\.)\s+(\w)', lambda m: '. ' + m.group(1).upper(), text)
    return text

@profile_function
def process_paragraph(paragraph: str, names2: Trie, names: Trie, viet_phrase: Trie, chinese_phien_am: Dict[str, str]) -> str:
    converted = convert_to_sino_vietnamese(paragraph, names2, names, viet_phrase, chinese_phien_am)
    return converted

def convert_filename(filename: str, names2: Trie, names: Trie, viet_phrase: Trie, chinese_phien_am: Dict[str, str]) -> str:
    base_name = os.path.basename(filename)
    name_without_ext, ext = os.path.splitext(base_name)
    converted_name = convert_to_sino_vietnamese(name_without_ext, names2, names, viet_phrase, chinese_phien_am)
    
    # Remove any characters that are not allowed in filenames
    converted_name = ''.join(char for char in converted_name if char not in r'<>:"/\|?*')
    
    return f"{converted_name}_Converted{ext}"

# Cache for storing frequently converted phrases
conversion_cache = {}

def cached_convert_to_sino_vietnamese(text: str, names2: Trie, names: Trie, viet_phrase: Trie, chinese_phien_am: Dict[str, str]) -> str:
    if text in conversion_cache:
        return conversion_cache[text]
    
    result = convert_to_sino_vietnamese(text, names2, names, viet_phrase, chinese_phien_am)
    conversion_cache[text] = result
    return result

@profile_function
def process_novel(novel_text: str, names2: Trie, names: Trie, viet_phrase: Trie, chinese_phien_am: Dict[str, str], progress_callback=None) -> str:
    paragraphs = novel_text.split('\n')
    converted_paragraphs = []
    total_paragraphs = len(paragraphs)

    for i, paragraph in enumerate(paragraphs):
        converted = cached_convert_to_sino_vietnamese(paragraph, names2, names, viet_phrase, chinese_phien_am)
        converted_paragraphs.append(converted)
        
        if progress_callback:
            progress = (i + 1) / total_paragraphs
            if progress_callback(progress):
                break  # Stop processing if the callback returns True

    return '\n'.join(converted_paragraphs)

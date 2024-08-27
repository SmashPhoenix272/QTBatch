import re
import logging
from typing import Dict, List, Tuple, Optional, Any, Callable
from ReplaceChar import SPECIAL_CHARS
import time
import os
import cProfile
from utils import detect_chapters
from concurrent.futures import ThreadPoolExecutor, as_completed
from models.trie import Trie

LATIN_CHARS = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')

def profile_function(func: Callable) -> Callable:
    """
    Decorator to profile a function's performance.

    Args:
        func (Callable): The function to be profiled.

    Returns:
        Callable: The wrapped function with profiling.
    """
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
    """
    Load data from various files into Trie structures and dictionaries.

    Returns:
        Tuple[Trie, Trie, Trie, Dict[str, str], Dict[str, Dict[str, Any]]]: 
        A tuple containing the loaded data structures:
        - names2: Trie containing Names2.txt data
        - names: Trie containing Names.txt data
        - viet_phrase: Trie containing VietPhrase.txt data
        - chinese_phien_am: Dictionary containing ChinesePhienAmWords.txt data
        - loading_info: Dictionary containing information about the loading process
    """
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

    def load_file(file_name: str, trie: Trie, info_key: str, is_vietphrase: bool = False):
        try:
            start_time = time.time()
            with open(file_name, 'r', encoding='utf-8') as f:
                if is_vietphrase:
                    entries = []
                    for line in f:
                        parts = line.strip().split('=')
                        if len(parts) == 2:
                            key, value = parts
                            first_value = value.split('/')[0]
                            entries.append((key, first_value))
                else:
                    entries = [tuple(line.strip().split('=')) for line in f if len(line.strip().split('=')) == 2]
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

    # Load Names.txt
    load_file('Names.txt', names, "names")

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

    # Load VietPhrase.txt
    load_file('VietPhrase.txt', viet_phrase, "viet_phrase", is_vietphrase=True)

    return names2, names, viet_phrase, chinese_phien_am, loading_info

def read_novel_file(file_path: str) -> Tuple[str, str]:
    """
    Read a novel file with various encoding attempts.

    Args:
        file_path (str): The path to the novel file.

    Returns:
        Tuple[str, str]: A tuple containing the novel text and the successful encoding.

    Raises:
        FileNotFoundError: If the file is not found.
        ValueError: If the file cannot be read with any of the attempted encodings or if the file is empty.
    """
    if not isinstance(file_path, str):
        raise TypeError("file_path must be a string")

    if not file_path.strip():
        raise ValueError("file_path cannot be empty")

    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")

    if not os.path.isfile(file_path):
        logging.error(f"Path is not a file: {file_path}")
        raise ValueError(f"Path is not a file: {file_path}")

    encodings_to_try = ['utf-8', 'gbk', 'gb2312', 'big5']
    for encoding in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                novel_text = file.read()
            if not novel_text.strip():
                logging.error(f"File is empty: {file_path}")
                raise ValueError(f"File is empty: {file_path}")
            logging.info(f"Successfully read the novel file using {encoding} encoding.")
            return novel_text, encoding
        except UnicodeDecodeError:
            logging.warning(f"Failed to read with {encoding} encoding.")
        except Exception as e:
            logging.error(f"Error reading file with {encoding} encoding: {str(e)}")
    
    logging.error(f"Unable to read the novel file with any of the attempted encodings: {encodings_to_try}")
    raise ValueError(f"Unable to read the novel file with any of the attempted encodings: {encodings_to_try}")

def replace_special_chars(text: str) -> str:
    """
    Replace special characters in the text with their Vietnamese equivalents.

    Args:
        text (str): The input text containing special characters.

    Returns:
        str: The text with special characters replaced.
    """
    for han, viet in SPECIAL_CHARS.items():
        text = text.replace(han, viet)
    return text

@profile_function
def convert_to_sino_vietnamese(text: str, names2: Trie, names: Trie, viet_phrase: Trie, chinese_phien_am: Dict[str, str]) -> str:
    """
    Convert Chinese text to Sino-Vietnamese.

    Args:
        text (str): The input Chinese text.
        names2 (Trie): Trie containing Names2.txt data.
        names (Trie): Trie containing Names.txt data.
        viet_phrase (Trie): Trie containing VietPhrase.txt data.
        chinese_phien_am (Dict[str, str]): Dictionary containing ChinesePhienAmWords.txt data.

    Returns:
        str: The converted Sino-Vietnamese text.
    """
    text = replace_special_chars(text)
    
    tokens = []
    i = 0
    chunk_size = 1000  # Process text in chunks of 5000 characters internally
    
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

def rephrase(tokens: List[str]) -> str:
    """
    Rephrase the tokens to form a properly formatted sentence.

    Args:
        tokens (List[str]): A list of tokens to be rephrased.

    Returns:
        str: The rephrased text.
    """
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
    """
    Process a single paragraph by converting it to Sino-Vietnamese.

    Args:
        paragraph (str): The input paragraph in Chinese.
        names2 (Trie): Trie containing Names2.txt data.
        names (Trie): Trie containing Names.txt data.
        viet_phrase (Trie): Trie containing VietPhrase.txt data.
        chinese_phien_am (Dict[str, str]): Dictionary containing ChinesePhienAmWords.txt data.

    Returns:
        str: The processed paragraph in Sino-Vietnamese.
    """
    converted = convert_to_sino_vietnamese(paragraph, names2, names, viet_phrase, chinese_phien_am)
    return converted

def convert_filename(filename: str, names2: Trie, names: Trie, viet_phrase: Trie, chinese_phien_am: Dict[str, str]) -> str:
    """
    Convert a Chinese filename to Sino-Vietnamese.

    Args:
        filename (str): The input filename in Chinese.
        names2 (Trie): Trie containing Names2.txt data.
        names (Trie): Trie containing Names.txt data.
        viet_phrase (Trie): Trie containing VietPhrase.txt data.
        chinese_phien_am (Dict[str, str]): Dictionary containing ChinesePhienAmWords.txt data.

    Returns:
        str: The converted filename in Sino-Vietnamese.
    """
    base_name = os.path.basename(filename)
    name_without_ext, ext = os.path.splitext(base_name)
    converted_name = convert_to_sino_vietnamese(name_without_ext, names2, names, viet_phrase, chinese_phien_am)
    
    # Remove any characters that are not allowed in filenames
    converted_name = ''.join(char for char in converted_name if char not in r'<>:"/\|?*')
    
    return f"{converted_name}{ext}"

@profile_function
def process_novel(novel_text: str, names2: Trie, names: Trie, viet_phrase: Trie, chinese_phien_am: Dict[str, str], 
                  progress_callback: Optional[Callable[[float], bool]] = None,
                  detect_chapters_enabled: bool = False,
                  start_chapter: Optional[int] = None,
                  end_chapter: Optional[int] = None,
                  update_cache_percentage_callback: Optional[Callable[[], None]] = None) -> str:
    """
    Process an entire novel by converting it to Sino-Vietnamese.

    Args:
        novel_text (str): The input novel text in Chinese.
        names2 (Trie): Trie containing Names2.txt data.
        names (Trie): Trie containing Names.txt data.
        viet_phrase (Trie): Trie containing VietPhrase.txt data.
        chinese_phien_am (Dict[str, str]): Dictionary containing ChinesePhienAmWords.txt data.
        progress_callback (Optional[Callable[[float], bool]]): A callback function to report progress.
        detect_chapters_enabled (bool): Whether to detect and process chapters (not used in this version).
        start_chapter (Optional[int]): The starting chapter number for conversion (not used in this version).
        end_chapter (Optional[int]): The ending chapter number for conversion (not used in this version).
        update_cache_percentage_callback (Optional[Callable[[], None]]): A callback function to update the cache percentage.

    Returns:
        str: The processed novel in Sino-Vietnamese.
    """
    paragraphs = novel_text.split('\n')
    converted_paragraphs = []
    total_paragraphs = len(paragraphs)

    for i, paragraph in enumerate(paragraphs):
        converted = convert_to_sino_vietnamese(paragraph, names2, names, viet_phrase, chinese_phien_am)
        converted_paragraphs.append(converted)
        
        if progress_callback:
            progress = (i + 1) / total_paragraphs
            if progress_callback(progress):
                break  # Stop processing if the callback returns True
        
        if update_cache_percentage_callback:
            update_cache_percentage_callback()

    converted_text = '\n'.join(converted_paragraphs)
    return converted_text


def process_chunk(chunk: str, names2: Trie, names: Trie, viet_phrase: Trie, chinese_phien_am: Dict[str, str],
                  progress_callback: Optional[Callable[[float], bool]] = None,
                  update_cache_percentage_callback: Optional[Callable[[], None]] = None) -> str:
    """
    Process a chunk of text by converting it to Sino-Vietnamese.

    Args:
        chunk (str): The input chunk of text in Chinese.
        names2 (Trie): Trie containing Names2.txt data.
        names (Trie): Trie containing Names.txt data.
        viet_phrase (Trie): Trie containing VietPhrase.txt data.
        chinese_phien_am (Dict[str, str]): Dictionary containing ChinesePhienAmWords.txt data.
        progress_callback (Optional[Callable[[float], bool]]): A callback function to report progress.
        update_cache_percentage_callback (Optional[Callable[[], None]]): A callback function to update the cache percentage.

    Returns:
        str: The processed chunk in Sino-Vietnamese.
    """
    return process_novel(chunk, names2, names, viet_phrase, chinese_phien_am, progress_callback, False, None, None, update_cache_percentage_callback)

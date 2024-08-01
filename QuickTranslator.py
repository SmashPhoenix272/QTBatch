import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from ReplaceChar import SPECIAL_CHARS
from typing import List
import time
import os
import cProfile
import pstats
import io

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
        """
        Insert a word and its associated value into the Trie.

        :param word: The word to insert
        :param value: The value associated with the word
        """
        current = self.root
        for char in word:
            if char not in current.children:
                current.children[char] = TrieNode()
            current = current.children[char]
        current.is_end_of_word = True
        current.value = value
        self.word_count += 1

    def batch_insert(self, words: List[Tuple[str, str]]) -> None:
        """
        Insert multiple words and their associated values into the Trie.

        :param words: A list of tuples, each containing a word and its associated value
        """
        for word, value in words:
            self.insert(word, value)

    def count(self) -> int:
        """
        Return the number of words in the Trie.

        :return: The number of words
        """
        return self.word_count

    def find_longest_prefix(self, text: str) -> Tuple[str, Optional[str]]:
        """
        Find the longest prefix of the given text that exists in the Trie.

        :param text: The text to search for a prefix
        :return: A tuple containing the longest prefix and its associated value (if any)
        """
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
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
        ps.print_stats()
        logging.info(f"Performance profile for {func.__name__}:\n{s.getvalue()}")
        return result
    return wrapper

@profile_function
def load_data() -> Tuple[Trie, Trie, Trie, Dict[str, str], Dict[str, Dict[str, Any]]]:
    """
    Load data from various files and return Trie structures and dictionaries.

    :return: A tuple containing Trie structures for names2, names, viet_phrase,
             a dictionary for chinese_phien_am, and a dictionary with loading information
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
            logging.warning(f"{file_name} not found. Proceeding without {info_key} data.")

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
        logging.warning("ChinesePhienAmWords.txt not found.")

    # Load VietPhrase.txt
    load_file('VietPhrase.txt', viet_phrase, "viet_phrase", is_vietphrase=True)

    return names2, names, viet_phrase, chinese_phien_am, loading_info

def read_novel_file(file_path: str) -> Tuple[str, str]:
    """
    Read a novel file using various encodings.

    :param file_path: Path to the novel file
    :return: A tuple containing the novel text and the encoding used
    :raises ValueError: If unable to read the file with any of the attempted encodings
    """
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
    """
    Replace special characters in the text with their Vietnamese equivalents.

    :param text: The input text
    :return: The text with special characters replaced
    """
    original = text
    for han, viet in SPECIAL_CHARS.items():
        text = text.replace(han, viet)

    if original != text:
        logging.debug(f"Special characters replaced: '{original}' -> '{text}'")
    return text

@profile_function
def convert_to_sino_vietnamese(text: str, names2: Trie, names: Trie, viet_phrase: Trie, chinese_phien_am: Dict[str, str]) -> str:
    """
    Convert Chinese text to Sino-Vietnamese.

    :param text: The input Chinese text
    :param names2: Trie containing Names2 data
    :param names: Trie containing Names data
    :param viet_phrase: Trie containing VietPhrase data
    :param chinese_phien_am: Dictionary containing Chinese Phien Am data
    :return: The converted Sino-Vietnamese text
    """
    text = replace_special_chars(text)
    tokens = []
    i = 0
    while i < len(text):
        # Check Names2 first
        name2_match, value = names2.find_longest_prefix(text[i:])
        if name2_match:
            tokens.append(value)
            i += len(name2_match)
            continue

        # Then check Names
        name_match, value = names.find_longest_prefix(text[i:])
        if name_match:
            tokens.append(value)
            i += len(name_match)
            continue

        # Try to find the longest prefix in VietPhrase
        max_prefix, value = viet_phrase.find_longest_prefix(text[i:])
        if max_prefix:
            if value != "":
                tokens.append(value)
            i += len(max_prefix)
        else:
            # If no match found, fallback to ChinesePhienAmWord
            char = text[i]
            fallback_value = chinese_phien_am.get(char, char)
            tokens.append(fallback_value)
            i += 1

    # Apply the rephrase function to the tokens
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
    text = re.sub(r'([\[\"\'])\s*(\w)', lambda m: m.group(1) + m.group(2).upper(), text)
    # Remove spaces before right quotation marks
    text = re.sub(r'\s+(["\'\]])', r'\1', text)
    # Capitalize first word after ? and ! marks
    text = re.sub(r'([?!⟨:])\s+(\w)', lambda m: m.group(1) + ' ' + m.group(2).upper(), text)
    # Remove spaces before colon and semicolon
    text = re.sub(r'\s+([;:?!.])', r'\1', text)
    # Capitalize first word after a single dot, but not after triple dots
    text = re.sub(r'(?<!\.)\.(?!\.)\s+(\w)', lambda m: '. ' + m.group(1).upper(), text)
    return text

@profile_function
def process_paragraph(paragraph: str, names2: Trie, names: Trie, viet_phrase: Trie, chinese_phien_am: Dict[str, str]) -> str:
    """
    Process a single paragraph of text.

    :param paragraph: The input paragraph
    :param names2: Trie containing Names2 data
    :param names: Trie containing Names data
    :param viet_phrase: Trie containing VietPhrase data
    :param chinese_phien_am: Dictionary containing Chinese Phien Am data
    :return: The processed paragraph
    """
    converted = convert_to_sino_vietnamese(paragraph, names2, names, viet_phrase, chinese_phien_am)
    return converted

def convert_filename(filename: str, names2: Trie, names: Trie, viet_phrase: Trie, chinese_phien_am: Dict[str, str]) -> str:
    """
    Convert a filename to Sino-Vietnamese.

    :param filename: The input filename
    :param names2: Trie containing Names2 data
    :param names: Trie containing Names data
    :param viet_phrase: Trie containing VietPhrase data
    :param chinese_phien_am: Dictionary containing Chinese Phien Am data
    :return: The converted filename
    """
    base_name = os.path.basename(filename)
    name_without_ext, ext = os.path.splitext(base_name)
    converted_name = convert_to_sino_vietnamese(name_without_ext, names2, names, viet_phrase, chinese_phien_am)
    
    # Remove any characters that are not allowed in filenames
    converted_name = ''.join(char for char in converted_name if char not in r'<>:"/\|?*')
    
    return f"{converted_name}_Converted{ext}"
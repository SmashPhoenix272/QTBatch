import re
import logging
from ReplaceChar import SPECIAL_CHARS
import time
import os

class TrieNode:
    __slots__ = ['children', 'is_end_of_word', 'value']
    def __init__(self):
        self.children = {}
        self.is_end_of_word = False
        self.value = None

class Trie:
    def __init__(self):
        self.root = TrieNode()
        self.word_count = 0

    def insert(self, word, value):
        current = self.root
        for char in word:
            if char not in current.children:
                current.children[char] = TrieNode()
            current = current.children[char]
        current.is_end_of_word = True
        current.value = value
        self.word_count += 1

    def batch_insert(self, words):
        for word, value in words:
            self.insert(word, value)

    def count(self):
        return self.word_count

    def find_longest_prefix(self, text):
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

def load_data():
    names2 = Trie()
    names = Trie()
    viet_phrase = Trie()
    chinese_phien_am = {}
    
    loading_info = {
        "names2": {"loaded": False, "count": 0, "time": 0},
        "names": {"loaded": False, "count": 0, "time": 0},
        "chinese_words": {"loaded": False, "count": 0, "time": 0},
        "viet_phrase": {"loaded": False, "count": 0, "time": 0}
    }

    # Load Names2.txt
    try:
        start_time = time.time()
        with open('Names2.txt', 'r', encoding='utf-8') as f:
            name2_entries = []
            for line in f:
                parts = line.strip().split('=')
                if len(parts) == 2:
                    name2_entries.append((parts[0], parts[1]))
            names2.batch_insert(name2_entries)
        loading_info["names2"]["loaded"] = True
        loading_info["names2"]["count"] = names2.count()
        loading_info["names2"]["time"] = time.time() - start_time
        logging.info(f"Loaded {names2.count()} names from Names2.txt in {loading_info['names2']['time']:.2f} seconds")
    except FileNotFoundError:
        logging.warning("Names2.txt not found. Proceeding without Names2 data.")

    # Load Names.txt
    try:
        start_time = time.time()
        with open('Names.txt', 'r', encoding='utf-8') as f:
            name_entries = []
            for line in f:
                parts = line.strip().split('=')
                if len(parts) == 2:
                    name_entries.append((parts[0], parts[1]))
        names.batch_insert(name_entries)
        loading_info["names"]["loaded"] = True
        loading_info["names"]["count"] = names.count()
        loading_info["names"]["time"] = time.time() - start_time
        logging.info(f"Loaded {names.count()} names in {loading_info['names']['time']:.2f} seconds")
    except FileNotFoundError:
        logging.warning("Names.txt not found. Proceeding without names data.")

    # Load ChinesePhienAmWords.txt
    try:
        start_time = time.time()
        with open('ChinesePhienAmWords.txt', 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                parts = line.strip().split('=')
                if len(parts) == 2:
                    chinese_phien_am[parts[0]] = parts[1]
        loading_info["chinese_words"]["loaded"] = True
        loading_info["chinese_words"]["count"] = len(chinese_phien_am)
        loading_info["chinese_words"]["time"] = time.time() - start_time
        logging.info(f"Loaded {len(chinese_phien_am)} Chinese words in {loading_info['chinese_words']['time']:.2f} seconds")
    except FileNotFoundError:
        logging.warning("ChinesePhienAmWords.txt not found.")

    # Load VietPhrase.txt
    try:
        start_time = time.time()
        vietphrase_entries = []
        with open('VietPhrase.txt', 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('=')
                if len(parts) == 2:
                    key, value = parts
                    first_value = value.split('/')[0]
                    vietphrase_entries.append((key, first_value))
        viet_phrase.batch_insert(vietphrase_entries)
        loading_info["viet_phrase"]["loaded"] = True
        loading_info["viet_phrase"]["count"] = len(vietphrase_entries)
        loading_info["viet_phrase"]["time"] = time.time() - start_time
        logging.info(f"Loaded {len(vietphrase_entries)} VietPhrase entries in {loading_info['viet_phrase']['time']:.2f} seconds")
    except FileNotFoundError:
        logging.error("VietPhrase.txt not found. This file is required.")
        raise

    return names2, names, viet_phrase, chinese_phien_am, loading_info


def read_novel_file(file_path):
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

def replace_special_chars(text):
    original = text
    for han, viet in SPECIAL_CHARS.items():
        text = text.replace(han, viet)

    if original != text:
        logging.debug(f"Special characters replaced: '{original}' -> '{text}'")
    return text

def convert_to_sino_vietnamese(text, names2, names, viet_phrase, chinese_phien_am):
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
    text = re.sub(r'([\[\“\‘])\s*(\w)', lambda m: m.group(1) + m.group(2).upper(), text)
    # Remove spaces before right quotation marks
    text = re.sub(r'\s+([”\’\]])', r'\1', text)
    # Capitalize first word after ? and ! marks
    text = re.sub(r'([?!⟨:])\s+(\w)', lambda m: m.group(1) + ' ' + m.group(2).upper(), text)
    # Remove spaces before colon and semicolon
    text = re.sub(r'\s+([;:?!.])', r'\1', text)
    # Capitalize first word after a single dot, but not after triple dots
    text = re.sub(r'(?<!\.)\.(?!\.)\s+(\w)', lambda m: '. ' + m.group(1).upper(), text)

    return text

def process_paragraph(paragraph, names2, names, viet_phrase, chinese_phien_am):
    converted = convert_to_sino_vietnamese(paragraph, names2, names, viet_phrase, chinese_phien_am)
    return converted

def convert_filename(filename, names2, names, viet_phrase, chinese_phien_am):
    base_name = os.path.basename(filename)
    name_without_ext, ext = os.path.splitext(base_name)
    converted_name = convert_to_sino_vietnamese(name_without_ext, names2, names, viet_phrase, chinese_phien_am)
    
    # Remove any characters that are not allowed in filenames
    converted_name = ''.join(char for char in converted_name if char not in r'<>:"/\|?*')
    
    return f"{converted_name}_Converted{ext}"


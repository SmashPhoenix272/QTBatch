import hanlp
import pandas as pd
from collections import defaultdict
import os
import time
import sqlite3
from typing import List, Dict, Tuple, Any, Optional, Callable
from utils import detect_chapters
import logging
import sys
import traceback
import csv
from functools import lru_cache

CATEGORY_TRANSLATION: Dict[str, str] = {
    'PERSON': 'Person Name',
    'LOCATION': 'Place Name',
    'ORGANIZATION': 'Organization Name'
}

CATEGORY_ORDER: List[str] = list(CATEGORY_TRANSLATION.values())

def process_paragraph(paragraph: str, recognizer: Any, tokenizer: Any) -> List[Any]:
    sentences: List[str] = []
    current_sentence: str = ""
    for char in paragraph:
        current_sentence += char
        if char in ['。', '！', '？']:
            sentences.append(current_sentence)
            current_sentence = ""
    if current_sentence:
        sentences.append(current_sentence)

    paragraph_entities: List[Any] = []
    for sentence in sentences:
        if sentence:
            segments = split_sentence(sentence)
            for segment in segments:
                try:
                    tokens = tokenizer(segment)
                    if len(tokens) > 126:
                        print(f"Warning: Segment still too long: {len(tokens)} tokens")
                        continue
                    entities = recognizer(tokens)
                    paragraph_entities.extend(entities)
                except Exception as e:
                    logging.error(f"Error during HanLP analysis: {e}")
                    logging.error(f"Segment causing error: {segment}")
                    logging.error(f"Full traceback: {traceback.format_exc()}")
    return paragraph_entities

@lru_cache(maxsize=1000)
def split_sentence(sentence: str, max_chars: int = 126) -> Tuple[str, ...]:
    if len(sentence) <= max_chars:
        return (sentence,)
    
    parts = sentence.split('，')
    if max(len(part) for part in parts) <= max_chars:
        return tuple(parts)
    
    return tuple(sentence[i:i+max_chars] for i in range(0, len(sentence), max_chars))

class HanLPAnalyzer:
    def __init__(self, novel_path: str, dictionary_path: str):
        self.novel_path: str = novel_path
        self.dictionary_path: str = dictionary_path
        self.dictionary_mapping: Dict[str, str] = self.read_dictionary()
        self.novel_text: str = ""
        self.all_entities: List[Any] = []
        self.entity_info: Dict[str, Dict[str, Any]] = defaultdict(lambda: {'category': '', 'appearances': 0})
        self.progress: float = 0
        self.is_paused: bool = False
        self.is_stopped: bool = False
        self.cache_path: str = os.path.join('caches', f"{os.path.basename(novel_path)}.db")

        # Load models
        self.recognizer: Optional[Any] = None
        self.tokenizer: Optional[Any] = None
        self.models_loaded: bool = False

        # Set up logging
        logging.basicConfig(filename='name_analyzer.log', level=logging.WARNING, 
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            encoding='utf-8')

    def load_models(self) -> None:
        print("Loading HanLP models...")
        self.recognizer = hanlp.load(hanlp.pretrained.ner.MSRA_NER_ELECTRA_SMALL_ZH)
        self.tokenizer = hanlp.load(hanlp.pretrained.tok.CTB9_TOK_ELECTRA_BASE)
        self.models_loaded = True
        print("HanLP models loaded successfully.")

    def is_ready(self) -> bool:
        return self.models_loaded

    def read_dictionary(self) -> Dict[str, str]:
        mapping: Dict[str, str] = {}
        try:
            with open(self.dictionary_path, 'r', encoding='utf-8') as file:
                for line in file:
                    if '=' in line:
                        chinese_word, sino_vietnamese_word = line.strip().split('=')
                        mapping[chinese_word] = sino_vietnamese_word.capitalize()
        except Exception as e:
            print(f"Error reading file {self.dictionary_path}: {e}")
        return mapping

    @lru_cache(maxsize=10000)
    def translate_to_sino_vietnamese(self, chinese_name: str) -> str:
        return ' '.join(self.dictionary_mapping.get(char, char) for char in chinese_name)

    def read_novel(self) -> None:
        encodings_to_try: List[str] = ['utf-8', 'gbk', 'gb2312', 'big5', 'ascii']
        
        for encoding in encodings_to_try:
            try:
                with open(self.novel_path, 'r', encoding=encoding) as file:
                    self.novel_text = file.read()
                print(f"Successfully read the file using {encoding} encoding.")
                return
            except UnicodeDecodeError:
                print(f"Failed to read with {encoding} encoding.")
        
        print("Failed to read the file with any of the attempted encodings.")
        raise ValueError("Unable to read the novel file")

    def analyze(self, progress_callback: Optional[Callable[[float], None]] = None, start_chapter: Optional[int] = None, end_chapter: Optional[int] = None) -> None:
        if not self.models_loaded:
            self.load_models()

        try:
            self.read_novel()
            paragraphs: List[str] = self.novel_text.split('\n')
            total_paragraphs: int = len(paragraphs)

            # Load cache if exists
            if self.load_cache():
                self.progress = len(self.entity_info) / total_paragraphs
                if progress_callback:
                    progress_callback(self.progress)

            start_paragraph: int = int(self.progress * total_paragraphs)

            # If chapter range is specified, adjust start and end paragraphs
            if start_chapter is not None and end_chapter is not None:
                chapters = detect_chapters(self.novel_text)
                if chapters:
                    start_paragraph = chapters[start_chapter - 1][0] if start_chapter <= len(chapters) else 0
                    end_paragraph = chapters[end_chapter][0] if end_chapter < len(chapters) else None
                    paragraphs = paragraphs[start_paragraph:end_paragraph]
                    total_paragraphs = len(paragraphs)
                    start_paragraph = 0

            for i, paragraph in enumerate(paragraphs[start_paragraph:], start=start_paragraph):
                if self.is_stopped:
                    break
                while self.is_paused:
                    time.sleep(0.1)

                entities = process_paragraph(paragraph, self.recognizer, self.tokenizer)
                self.update_entity_info(entities, paragraph)

                self.progress = (i + 1) / total_paragraphs
                if progress_callback:
                    progress_callback(self.progress)

                if (i + 1) % 10 == 0:  # Cache every 10 paragraphs
                    self.cache_progress()

            self.cache_progress()  # Final cache
        except Exception as e:
            logging.error(f"Error during analysis: {e}")
            logging.error(f"Full traceback: {traceback.format_exc()}")

    def update_entity_info(self, entities: List[Any], paragraph: str) -> None:
        try:
            for entity in entities:
                if isinstance(entity, dict) and 'entity' in entity and 'type' in entity:
                    name: str = entity['entity']
                    category: str = entity['type']
                elif isinstance(entity, tuple) and len(entity) >= 2:
                    name: str = entity[0]
                    category: str = entity[1]
                else:
                    continue  # Skip unexpected entity formats

                if category not in CATEGORY_TRANSLATION:
                    continue  # Skip categories that are not PERSON, LOCATION, or ORGANIZATION

                # Check if the character after the name is a punctuation mark
                name_end_index = paragraph.find(name) + len(name)
                if name_end_index < len(paragraph):
                    next_char = paragraph[name_end_index]
                    if next_char in ['。', '！', '？', '；', '，']:
                        continue  # Skip this name for this session

                # If we reach here, the name is valid for this session
                self.entity_info[name]['category'] = category
                self.entity_info[name]['appearances'] += 1

        except Exception as e:
            logging.error(f"Error in update_entity_info: {e}")
            logging.error(f"Entities causing error: {entities}")
            logging.error(f"Entity type: {type(entities)}")
            logging.error(f"Full traceback: {traceback.format_exc()}")

    def cache_progress(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            conn: sqlite3.Connection = sqlite3.connect(self.cache_path)
            cursor: sqlite3.Cursor = conn.cursor()
            
            cursor.execute('''CREATE TABLE IF NOT EXISTS entities
                              (entity TEXT PRIMARY KEY, category TEXT, appearances INTEGER)''')
            
            cursor.execute('''CREATE TABLE IF NOT EXISTS progress
                              (id INTEGER PRIMARY KEY, progress REAL)''')
            
            for entity, info in self.entity_info.items():
                cursor.execute('''INSERT OR REPLACE INTO entities (entity, category, appearances)
                                  VALUES (?, ?, ?)''', (entity, info['category'], info['appearances']))
            
            cursor.execute('''INSERT OR REPLACE INTO progress (id, progress)
                              VALUES (1, ?)''', (self.progress,))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error(f"Error in cache_progress: {e}")
            logging.error(f"Full traceback: {traceback.format_exc()}")

    def load_cache(self) -> bool:
        try:
            if os.path.exists(self.cache_path):
                conn: sqlite3.Connection = sqlite3.connect(self.cache_path)
                cursor: sqlite3.Cursor = conn.cursor()
                
                cursor.execute('SELECT entity, category, appearances FROM entities')
                for entity, category, appearances in cursor.fetchall():
                    self.entity_info[entity]['category'] = category
                    self.entity_info[entity]['appearances'] = appearances
                
                cursor.execute('SELECT progress FROM progress WHERE id = 1')
                result: Optional[Tuple[float]] = cursor.fetchone()
                if result:
                    self.progress = result[0]
                
                conn.close()
                return True
            return False
        except Exception as e:
            logging.error(f"Error in load_cache: {e}")
            logging.error(f"Full traceback: {traceback.format_exc()}")
            return False

    def export_to_csv(self, output_file: str = 'AnalyzedNames.csv') -> None:
        try:
            data: List[Dict[str, Any]] = []
            for entity, info in self.entity_info.items():
                sino_vietnamese_name: str = self.translate_to_sino_vietnamese(entity)
                data.append({
                    'Category': CATEGORY_TRANSLATION.get(info['category'], info['category']),
                    'Name': entity,
                    'NameSinoVietnamese': sino_vietnamese_name,
                    'Appearances': info['appearances']
                })
            
            if not data:
                print("No names found to export.")
                return

            df: pd.DataFrame = pd.DataFrame(data)
            
            # Ensure 'Category' column exists
            if 'Category' not in df.columns:
                df['Category'] = 'Unknown'  # Set a default category if missing
            
            # Create a custom sorting key based on the CATEGORY_ORDER
            category_order_dict: Dict[str, int] = {cat: i for i, cat in enumerate(CATEGORY_ORDER)}
            df['CategoryOrder'] = df['Category'].map(category_order_dict)
            
            # Sort by Category (using the custom order) first, then by Appearances in descending order
            df = df.sort_values(['CategoryOrder', 'Appearances'], ascending=[True, False])
            
            # Remove the temporary sorting column
            df = df.drop('CategoryOrder', axis=1)
            
            # Write to CSV with UTF-8 encoding and BOM
            with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Category', 'Name', 'NameSinoVietnamese', 'Appearances'])
                for _, row in df.iterrows():
                    writer.writerow([row['Category'], row['Name'], row['NameSinoVietnamese'], row['Appearances']])
            
            print(f"Results exported to {output_file}")
        except Exception as e:
            logging.error(f"Error in export_to_csv: {e}")
            logging.error(f"Full traceback: {traceback.format_exc()}")

    def export_to_names2(self, settings: Dict[str, int], name_length_range: Tuple[int, int], csv_file: str = 'AnalyzedNames.csv', output_file: str = 'Names2.txt') -> None:
        try:
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                with open(output_file, 'w', encoding='utf-8') as out_f:
                    for row in reader:
                        category = row['Category']
                        name = row['Name']
                        appearances = int(row['Appearances'])
                        name_length = len(name)

                        if (category in settings and appearances >= settings[category] and
                            name_length_range[0] <= name_length <= name_length_range[1]):
                            out_f.write(f"{row['Name']}={row['NameSinoVietnamese']}\n")

            print(f"Names2 file created: {output_file} (settings: {settings}, name length range: {name_length_range})")
        except Exception as e:
            logging.error(f"Error in export_to_names2: {e}")
            logging.error(f"Full traceback: {traceback.format_exc()}")

    def get_status(self) -> Dict[str, int]:
        status: Dict[str, int] = {category: 0 for category in CATEGORY_TRANSLATION.values()}
        for info in self.entity_info.values():
            category: str = CATEGORY_TRANSLATION.get(info['category'], info['category'])
            if category in status:
                status[category] += 1
        return status

    def pause(self) -> None:
        self.is_paused = True

    def resume(self) -> None:
        self.is_paused = False

    def stop(self) -> None:
        self.is_stopped = True

    def reset_cache(self) -> None:
        if os.path.exists(self.cache_path):
            os.remove(self.cache_path)
        self.progress = 0
        self.entity_info.clear()
        self.all_entities.clear()

# Usage example:
# analyzer = HanLPAnalyzer('path_to_novel.txt', 'path_to_ChinesePhienAmWords.txt')
# analyzer.analyze(progress_callback=lambda p: print(f"Progress: {p*100:.2f}%"))
# analyzer.export_to_csv()
# analyzer.export_to_names2(minimum_appearances=5)
# print(analyzer.get_status())
import time
import os
import threading
from typing import Dict, Any, List
import logging
import opencc
import queue
from concurrent.futures import ThreadPoolExecutor
import statistics

import QuickTranslator as qt
from gui import GUI
from name_analyzer import HanLPAnalyzer, CATEGORY_TRANSLATION
from ai_proofread import AIProofreader, load_names_from_file
import dearpygui.dearpygui as dpg
import config
from utils import check_and_download_fonts, get_file_size_str, detect_chinese_script
from logging_config import setup_logging

logger = setup_logging()

def measure_api_response_time(text: str, names2: qt.Trie, names: qt.Trie, viet_phrase: qt.Trie, chinese_phien_am: Dict[str, str]) -> float:
    start_time = time.time()
    qt.process_novel(text, names2, names, viet_phrase, chinese_phien_am, lambda _: False, False, None, None, lambda: None)
    end_time = time.time()
    return end_time - start_time

def split_text_into_chunks(text: str, names2: qt.Trie, names: qt.Trie, viet_phrase: qt.Trie, chinese_phien_am: Dict[str, str], initial_chunk_size: int = 5500, target_response_time: float = 5.0, max_chunk_size: int = 10000) -> List[str]:
    chunks = []
    current_chunk = ""
    chunk_size = initial_chunk_size
    response_times = []

    for paragraph in text.split('\n'):
        if len(current_chunk) + len(paragraph) + 1 > chunk_size:
            if current_chunk:
                chunks.append(current_chunk)
                response_time = measure_api_response_time(current_chunk, names2, names, viet_phrase, chinese_phien_am)
                response_times.append(response_time)

                # Adjust chunk size based on response time
                if len(response_times) >= 3:
                    avg_response_time = statistics.mean(response_times[-3:])
                    if avg_response_time < target_response_time * 0.8:
                        chunk_size = min(int(chunk_size * 1.2), max_chunk_size)
                    elif avg_response_time > target_response_time * 1.2:
                        chunk_size = max(int(chunk_size * 0.8), initial_chunk_size)

            current_chunk = paragraph
        else:
            current_chunk += '\n' + paragraph if current_chunk else paragraph

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

class QuickTranslatorGUI:
    def __init__(self):
        print("Initializing QuickTranslatorGUI...")
        self.novel_path: str = ""
        self.novel_text: str = ""
        self.loading_info: Dict[str, Dict[str, Any]] = {
            "names2": {"loaded": False, "count": 0, "time": 0},
            "names": {"loaded": False, "count": 0, "time": 0},
            "chinese_words": {"loaded": False, "count": 0, "time": 0},
            "viet_phrase": {"loaded": False, "count": 0, "time": 0}
        }
        self.conversion_running: bool = False
        self.stop_conversion: bool = False
        self.names2_reloaded = False

        self.max_workers = 4  # Default number of parallel processing threads
        self.paused = False
        self.pause_condition = threading.Condition()

        # Initialize attributes
        self.names2 = qt.Trie()
        self.names = qt.Trie()
        self.viet_phrase = qt.Trie()
        self.chinese_phien_am = {}

        # HanLP analysis variables
        self.hanlp_analyzer: HanLPAnalyzer = None
        self.hanlp_thread: threading.Thread = None
        self.hanlp_running: bool = False

        # OpenCC converter
        opencc_config_path = os.path.join(os.path.dirname(opencc.__file__), 'config', 't2s.json')
        print(f"OpenCC config path: {opencc_config_path}")
        print(f"OpenCC config file exists: {os.path.exists(opencc_config_path)}")
        try:
            self.opencc_converter = opencc.OpenCC(opencc_config_path[:-5])  # Remove .json extension
            print("OpenCC converter initialized successfully")
        except Exception as e:
            print(f"Error initializing OpenCC converter: {str(e)}")

        fonts = [
            (config.CHINESE_FONT_PATH, config.CHINESE_FONT_URL, "Chinese"),
            (config.VIETNAMESE_FONT_PATH, config.VIETNAMESE_FONT_URL, "Vietnamese")
        ]
        check_and_download_fonts(config.FONT_DIR, fonts)
        # Chapters
        self.start_chapter = 1
        self.end_chapter = 999999
        self.detect_chapters_enabled = False
        self.ai_proofreader = AIProofreader(self, self.update_ai_proofread_settings)

        self.gui = GUI(
            load_novel_callback=self.load_novel,
            reload_names2_callback=self.reload_names2,
            start_conversion_callback=self.start_conversion,
            stop_conversion_callback=lambda: setattr(self, 'stop_conversion', True),
            start_hanlp_callback=self.start_hanlp_analysis,
            stop_hanlp_callback=self.stop_hanlp_analysis,
            pause_hanlp_callback=self.pause_hanlp_analysis,
            resume_hanlp_callback=self.resume_hanlp_analysis,
            export_names_to_csv_callback=self.export_names_to_csv,
            csv_to_names2_callback=self.csv_to_names2,
            reanalyze_hanlp_callback=self.reanalyze_hanlp_analysis,
            tc_to_sc_callback=self.tc_to_sc_conversion,
            chapter_range_callback=self.update_chapter_range,
            pause_conversion_callback=self.pause_conversion,
            resume_conversion_callback=self.resume_conversion,
            set_max_workers_callback=self.set_max_workers
        )
        print("QuickTranslatorGUI initialized.")

        # Start data loading in a separate thread
        self.data_loading_thread = threading.Thread(target=self.load_data_in_background)
        self.data_loading_thread.start()
        self.gui_update_queue = queue.Queue()

    def load_data_in_background(self):
        print("Loading data in background...")
        self.names2, self.names, self.viet_phrase, self.chinese_phien_am, self.loading_info = qt.load_data()
        if 'chinese_words' in self.loading_info:
            logging.info(f"Chinese words loaded: {self.loading_info['chinese_words']}")
        else:
            logging.warning("Chinese words data not found in loading_info")
        self.gui.update_status(self.loading_info)
        self.gui.set_conversion_data(self.names2, self.names, self.viet_phrase, self.chinese_phien_am)
        print("Data loading completed.")

    def load_novel(self, sender: Any, app_data: Dict[str, Any]):
        print("Loading novel...")
        if 'file_path_name' not in app_data or not app_data['file_path_name']:
            logger.warning("No file selected or invalid file path")
            self.gui.update_novel_status("No file selected", "N/A", "N/A", "N/A")
            return

        self.novel_path = app_data['file_path_name']
    
        if not os.path.exists(self.novel_path):
            logger.error(f"File not found: {self.novel_path}")
            self.gui.update_novel_status("Error: File not found", "N/A", "N/A", "N/A")
            return

        try:
            self.novel_text, encoding = qt.read_novel_file(self.novel_path)
            novel_name = os.path.basename(self.novel_path)
            size_str = get_file_size_str(self.novel_path)
            chinese_form = detect_chinese_script(self.novel_text[:1000])  # Detect script using the first 1000 characters
            self.gui.update_novel_status(novel_name, encoding, size_str, chinese_form)
            self.gui.update_novel_preview(self.novel_text[:150])
            self.gui.update_conversion_status(f"Not started", (255, 165, 0))
            self.gui.update_conversion_time("")
            self.gui.update_conversion_progress(0.0)
            self.gui.update_conversion_percent(0.0)
            self.gui.update_status_bar(f"Novel loaded: {novel_name}.")
            self.gui.update_conversion_preview(self.novel_text[:150])

            # Initialize HanLPAnalyzer
            self.hanlp_analyzer = HanLPAnalyzer(self.novel_path, 'ChinesePhienAmWords.txt')
            
            # Load cache and update progress/status if available
            if self.hanlp_analyzer.load_cache():
                self.gui.update_hanlp_progress(self.hanlp_analyzer.progress)
                status = self.hanlp_analyzer.get_status()
                self.gui.update_name_analyzing_status(status)
                self.gui.update_status_bar(f"Loaded cached analysis. Progress: {self.hanlp_analyzer.progress:.2%}")
            else:
                # Reset HanLP progress and status
                self.gui.update_hanlp_progress(0.0)
                initial_status = {category: 0 for category in CATEGORY_TRANSLATION.values()}
                self.gui.update_name_analyzing_status(initial_status)
                self.gui.update_status_bar("HanLP analyzer initialized. Loading models...")

            # Start a thread to load HanLP models
            threading.Thread(target=self.load_hanlp_models).start()

            print(f"Novel loaded: {novel_name}")
        except Exception as e:
            logger.error(f"Error loading novel: {str(e)}")
            self.gui.update_novel_status("Error", "N/A", "N/A", "N/A")
            print(f"Error loading novel: {str(e)}")

    def load_hanlp_models(self):
        self.hanlp_analyzer.load_models()
        self.gui.update_status_bar("HanLP models loaded. Ready for analysis.")

    def reload_names2(self):
        print("Reloading Names2...")
        start_time = time.time()
        try:
            with open(config.NAMES2_PATH, 'r', encoding='utf-8') as f:
                name2_entries = [tuple(line.strip().split('=')) for line in f if len(line.strip().split('=')) == 2]
            self.names2 = qt.Trie()
            self.names2.batch_insert(name2_entries)
            self.loading_info["names2"]["loaded"] = True
            self.loading_info["names2"]["count"] = self.names2.count()
            self.loading_info["names2"]["time"] = time.time() - start_time
            logger.info(f"Reloaded {self.names2.count()} names from Names2.txt in {self.loading_info['names2']['time']:.2f} seconds")
            self.gui.names2_reloaded = True
            self.gui.update_status(self.loading_info)
            self.gui.set_conversion_data(self.names2, self.names, self.viet_phrase, self.chinese_phien_am)
            print(f"Names2 reloaded: {self.names2.count()} names")
        except FileNotFoundError:
            logger.warning("Names2.txt not found. Unable to reload.")
            self.gui.update_status({"names2": {"loaded": False, "count": 0, "time": 0}})
            print("Error: Names2.txt not found")
        finally:
            dpg.render_dearpygui_frame()

    def update_chapter_range(self, start_chapter, end_chapter, detect_chapters_enabled):
        self.start_chapter = start_chapter
        self.end_chapter = end_chapter
        self.detect_chapters_enabled = detect_chapters_enabled

    def start_conversion(self):
        print("Starting conversion...")
        if not self.data_loading_thread.is_alive() and self.loading_info["viet_phrase"]["loaded"]:
            if not self.novel_text:
                self.gui.update_conversion_status("No text to convert")
                print("Error: No text to convert")
                return

            detect_chapters_enabled = self.gui.detect_chapters
            apply_to_conversion = self.gui.apply_to_conversion if hasattr(self.gui, 'apply_to_conversion') else False
            chapter_range_applied = self.gui.chapter_range_applied if hasattr(self.gui, 'chapter_range_applied') else False

            # Determine which text to use based on the conditions
            if detect_chapters_enabled and apply_to_conversion and chapter_range_applied:
                # Use the chapter range text
                with open(self.gui.temp_file_path, "r", encoding="utf-8") as temp_file:
                    text_to_convert = temp_file.read()
                start_chapter = self.gui.start_chapter
                end_chapter = self.gui.end_chapter
            else:
                # Use the full novel text
                text_to_convert = self.novel_text
                start_chapter = 1
                end_chapter = 999999

            self.conversion_running = False
            self.stop_conversion = False

            if self.conversion_running:
                return

            self.conversion_running = True
            self.gui.update_conversion_status("Running", (0, 255, 0))
            
            # Generate export filename
            base_filename = qt.convert_filename(os.path.basename(self.novel_path), self.names2, self.names, self.viet_phrase, self.chinese_phien_am)
            name, ext = os.path.splitext(base_filename)
            if detect_chapters_enabled and apply_to_conversion and chapter_range_applied:
                export_filename = f"{name}_Converted_{start_chapter}-{end_chapter}{ext}"
            else:
                export_filename = f"{name}_Converted{ext}"

            threading.Thread(target=self.run_conversion, args=(detect_chapters_enabled, apply_to_conversion, chapter_range_applied, start_chapter, end_chapter, export_filename, text_to_convert)).start()
        else:
            self.gui.update_conversion_status("Waiting for data to load")
            print("Waiting for data to load")

    def run_conversion(self, detect_chapters_enabled, apply_to_conversion, chapter_range_applied, start_chapter, end_chapter, export_filename, text_to_convert):
        print(f"Running conversion (detect_chapters_enabled={detect_chapters_enabled}, apply_to_conversion={apply_to_conversion}, chapter_range_applied={chapter_range_applied}, start_chapter={start_chapter}, end_chapter={end_chapter}, export_filename={export_filename})...")
        start_time = time.time()
        try:
            chunks = split_text_into_chunks(text_to_convert, self.names2, self.names, self.viet_phrase, self.chinese_phien_am)
            total_chunks = len(chunks)
            converted_chunks = queue.Queue()
            proofread_chunks = queue.Queue()

            def update_progress_and_status(conversion_progress, proofreading_progress, message):
                self.gui_update_queue.put(lambda: dpg.set_value("conversion_progress", conversion_progress))
                self.gui_update_queue.put(lambda: dpg.does_item_exist("proofreading_progress") and dpg.set_value("proofreading_progress", proofreading_progress))
                self.gui_update_queue.put(lambda: dpg.set_value("conversion_status", message))
                logging.info(message)

            def estimate_time_remaining(elapsed_time, progress):
                if progress > 0:
                    total_time = elapsed_time / progress
                    return total_time - elapsed_time
                return 0

            def chunk_progress_callback(chunk_index, chunk_progress):
                if self.stop_conversion:
                    return True  # Signal to stop the conversion
                with self.pause_condition:
                    while self.paused:
                        self.pause_condition.wait()
                overall_progress = (chunk_index + chunk_progress) / total_chunks
                elapsed_time = time.time() - start_time
                time_remaining = estimate_time_remaining(elapsed_time, overall_progress)
                message = f"Converting chunk {chunk_index + 1}/{total_chunks} - {chunk_progress:.1%} complete. Estimated time remaining: {time_remaining:.1f} seconds"
                self.gui_update_queue.put(lambda: update_progress_and_status(overall_progress, 0, message))
                return False  # Continue the conversion

            def convert_chunk(chunk_index, chunk):
                try:
                    converted_chunk = qt.process_novel(
                        chunk,
                        self.names2,
                        self.names,
                        self.viet_phrase,
                        self.chinese_phien_am,
                        lambda progress: chunk_progress_callback(chunk_index, progress),
                        False,
                        None,
                        None,
                        self.update_ai_proofread_cache_percentage
                    )
                    converted_chunks.put((chunk_index, converted_chunk))
                except Exception as e:
                    logging.error(f"Error converting chunk {chunk_index}: {str(e)}")
                    self.gui_update_queue.put(lambda: self.gui.add_log_message(f"Error converting chunk {chunk_index}: {str(e)}"))
                    converted_chunks.put((chunk_index, None))  # Put None to indicate error

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                for i, chunk in enumerate(chunks):
                    executor.submit(convert_chunk, i, chunk)

            output_path = os.path.join(os.path.dirname(self.novel_path), export_filename)
            with open(output_path, 'w', encoding='utf-8') as f:
                converted_count = 0
                proofread_count = 0
                chunks_to_write = {}
                next_chunk_to_write = 0

                while not self.stop_conversion:
                    try:
                        chunk_index, converted_chunk = converted_chunks.get(timeout=1)
                        if converted_chunk is None:
                            # Handle error in chunk conversion
                            self.gui_update_queue.put(lambda: self.gui.add_log_message(f"Skipping chunk {chunk_index} due to conversion error"))
                            continue
                        converted_count += 1
                        conversion_progress = converted_count / total_chunks
                        proofreading_progress = proofread_count / total_chunks
                        message = f"Converted: {converted_count}/{total_chunks}, Proofread: {proofread_count}/{total_chunks}"
                        self.gui_update_queue.put(lambda: update_progress_and_status(conversion_progress, proofreading_progress, message))
                        
                        if self.gui.ai_proofread_enabled:
                            try:
                                self.gui_update_queue.put(lambda: self.gui.update_status_bar(f"AI Proofreading chunk {chunk_index + 1}/{total_chunks}..."))
                                names = load_names_from_file('Names2.txt')
                                
                                # Check if the chunk is in the cache
                                cache_key = self.ai_proofreader.cache.get_cache_key(chunks[chunk_index], converted_chunk, names)
                                cached_result = self.ai_proofreader.cache.get_cached_result(os.path.basename(self.novel_path), chunks[chunk_index], converted_chunk, names)
                                
                                if cached_result:
                                    logging.info(f"Using cached result for chunk {chunk_index + 1}")
                                    proofread_chunk = cached_result
                                else:
                                    logging.info(f"Proofreading chunk {chunk_index + 1}")
                                    proofread_chunk = self.ai_proofreader.proofread_chunk(chunks[chunk_index], converted_chunk, names, os.path.basename(self.novel_path))
                                
                                chunks_to_write[chunk_index] = proofread_chunk
                                proofread_count += 1
                                
                                # Update cache percentage
                                self.update_ai_proofread_cache_percentage()
                            except Exception as e:
                                logging.error(f"Error during AI proofreading: {str(e)}")
                                self.gui_update_queue.put(lambda: self.gui.add_log_message(f"Error during AI proofreading: {str(e)}"))
                                chunks_to_write[chunk_index] = converted_chunk  # Use the non-proofread chunk in case of error
                                proofread_count += 1
                        else:
                            chunks_to_write[chunk_index] = converted_chunk
                            proofread_count += 1
                        
                        # Write chunks in order
                        while next_chunk_to_write in chunks_to_write:
                            f.write(chunks_to_write[next_chunk_to_write])
                            del chunks_to_write[next_chunk_to_write]
                            next_chunk_to_write += 1
                        
                        proofreading_progress = proofread_count / total_chunks
                        message = f"Converted: {converted_count}/{total_chunks}, Proofread: {proofread_count}/{total_chunks}"
                        self.gui_update_queue.put(lambda: update_progress_and_status(conversion_progress, proofreading_progress, message))
                    except queue.Empty:
                        if converted_chunks.empty() and proofread_count == total_chunks:
                            break

                # Write any remaining chunks
                for i in range(next_chunk_to_write, total_chunks):
                    if i in chunks_to_write:
                        f.write(chunks_to_write[i])

            if not self.stop_conversion:
                end_time = time.time()
                conversion_time = end_time - start_time

                if detect_chapters_enabled and apply_to_conversion and chapter_range_applied:
                    status_message = f"Complete. Converted chapters {start_chapter}-{end_chapter}."
                else:
                    status_message = "Complete. Converted entire novel."
                
                final_message = f"{status_message} Saved as {os.path.basename(output_path)}. Total time: {conversion_time:.2f} seconds"
                self.gui_update_queue.put(lambda: update_progress_and_status(1.0, 1.0, final_message))
                print(f"Conversion completed. Saved as {os.path.basename(output_path)}")
            else:
                self.gui_update_queue.put(lambda: update_progress_and_status(converted_count / total_chunks, proofread_count / total_chunks, "Conversion stopped"))
                print("Conversion stopped")

            # Update AI Proofread stats
            if self.gui.ai_proofread_enabled:
                stats = self.ai_proofreader.get_stats()
                self.gui_update_queue.put(lambda: self.gui.update_ai_proofread_stats(stats['total_tokens'], stats['total_cost']))

        except Exception as e:
            logging.error(f"Error during conversion: {str(e)}")
            self.gui_update_queue.put(lambda: self.gui.update_conversion_status(f"Error - {str(e)}"))
            self.gui_update_queue.put(lambda: self.gui.add_log_message(f"Error during conversion: {str(e)}"))
            print(f"Error during conversion: {str(e)}")
        finally:
            self.conversion_running = False
            self.paused = False
            
    def start_hanlp_analysis(self):
        print("Starting HanLP analysis...")
        if not self.hanlp_analyzer:
            self.gui.update_status_bar("No novel loaded for HanLP analysis")
            print("Error: No novel loaded for HanLP analysis")
            return

        if self.hanlp_running:
            self.gui.update_status_bar("HanLP analysis already running")
            print("HanLP analysis already running")
            return

        if not self.hanlp_analyzer.is_ready():
            self.gui.update_status_bar("HanLP models are still loading. Please wait.")
            print("HanLP models are still loading. Please wait.")
            return

        detect_chapters_enabled = self.gui.detect_chapters
        apply_to_hanlp = self.gui.apply_to_hanlp if hasattr(self.gui, 'apply_to_hanlp') else False
        chapter_range_applied = self.gui.chapter_range_applied if hasattr(self.gui, 'chapter_range_applied') else False

        if detect_chapters_enabled and apply_to_hanlp and chapter_range_applied:
            with open(self.gui.temp_file_path, "r", encoding="utf-8") as temp_file:
                text_to_analyze = temp_file.read()
            cache_file = f"{os.path.basename(self.novel_path)}_{self.gui.start_chapter}_{self.gui.end_chapter}.db"
        else:
            text_to_analyze = self.novel_text
            cache_file = f"{os.path.basename(self.novel_path)}.db"

        self.hanlp_analyzer.novel_text = text_to_analyze
        self.hanlp_analyzer.cache_path = os.path.join('caches', cache_file)

        # Check if the cache file exists
        if os.path.exists(self.hanlp_analyzer.cache_path):
            # Load the cache
            if self.hanlp_analyzer.load_cache():
                self.gui.update_hanlp_progress(self.hanlp_analyzer.progress)
                status = self.hanlp_analyzer.get_status()
                self.gui.update_name_analyzing_status(status)
                self.gui.update_status_bar(f"Loaded cached analysis for chapters {self.gui.start_chapter}-{self.gui.end_chapter}. Progress: {self.hanlp_analyzer.progress:.2%}")
            else:
                # If loading cache fails, reset progress and status
                self.hanlp_analyzer.reset_cache()
                self.gui.update_hanlp_progress(0.0)
                initial_status = {category: 0 for category in CATEGORY_TRANSLATION.values()}
                self.gui.update_name_analyzing_status(initial_status)
                self.gui.update_status_bar("Failed to load cache. Starting new analysis.")
        else:
            # If no cache file exists, reset progress and status
            self.hanlp_analyzer.reset_cache()
            self.gui.update_hanlp_progress(0.0)
            initial_status = {category: 0 for category in CATEGORY_TRANSLATION.values()}
            self.gui.update_name_analyzing_status(initial_status)
            self.gui.update_status_bar("Starting new analysis.")

        self.hanlp_running = True
        self.hanlp_thread = threading.Thread(target=self.run_hanlp_analysis)
        self.hanlp_thread.start()
        self.gui.update_status_bar("HanLP analysis started")

    def pause_conversion(self):
        self.paused = True
        self.gui.update_status_bar("Conversion paused")
        print("Conversion paused")

    def resume_conversion(self):
        with self.pause_condition:
            self.paused = False
            self.pause_condition.notify_all()
        self.gui.update_status_bar("Conversion resumed")
        print("Conversion resumed")

    def run_hanlp_analysis(self):
        print("Running HanLP analysis...")
        try:
            def progress_callback(progress):
                self.gui.update_hanlp_progress(progress)
                status = self.hanlp_analyzer.get_status()
                self.gui.update_name_analyzing_status(status)
                estimated_time = (1 - progress) * (time.time() - start_time) / progress if progress > 0 else 0
                self.gui.update_hanlp_estimated_time(estimated_time)
                print(f"HanLP analysis progress: {progress:.2f}")

            start_time = time.time()
            
            detect_chapters_enabled = self.gui.detect_chapters
            apply_to_hanlp = self.gui.apply_to_hanlp if hasattr(self.gui, 'apply_to_hanlp') else False
            chapter_range_applied = self.gui.chapter_range_applied if hasattr(self.gui, 'chapter_range_applied') else False

            start_chapter = self.gui.start_chapter if (detect_chapters_enabled and apply_to_hanlp and chapter_range_applied) else None
            end_chapter = self.gui.end_chapter if (detect_chapters_enabled and apply_to_hanlp and chapter_range_applied) else None

            self.hanlp_analyzer.analyze(progress_callback=progress_callback, start_chapter=start_chapter, end_chapter=end_chapter)
            
            if not self.hanlp_analyzer.is_stopped:
                if start_chapter and end_chapter:
                    self.gui.update_status_bar(f"HanLP analysis completed for chapters {start_chapter}-{end_chapter}")
                    print(f"HanLP analysis completed for chapters {start_chapter}-{end_chapter}")
                else:
                    self.gui.update_status_bar("HanLP analysis completed for entire novel")
                    print("HanLP analysis completed for entire novel")
            else:
                self.gui.update_status_bar("HanLP analysis stopped")
                print("HanLP analysis stopped")
        except Exception as e:
            logger.error(f"Error during HanLP analysis: {str(e)}")
            self.gui.update_status_bar(f"Error in HanLP analysis: {str(e)}")
            print(f"Error during HanLP analysis: {str(e)}")
        finally:
            self.hanlp_running = False

    def stop_hanlp_analysis(self):
        print("Stopping HanLP analysis...")
        if self.hanlp_analyzer:
            self.hanlp_analyzer.stop()
            self.gui.update_status_bar("Stopping HanLP analysis...")

    def pause_hanlp_analysis(self):
        print("Pausing HanLP analysis...")
        if self.hanlp_analyzer:
            self.hanlp_analyzer.pause()
            self.gui.update_status_bar("HanLP analysis paused")

    def resume_hanlp_analysis(self):
        print("Resuming HanLP analysis...")
        if self.hanlp_analyzer:
            self.hanlp_analyzer.resume()
            self.gui.update_status_bar("HanLP analysis resumed")

    def reanalyze_hanlp_analysis(self):
        print("Reanalyzing HanLP analysis...")
        if self.hanlp_analyzer:
            self.hanlp_analyzer.reset_cache()
            self.gui.update_hanlp_progress(0.0)
            self.gui.update_name_analyzing_status({category: 0 for category in self.hanlp_analyzer.get_status()})
            self.gui.update_status_bar("HanLP analysis cache reset. Ready for reanalysis.")
            print("HanLP analysis cache reset. Ready for reanalysis.")
        else:
            self.gui.update_status_bar("No HanLP analyzer initialized. Please load a novel first.")
            print("Error: No HanLP analyzer initialized. Please load a novel first.")

    def export_names_to_csv(self):
        print("Exporting names to CSV...")
        if self.hanlp_analyzer:
            try:
                self.hanlp_analyzer.export_to_csv()
                self.gui.update_status_bar("Names exported to CSV successfully")
                print("Names exported to CSV successfully")
            except Exception as e:
                logger.error(f"Error exporting names to CSV: {str(e)}")
                self.gui.update_status_bar(f"Error exporting names to CSV: {str(e)}")
                print(f"Error exporting names to CSV: {str(e)}")
        else:
            self.gui.update_status_bar("No HanLP analysis results to export")
            print("Error: No HanLP analysis results to export")

    def csv_to_names2(self, settings, name_length_range):
        print(f"Converting CSV to Names2 with settings: {settings} and name length range: {name_length_range}")
        if self.hanlp_analyzer:
            try:
                self.hanlp_analyzer.export_to_names2(settings, name_length_range)
                self.gui.update_status_bar(f"CSV data converted to Names2.txt successfully (settings: {settings}, name length range: {name_length_range})")
                print(f"CSV data converted to Names2.txt successfully (settings: {settings}, name length range: {name_length_range})")
            except Exception as e:
                logger.error(f"Error converting CSV to Names2: {str(e)}")
                self.gui.update_status_bar(f"Error converting CSV to Names2: {str(e)}")
                print(f"Error converting CSV to Names2: {str(e)}")
        else:
            self.gui.update_status_bar("No HanLP analysis results to convert")
            print("Error: No HanLP analysis results to convert")

    def tc_to_sc_conversion(self):
        print("Starting Traditional Chinese to Simplified Chinese conversion...")
        if not self.novel_path:
            self.gui.update_status_bar("No novel loaded for Traditional Chinese to Simplified Chinese conversion")
            print("Error: No novel loaded for Traditional Chinese to Simplified Chinese conversion")
            return

        try:
            novel_text, encoding = qt.read_novel_file(self.novel_path)
            converted_text = self.opencc_converter.convert(novel_text)
            
            output_filename = f"{os.path.splitext(os.path.basename(self.novel_path))[0]}_SC.txt"
            output_path = os.path.join(os.path.dirname(self.novel_path), output_filename)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(converted_text)
            
            self.gui.update_status_bar(f"Traditional Chinese to Simplified Chinese conversion completed. Saved as {output_filename}")
            print(f"Traditional Chinese to Simplified Chinese conversion completed. Saved as {output_filename}")
        except Exception as e:
            logger.error(f"Error during Traditional Chinese to Simplified Chinese conversion: {str(e)}")
            self.gui.update_status_bar(f"Error in Traditional Chinese to Simplified Chinese conversion: {str(e)}")
            print(f"Error during Traditional Chinese to Simplified Chinese conversion: {str(e)}")

    def update_ai_proofread_settings(self, new_settings):
        self.ai_proofreader.update_settings(new_settings)
        self.gui.update_status_bar("AI Proofread settings updated")
        if self.gui.ai_proofread_settings_gui:
            self.gui.ai_proofread_settings_gui.update_settings(new_settings)
        
        # Update GUI elements with new settings
        stats = self.ai_proofreader.get_stats()
        self.gui_update_queue.put(lambda: dpg.set_value("ai_proofread_tokens", f"Tokens: {stats['total_tokens']}"))
        self.gui_update_queue.put(lambda: dpg.set_value("ai_proofread_cost", f"Cost: ${stats['total_cost']:.2f}"))

    def update_ai_proofread_cache_percentage(self, percentage=None):
        if percentage is None and hasattr(self, 'ai_proofreader') and self.novel_path:
            percentage = self.ai_proofreader.get_cache_percentage(os.path.basename(self.novel_path))
        if percentage is not None:
            self.gui.update_ai_proofread_cache_percentage(percentage)

    def set_max_workers(self, workers: int):
        self.max_workers = max(1, min(workers, 16))  # Limit between 1 and 16 workers
        self.gui.update_status_bar(f"Max parallel processing threads set to {self.max_workers}")
        print(f"Max parallel processing threads set to {self.max_workers}")

    def process_gui_updates(self):
        try:
            while True:
                update_func = self.gui_update_queue.get_nowait()
                if callable(update_func):
                    try:
                        update_func()
                    except Exception as e:
                        logger.error(f"Error in GUI update function: {str(e)}")
        except queue.Empty:
            pass

    def run(self):
        print("Running QuickTranslatorGUI...")
        self.gui.create_gui()
        self.gui.load_fonts()
        self.gui.update_status(self.loading_info)
        
        dpg.set_primary_window("main_window", True)
        
        while dpg.is_dearpygui_running():
            self.process_gui_updates()
            dpg.render_dearpygui_frame()
        
        dpg.destroy_context()

if __name__ == "__main__":
    print("Starting QuickTranslatorGUI application...")
    gui = QuickTranslatorGUI()
    gui.run()
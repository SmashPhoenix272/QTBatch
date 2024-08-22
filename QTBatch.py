import time
import os
import threading
from typing import Dict, Any
import logging
import opencc

import QuickTranslator as qt
from gui import GUI
from name_analyzer import HanLPAnalyzer, CATEGORY_TRANSLATION
import dearpygui.dearpygui as dpg
import config
from utils import check_and_download_fonts, get_file_size_str, detect_chinese_script
from logging_config import setup_logging

logger = setup_logging()

class QuickTranslatorGUI:
    def __init__(self):
        print("Initializing QuickTranslatorGUI...")
        self.novel_path: str = ""
        self.loading_info: Dict[str, Dict[str, Any]] = {
            "names2": {"loaded": False, "count": 0, "time": 0},
            "names": {"loaded": False, "count": 0, "time": 0},
            "chinese_words": {"loaded": False, "count": 0, "time": 0},
            "viet_phrase": {"loaded": False, "count": 0, "time": 0}
        }
        self.conversion_running: bool = False
        self.stop_conversion: bool = False
        self.names2_reloaded = False

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

        # Start data loading in a separate thread
        self.data_loading_thread = threading.Thread(target=self.load_data_in_background)
        self.data_loading_thread.start()

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
            tc_to_sc_callback=self.tc_to_sc_conversion
        )
        print("QuickTranslatorGUI initialized.")

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
            novel_text, encoding = qt.read_novel_file(self.novel_path)
            novel_name = os.path.basename(self.novel_path)
            size_str = get_file_size_str(self.novel_path)
            chinese_form = detect_chinese_script(novel_text[:1000])  # Detect script using the first 1000 characters
            self.gui.update_novel_status(novel_name, encoding, size_str, chinese_form)
            self.gui.update_novel_preview(novel_text[:150])
            self.gui.update_conversion_status(f"Not started", (255, 165, 0))
            self.gui.update_conversion_time("")
            self.gui.update_conversion_progress(0.0)
            self.gui.update_conversion_percent(0.0, (220, 220, 220))
            self.gui.update_status_bar(f"Novel loaded: {novel_name}.")
            self.gui.update_conversion_preview(novel_text[:150])

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

    def start_conversion(self):
        print("Starting conversion...")
        if not self.data_loading_thread.is_alive() and self.loading_info["viet_phrase"]["loaded"]:
            if not self.novel_path:
                self.gui.update_conversion_status("No novel selected")
                print("Error: No novel selected")
                return

            self.conversion_running = False
            self.stop_conversion = False

            if self.conversion_running:
                return

            self.conversion_running = True
            self.gui.update_conversion_status("Running", (0, 255, 0))
            threading.Thread(target=self.run_conversion).start()
        else:
            self.gui.update_conversion_status("Waiting for data to load")
            print("Waiting for data to load")

    def run_conversion(self):
        print("Running conversion...")
        start_time = time.time()
        try:
            novel_text, encoding = qt.read_novel_file(self.novel_path)

            def progress_callback(progress):
                if self.stop_conversion:
                    return True  # Signal to stop the conversion
                self.gui.update_conversion_progress(progress)
                self.gui.update_conversion_percent(progress)
                return False  # Continue the conversion

            converted_text = qt.process_novel(novel_text, self.names2, self.names, self.viet_phrase, self.chinese_phien_am, progress_callback)

            if not self.stop_conversion:
                converted_filename = qt.convert_filename(os.path.basename(self.novel_path), self.names2, self.names, self.viet_phrase, self.chinese_phien_am)
                output_path = os.path.join(os.path.dirname(self.novel_path), converted_filename)

                try:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(converted_text)
                except OSError as e:
                    short_name = f"Converted_Novel_{int(time.time())}.txt"
                    output_path = os.path.join(os.path.dirname(self.novel_path), short_name)
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(converted_text)
                    logger.warning(f"Used shortened filename due to error: {e}")

                end_time = time.time()
                conversion_time = end_time - start_time

                self.gui.update_conversion_status(f"Complete. Saved as {os.path.basename(output_path)}", (0, 255, 0))
                self.gui.update_conversion_time(conversion_time)
                print(f"Conversion completed. Saved as {os.path.basename(output_path)}")
            else:
                self.gui.update_conversion_status(f"Stopped", (255, 0, 0))
                current_percentage = dpg.get_value("conversion_percentage")
                self.gui.update_conversion_percent(float(current_percentage[:-1]) / 100, color=(255, 0, 0))
                print("Conversion stopped")
        except Exception as e:
            logger.error(f"Error during conversion: {str(e)}")
            self.gui.update_conversion_status(f"Error - {str(e)}", (255, 0, 0))
            print(f"Error during conversion: {str(e)}")
        finally:
            self.conversion_running = False

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

        self.hanlp_running = True
        self.hanlp_thread = threading.Thread(target=self.run_hanlp_analysis)
        self.hanlp_thread.start()
        self.gui.update_status_bar("HanLP analysis started")

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
            self.hanlp_analyzer.analyze(progress_callback=progress_callback)
            
            if not self.hanlp_analyzer.is_stopped:
                self.gui.update_status_bar("HanLP analysis completed")
                print("HanLP analysis completed")
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

    def csv_to_names2(self, minimum_appearances: int):
        print(f"Converting CSV to Names2 with minimum appearances: {minimum_appearances}")
        if self.hanlp_analyzer:
            try:
                self.hanlp_analyzer.export_to_names2(minimum_appearances)
                self.gui.update_status_bar(f"CSV data converted to Names2.txt successfully (min appearances: {minimum_appearances})")
                print(f"CSV data converted to Names2.txt successfully (min appearances: {minimum_appearances})")
            except Exception as e:
                logger.error(f"Error converting CSV to Names2: {str(e)}")
                self.gui.update_status_bar(f"Error converting CSV to Names2: {str(e)}")
                print(f"Error converting CSV to Names2: {str(e)}")
        else:
            self.gui.update_status_bar("No HanLP analysis results to convert")
            print("Error: No HanLP analysis results to convert")

    def tc_to_sc_conversion(self):
        print("Starting TC to SC conversion...")
        if not self.novel_path:
            self.gui.update_status_bar("No novel loaded for TC to SC conversion")
            print("Error: No novel loaded for TC to SC conversion")
            return

        try:
            novel_text, encoding = qt.read_novel_file(self.novel_path)
            converted_text = self.opencc_converter.convert(novel_text)
            
            output_filename = f"{os.path.splitext(os.path.basename(self.novel_path))[0]}_SC.txt"
            output_path = os.path.join(os.path.dirname(self.novel_path), output_filename)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(converted_text)
            
            self.gui.update_status_bar(f"TC to SC conversion completed. Saved as {output_filename}")
            print(f"TC to SC conversion completed. Saved as {output_filename}")
        except Exception as e:
            logger.error(f"Error during TC to SC conversion: {str(e)}")
            self.gui.update_status_bar(f"Error in TC to SC conversion: {str(e)}")
            print(f"Error during TC to SC conversion: {str(e)}")

    def run(self):
        print("Running QuickTranslatorGUI...")
        self.gui.create_gui()
        self.gui.load_fonts()
        self.gui.update_status(self.loading_info)
        self.gui.run()

if __name__ == "__main__":
    print("Starting QuickTranslatorGUI application...")
    gui = QuickTranslatorGUI()
    gui.run()
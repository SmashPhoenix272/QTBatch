import time
import os
import threading
from typing import Dict, Any
import logging

import QuickTranslator as qt
from gui import GUI
import dearpygui.dearpygui as dpg
import config
from utils import check_and_download_fonts, get_file_size_str
from logging_config import setup_logging

logger = setup_logging()

class QuickTranslatorGUI:
    def __init__(self):
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
            stop_conversion_callback=lambda: setattr(self, 'stop_conversion', True)
        )

    def load_data_in_background(self):
        self.names2, self.names, self.viet_phrase, self.chinese_phien_am, self.loading_info = qt.load_data()
        # Verify 'chinese_words' data
        if 'chinese_words' in self.loading_info:
            logging.info(f"Chinese words loaded: {self.loading_info['chinese_words']}")
        else:
            logging.warning("Chinese words data not found in loading_info")
        self.gui.update_status(self.loading_info)

    def load_novel(self, sender: Any, app_data: Dict[str, Any]):
        if 'file_path_name' not in app_data or not app_data['file_path_name']:
            logger.warning("No file selected or invalid file path")
            self.gui.update_novel_status("No file selected", "N/A", "N/A")
            return

        self.novel_path = app_data['file_path_name']
    
        if not os.path.exists(self.novel_path):
            logger.error(f"File not found: {self.novel_path}")
            self.gui.update_novel_status(f"Error: File not found", "N/A", "N/A", color=self.gui.colors["error"])
            return

        try:
            novel_text, encoding = qt.read_novel_file(self.novel_path)
            novel_name = os.path.basename(self.novel_path)
            size_str = get_file_size_str(self.novel_path)
            self.gui.update_novel_status(novel_name, encoding, size_str)
            self.gui.update_novel_preview(novel_text[:100])
            self.gui.update_conversion_status(f"Not started", (255, 165, 0))
            self.gui.update_conversion_time("")
            self.gui.update_conversion_progress(0.0)
            self.gui.update_conversion_percent(0.0, (220, 220, 220))
            self.gui.update_status_bar(f"Novel loaded: {novel_name}.")
        except ValueError as e:
            logger.error(f"Error loading novel: {str(e)}")
            self.gui.update_novel_status(f"Error: {str(e)}", "N/A", "N/A", color=self.gui.colors["error"])

    def reload_names2(self):
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
            self.gui.names2_reloaded = True  # Set the flag to indicate Names2 has been reloaded
            self.gui.update_status(self.loading_info)
        except FileNotFoundError:
            logger.warning("Names2.txt not found. Unable to reload.")
            self.gui.update_status({"names2": {"loaded": False, "count": 0, "time": 0}})
        finally:
            dpg.render_dearpygui_frame()  # Force an immediate update of the GUI

    def start_conversion(self):
        if not self.data_loading_thread.is_alive() and self.loading_info["viet_phrase"]["loaded"]:
            if not self.novel_path:
                self.gui.update_conversion_status("No novel selected")
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

    def run_conversion(self):
        start_time = time.time()
        try:
            novel_text, encoding = qt.read_novel_file(self.novel_path)
            paragraphs = novel_text.split('\n')
            converted_paragraphs = []

            for i, paragraph in enumerate(paragraphs):
                if self.stop_conversion:
                    break

                converted = qt.process_paragraph(paragraph, self.names2, self.names, self.viet_phrase, self.chinese_phien_am)
                converted_paragraphs.append(converted)

                progress = (i + 1) / len(paragraphs)
                self.gui.update_conversion_progress(progress)
                self.gui.update_conversion_percent(progress)

            if not self.stop_conversion:
                final_text = '\n'.join(converted_paragraphs)
                converted_filename = qt.convert_filename(os.path.basename(self.novel_path), self.names2, self.names, self.viet_phrase, self.chinese_phien_am)
                output_path = os.path.join(os.path.dirname(self.novel_path), converted_filename)

                try:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(final_text)
                except OSError as e:
                    short_name = f"Converted_Novel_{int(time.time())}.txt"
                    output_path = os.path.join(os.path.dirname(self.novel_path), short_name)
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(final_text)
                    logger.warning(f"Used shortened filename due to error: {e}")

                end_time = time.time()
                conversion_time = end_time - start_time

                self.gui.update_conversion_status(f"Complete. Saved as {os.path.basename(output_path)}", (0, 255, 0))
                self.gui.update_conversion_time(conversion_time)
            else:
                self.gui.update_conversion_status(f"Stopped",(255, 0, 0))
                current_percentage = dpg.get_value("conversion_percentage")
                self.gui.update_conversion_percent(float(current_percentage[:-1]) / 100, color=(255, 0, 0))
        except Exception as e:
            logger.error(f"Error during conversion: {str(e)}")
            self.gui.update_conversion_status(f"Error - {str(e)}", (255, 0, 0))
        finally:
            self.conversion_running = False

    def run(self):
        self.gui.create_gui()
        self.gui.load_fonts()
        self.gui.update_status(self.loading_info)
        self.gui.run()

if __name__ == "__main__":
    gui = QuickTranslatorGUI()
    gui.run()
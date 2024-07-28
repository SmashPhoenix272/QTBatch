import dearpygui.dearpygui as dpg
import QuickTranslator as qt
import time
import logging
import os
import threading
import requests
import shutil

class QuickTranslatorGUI:
    def __init__(self):
        self.novel_path = ""
        self.loading_info = {
            "names2": {"loaded": False, "count": 0, "time": 0},
            "names": {"loaded": False, "count": 0, "time": 0},
            "chinese_words": {"loaded": False, "count": 0, "time": 0},
            "viet_phrase": {"loaded": False, "count": 0, "time": 0}
        }
        self.conversion_running = False
        self.stop_conversion = False
        self.chinese_font_loaded = False
        self.vietnamese_font_loaded = False
        self.font_dir = "font"
        self.chinese_font_path = os.path.join(self.font_dir, "NotoSansSC-Medium.ttf")
        self.vietnamese_font_path = os.path.join(self.font_dir, "Montserrat-Medium.ttf")
        self.chinese_font_url = "https://github.com/SmashPhoenix272/Fonts/raw/main/font/NotoSansSC-Medium.ttf"
        self.vietnamese_font_url = "https://github.com/SmashPhoenix272/Fonts/raw/main/font/Montserrat-Medium.ttf"
        self.check_and_download_fonts()
    
        # Start data loading in a separate thread
        self.data_loading_thread = threading.Thread(target=self.load_data_in_background)
        self.data_loading_thread.start()
        
    def load_data_in_background(self):
        self.names2, self.names, self.viet_phrase, self.chinese_phien_am, self.loading_info = qt.load_data()
        self.update_status()

    def check_and_download_fonts(self):
        if not os.path.exists(self.font_dir):
            os.makedirs(self.font_dir)
    
        fonts = [
            (self.chinese_font_path, self.chinese_font_url, "Chinese"),
            (self.vietnamese_font_path, self.vietnamese_font_url, "Vietnamese")
        ]
    
        for font_path, font_url, font_name in fonts:
            if not os.path.exists(font_path):
                print(f"{font_name} font not found. Downloading...")
                try:
                    response = requests.get(font_url, stream=True)
                    response.raise_for_status()
                    with open(font_path, 'wb') as out_file:
                        shutil.copyfileobj(response.raw, out_file)
                    print(f"{font_name} font downloaded successfully.")
                except Exception as e:
                    print(f"Error downloading {font_name} font: {str(e)}")
            else:
                print(f"{font_name} font found.")

    def load_novel(self, sender, app_data):
        self.novel_path = app_data['file_path_name']
        try:
            novel_text, encoding = qt.read_novel_file(self.novel_path)
            novel_name = os.path.basename(self.novel_path)
    
            # Get file size
            file_size = os.path.getsize(self.novel_path)
    
            # Convert file size to appropriate unit
            if file_size < 1024:
                size_str = f"{file_size} bytes"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.2f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.2f} MB"
    
            dpg.set_value("novel_status", f"Novel: {novel_name} (Loaded, Encoding: {encoding}, Size: {size_str})")
            dpg.configure_item("novel_status", color=(0, 255, 0))
    
            # Display a preview of the novel text
            preview = novel_text[:50]  # First 50 characters
            dpg.set_value("novel_preview", f"Preview: {preview}")
        
            # Reset conversion status and progress
            dpg.set_value("conversion_status", "Conversion: Not started")
            dpg.configure_item("conversion_status", color=(255, 255, 0))  # Yellow color
            dpg.set_value("conversion_time", "")
            dpg.set_value("conversion_progress", 0.0)
        
        except ValueError as e:
            dpg.set_value("novel_status", f"Error: {str(e)}")
            dpg.configure_item("novel_status", color=(255, 0, 0))

    def reload_names2(self):
        start_time = time.time()
        try:
            with open('Names2.txt', 'r', encoding='utf-8') as f:
                name2_entries = []
                for line in f:
                    parts = line.strip().split('=')
                    if len(parts) == 2:
                        name2_entries.append((parts[0], parts[1]))
        
            self.names2 = qt.Trie()
            self.names2.batch_insert(name2_entries)
        
            self.loading_info["names2"]["loaded"] = True
            self.loading_info["names2"]["count"] = self.names2.count()
            self.loading_info["names2"]["time"] = time.time() - start_time
        
            logging.info(f"Reloaded {self.names2.count()} names from Names2.txt in {self.loading_info['names2']['time']:.2f} seconds")
        
            self.update_status()
            dpg.set_value("names2_status", "Names2.txt: Reloaded")
            dpg.configure_item("names2_status", color=(0, 255, 0))
        except FileNotFoundError:
            logging.warning("Names2.txt not found. Unable to reload.")
            dpg.set_value("names2_status", "Names2.txt: Not found")
            dpg.configure_item("names2_status", color=(255, 0, 0))

    def start_conversion(self):
        if not self.data_loading_thread.is_alive() and self.loading_info["viet_phrase"]["loaded"]:
            if not self.novel_path:
                dpg.set_value("conversion_status", "Conversion: No novel selected")
                return
        
            # Reset conversion state
            self.conversion_running = False
            self.stop_conversion = False
        
            if self.conversion_running:
                return
        
            self.conversion_running = True
            dpg.set_value("conversion_status", "Conversion: Running")
            dpg.configure_item("conversion_status", color=(0, 255, 0))
            threading.Thread(target=self.run_conversion).start()
        else:
            dpg.set_value("conversion_status", "Conversion: Waiting for data to load")
        
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
                dpg.set_value("conversion_progress", progress)

            if not self.stop_conversion:
                final_text = '\n'.join(converted_paragraphs)
                converted_filename = qt.convert_filename(os.path.basename(self.novel_path), self.names2, self.names, self.viet_phrase, self.chinese_phien_am)
                output_path = os.path.join(os.path.dirname(self.novel_path), converted_filename)
            
                try:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(final_text)
                except OSError as e:
                    # If we encounter a filesystem error, try a shorter filename
                    short_name = f"Converted_Novel_{int(time.time())}.txt"
                    output_path = os.path.join(os.path.dirname(self.novel_path), short_name)
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(final_text)
                    logging.warning(f"Used shortened filename due to error: {e}")

                end_time = time.time()
                conversion_time = end_time - start_time
            
                dpg.set_value("conversion_status", f"Conversion: Complete. Saved as {os.path.basename(output_path)}")
                dpg.set_value("conversion_time", f"Time taken: {conversion_time:.2f} seconds")
                dpg.configure_item("conversion_time", color=(0, 255, 0))
            else:
                dpg.set_value("conversion_status", "Conversion: Stopped")
                dpg.set_value("conversion_time", "")
        except Exception as e:
            dpg.set_value("conversion_status", f"Conversion: Error - {str(e)}")
            dpg.set_value("conversion_time", "")
        finally:
            self.conversion_running = False

    def update_status(self):
        names2_status = dpg.get_value("names2_status")
        if names2_status != "Names2.txt: Reloaded":
            dpg.set_value("names2_status", f"Names2.txt: {'Loaded' if self.loading_info['names2']['loaded'] else 'Not loaded. Please Wait!'}")
        dpg.configure_item("names2_status", color=(0, 255, 0) if self.loading_info['names2']['loaded'] else (255, 0, 0))
    
        if self.loading_info['names2']['loaded']:
            dpg.set_value("names2_count", f"Names2 loaded: {self.loading_info['names2']['count']}")
            dpg.set_value("names2_time", f"Loading time: {self.loading_info['names2']['time']:.2f} seconds")
            
        dpg.set_value("names_status", f"Names.txt: {'Loaded' if self.loading_info['names']['loaded'] else 'Not loaded. Please Wait!'}")
        dpg.configure_item("names_status", color=(0, 255, 0) if self.loading_info['names']['loaded'] else (255, 0, 0))
        if self.loading_info['names']['loaded']:
            dpg.set_value("names_count", f"Names loaded: {self.loading_info['names']['count']}")
            dpg.set_value("names_time", f"Loading time: {self.loading_info['names']['time']:.2f} seconds")

        dpg.set_value("chinese_words_status", f"ChinesePhienAmWords.txt: {'Loaded' if self.loading_info['chinese_words']['loaded'] else 'Not loaded. Please Wait!'}")
        dpg.configure_item("chinese_words_status", color=(0, 255, 0) if self.loading_info['chinese_words']['loaded'] else (255, 0, 0))
        if self.loading_info['chinese_words']['loaded']:
            dpg.set_value("chinese_words_count", f"Chinese words loaded: {self.loading_info['chinese_words']['count']}")

        dpg.set_value("viet_phrase_status", f"VietPhrase.txt: {'Loaded' if self.loading_info['viet_phrase']['loaded'] else 'Not loaded. Please Wait!'}")
        dpg.configure_item("viet_phrase_status", color=(0, 255, 0) if self.loading_info['viet_phrase']['loaded'] else (255, 0, 0))
        if self.loading_info['viet_phrase']['loaded']:
            dpg.set_value("viet_phrase_count", f"VietPhrase entries loaded: {self.loading_info['viet_phrase']['count']}")
            dpg.set_value("viet_phrase_time", f"Loading time: {self.loading_info['viet_phrase']['time']:.2f} seconds")

    def create_gui(self):
        dpg.create_context()
        self.check_and_download_fonts()

        # Create main window
        with dpg.window(label="QuickTranslator Batch", tag="main_window", width=400, height=500):
        
            # QTBatch controls
            dpg.add_button(label="Load Novel", callback=lambda: dpg.show_item("file_dialog_id"))
            dpg.add_button(label="Reload Names2", callback=lambda: self.reload_names2())
            dpg.add_button(label="Start Conversion", callback=lambda: self.start_conversion())
            dpg.add_button(label="Stop Conversion", callback=lambda: setattr(self, 'stop_conversion', True))
    
            # Status window as a child of the main window
            with dpg.child_window(label="Status", height=725, border=True):
                dpg.add_text("Names2.txt: ", tag="names2_status")
                dpg.add_text("", tag="names2_count")
                dpg.add_text("", tag="names2_time")
                dpg.add_text("Names.txt: ", tag="names_status")
                dpg.add_text("", tag="names_count")
                dpg.add_text("", tag="names_time")
                dpg.add_text("ChinesePhienAmWords.txt: ", tag="chinese_words_status")
                dpg.add_text("", tag="chinese_words_count")
                dpg.add_text("VietPhrase.txt: ", tag="viet_phrase_status")
                dpg.add_text("", tag="viet_phrase_count")
                dpg.add_text("", tag="viet_phrase_time")
                dpg.add_text("Novel: Not loaded", tag="novel_status")
                dpg.add_text("", tag="novel_preview", wrap=300)
                dpg.add_text("Conversion: Not started", tag="conversion_status")
                dpg.add_text("", tag="conversion_time")
                dpg.add_progress_bar(label="Conversion Progress", width=-1, tag="conversion_progress")

        with dpg.file_dialog(directory_selector=False, show=False, callback=lambda sender, app_data, user_data: self.load_novel(sender, app_data), tag="file_dialog_id"):
            dpg.add_file_extension(".txt", color=(255, 255, 0, 255))

        dpg.create_viewport(title="QuickTranslator Batch", width=710, height=905)

        # Load fonts
        self.load_fonts()

        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("main_window", True)

        self.update_status()

        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()

        dpg.destroy_context()

    def load_fonts(self):
        with dpg.font_registry():
            # Load Chinese font
            if os.path.exists(self.chinese_font_path):
                self.chinese_font = dpg.add_font(self.chinese_font_path, 20)
                dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Full, parent=self.chinese_font)
                self.chinese_font_loaded = True
            else:
                self.chinese_font_loaded = False
                logging.warning(f"Chinese font not found: {self.chinese_font_path}")

            # Load Vietnamese font
            if os.path.exists(self.vietnamese_font_path):
                self.vietnamese_font = dpg.add_font(self.vietnamese_font_path, 20)
                dpg.add_font_range_hint(dpg.mvFontRangeHint_Vietnamese, parent=self.vietnamese_font)
                self.vietnamese_font_loaded = True
            else:
                self.vietnamese_font_loaded = False
                logging.warning(f"Vietnamese font not found: {self.vietnamese_font_path}")

            # Create a fallback chain
            if self.chinese_font_loaded and self.vietnamese_font_loaded:
                dpg.add_font_range_hint(dpg.mvFontRangeHint_Vietnamese, parent=self.chinese_font)
                dpg.bind_font(self.chinese_font)
            elif self.chinese_font_loaded:
                dpg.bind_font(self.chinese_font)
            elif self.vietnamese_font_loaded:
                dpg.bind_font(self.vietnamese_font)
            else:
                logging.error("No fonts loaded. Using default font.")

    def show_output_filename(self, output_path):
        filename = os.path.basename(output_path)
        dpg.add_text(f"Saved as: {filename}", tag="output_filename", parent="main_window")

if __name__ == "__main__":
    gui = QuickTranslatorGUI()
    gui.create_gui()

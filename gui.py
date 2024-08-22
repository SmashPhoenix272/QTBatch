import os
import dearpygui.dearpygui as dpg
from typing import Callable
import config
import logging
import subprocess
import pywinstyles
import QuickTranslator as qt

class GUI:
    def __init__(self, load_novel_callback: Callable, reload_names2_callback: Callable,
                 start_conversion_callback: Callable, stop_conversion_callback: Callable,
                 start_hanlp_callback: Callable, stop_hanlp_callback: Callable,
                 pause_hanlp_callback: Callable, resume_hanlp_callback: Callable,
                 export_names_to_csv_callback: Callable, csv_to_names2_callback: Callable,
                 reanalyze_hanlp_callback: Callable, tc_to_sc_callback: Callable):
        self.load_novel_callback = load_novel_callback
        self.reload_names2_callback = reload_names2_callback
        self.start_conversion_callback = start_conversion_callback
        self.stop_conversion_callback = stop_conversion_callback
        self.start_hanlp_callback = start_hanlp_callback
        self.stop_hanlp_callback = stop_hanlp_callback
        self.pause_hanlp_callback = pause_hanlp_callback
        self.resume_hanlp_callback = resume_hanlp_callback
        self.export_names_to_csv_callback = export_names_to_csv_callback
        self.reanalyze_hanlp_callback = reanalyze_hanlp_callback
        self.csv_to_names2_callback = csv_to_names2_callback
        self.tc_to_sc_callback = tc_to_sc_callback
        self.names2_reloaded = False
        self.hanlp_paused = False
        self.min_appearances = 1
        self.conversion_data = None

    def create_gui(self):
        dpg.create_context()

        # Define color scheme
        self.colors = {
            "bg_primary": (30, 30, 30),
            "bg_secondary": (45, 45, 45),
            "text_primary": (220, 220, 220),
            "text_header": (255, 255, 255),
            "accent": (0, 120, 215),
            "success": (0, 200, 0),
            "warning": (255, 165, 0),
            "error": (255, 0, 0)
        }

        with dpg.theme() as global_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, self.colors["bg_primary"])
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, self.colors["bg_secondary"])
                dpg.add_theme_color(dpg.mvThemeCol_Text, self.colors["text_primary"])
                dpg.add_theme_color(dpg.mvThemeCol_Button, self.colors["accent"])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [c + 30 for c in self.colors["accent"]])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [c + 50 for c in self.colors["accent"]])
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 5)
                dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 5)

        dpg.bind_theme(global_theme)

        with dpg.window(label="QuickTranslator Batch", tag="main_window", width=1000, height=800):
            with dpg.menu_bar():
                with dpg.menu(label="File"):
                    dpg.add_menu_item(label="Load Novel", callback=lambda: dpg.show_item("file_dialog_id"), tag="load_novel_menu")
                    dpg.add_menu_item(label="Exit", callback=lambda: dpg.stop_dearpygui())
                with dpg.menu(label="Settings"):
                    dpg.add_menu_item(label="About", callback=self.show_about)

            with dpg.group(horizontal=True):
                with dpg.group():
                    with dpg.child_window(width=304, height=200):
                        self.add_data_status_window()
                    dpg.add_spacer(height=10)
                    with dpg.child_window(width=304, height=-35):
                        self.add_hanlp_analysis_window()

                with dpg.child_window(width=-1, height=-35):
                    with dpg.group():
                        with dpg.group(horizontal=True):
                            dpg.add_button(label="Load Novel", callback=lambda: dpg.show_item("file_dialog_id"), tag="load_novel_button")
                            dpg.add_button(label="Convert TC to SC", callback=lambda: self.tc_to_sc_callback(), tag="tc_to_sc_button")
                            dpg.add_button(label="Reload Names2", callback=lambda: self.reload_names2_callback(), tag="reload_names2_button")
                            dpg.add_button(label="Start Conversion", callback=lambda: self.start_conversion_callback(), tag="start_conversion_button")
                            dpg.add_button(label="Stop Conversion", callback=lambda: self.stop_conversion_callback(), tag="stop_conversion_button")
                    
                    dpg.add_separator()
                    dpg.add_text("Novel Status", color=self.colors["text_header"])
                    self.add_novel_status_tables()
                    
                    dpg.add_separator()
                    dpg.add_text("Novel Preview", color=self.colors["text_header"])
                    with dpg.child_window(height=135):
                        dpg.add_text("", tag="novel_preview", wrap=680)

                    dpg.add_separator()
                    dpg.add_text("Conversion Preview", color=self.colors["text_header"])
                    with dpg.child_window(height=135):
                        dpg.add_text("", tag="conversion_preview", wrap=680)
                    
                    dpg.add_separator()
                    dpg.add_text("Conversion Status", color=self.colors["text_header"])
                    dpg.add_text("Not started", tag="conversion_status")
                    dpg.add_text("", tag="conversion_time")
                    dpg.add_text("0%", tag="conversion_percentage", before="conversion_progress")
                    dpg.add_progress_bar(label="Conversion Progress", width=-1, tag="conversion_progress")

            # Add status bar
            with dpg.group(horizontal=True):
                dpg.add_text("Status: ", tag="status_bar_label")
                dpg.add_text("Ready", tag="status_bar_text")

        with dpg.file_dialog(directory_selector=False, show=False, callback=lambda sender, app_data: self.load_novel_callback(sender, app_data), tag="file_dialog_id"):
            dpg.add_file_extension(".txt", color=(255, 255, 0, 255))

        dpg.create_viewport(title="QuickTranslator Batch", width=1075, height=800)
        
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("main_window", True)

        self.add_tooltips()
        self.update_novel_status("", "", "", "")
        pywinstyles.apply_style("main_window","dark")

    def add_data_status_window(self):
        dpg.add_text("Data Status", color=self.colors["text_header"])
        dpg.add_separator()
        self.add_data_status_table()

    def add_hanlp_analysis_window(self):
        dpg.add_text("HanLP Name Analysis", color=self.colors["text_header"])
        dpg.add_separator()
        self.add_hanlp_analysis_section()

    def add_data_status_table(self):
        with dpg.table(header_row=True, borders_innerH=True, borders_outerH=True, borders_innerV=True, borders_outerV=True):
            dpg.add_table_column(label="Data", width_stretch=True, init_width_or_weight=2)
            dpg.add_table_column(label="Status", width_stretch=True, init_width_or_weight=1)
            dpg.add_table_column(label="Count", width_stretch=True, init_width_or_weight=1)
            dpg.add_table_column(label="Time", width_stretch=True, init_width_or_weight=1)

            for key in ["names2", "names", "chinese_words", "viet_phrase"]:
                with dpg.table_row():
                    dpg.add_text(key.capitalize())
                    dpg.add_text("Loading", tag=f"{key}_status")
                    dpg.add_text("", tag=f"{key}_count")
                    dpg.add_text("", tag=f"{key}_time")

    def add_hanlp_analysis_section(self):
        with dpg.group():
            with dpg.group(horizontal=True):
                dpg.add_button(label="Start", callback=lambda: self.start_hanlp_callback(), tag="start_hanlp_button")
                dpg.add_button(label="Stop", callback=lambda: self.stop_hanlp_callback(), tag="stop_hanlp_button")
                dpg.add_button(label="Pause/Resume", callback=lambda: self.toggle_pause_hanlp(), tag="pause_resume_hanlp_button")
                dpg.add_button(label="ReAnalyze", callback=lambda: self.reanalyze_hanlp_callback(), tag="reanalyze_hanlp_button")
             
            dpg.add_text("HanLP Progress", color=self.colors["text_header"])
            dpg.add_text("0%", tag="hanlp_percentage", before="hanlp_progress")
            dpg.add_progress_bar(label="HanLP Progress", width=-1, tag="hanlp_progress")
            dpg.add_text("Estimated time: N/A", tag="hanlp_estimated_time")

            dpg.add_text("Name Analyzing Status", color=self.colors["text_header"])
            self.add_name_analyzing_status_table()

            with dpg.group(horizontal=True):
                dpg.add_button(label="Export Names to CSV", callback=lambda: self.export_names_to_csv_callback(), tag="export_names_button")
                dpg.add_button(label="Open CSV File", callback=self.open_csv_file, tag="open_csv_button")
                dpg.add_spacer(height=10)
            
            with dpg.group():
                dpg.add_separator()
                dpg.add_input_int(label="Min Appearances", default_value=self.min_appearances, callback=lambda sender, app_data: self.update_min_appearances(sender, app_data), width=100, tag="min_appearances_input")
                dpg.add_button(label="CSV To Names2", callback=lambda: self.csv_to_names2_callback(self.min_appearances), tag="csv_to_names2_button")

    def add_name_analyzing_status_table(self):
        with dpg.table(header_row=True, borders_innerH=True, borders_outerH=True, borders_innerV=True, borders_outerV=True):
            dpg.add_table_column(label="Category", width_stretch=True)
            dpg.add_table_column(label="Count", width_stretch=True)

            for category in ['Person Name', 'Place Name', 'Organization Name']:
                with dpg.table_row():
                    dpg.add_text(category)
                    dpg.add_text("0", tag=f"{category.lower().replace(' ', '_')}_count")

    def add_novel_status_tables(self):
        # First table for Loaded File
        with dpg.table(header_row=False, borders_innerH=True, borders_outerH=True, borders_innerV=True, borders_outerV=True, tag="loaded_file_table"):
            dpg.add_table_column(width_fixed=True, init_width_or_weight=100)  # Adjust width as needed
            dpg.add_table_column(width_stretch=True)
            
            with dpg.table_row():
                dpg.add_text("Loaded File")
                dpg.add_text("", tag="loaded_file")

        dpg.add_spacer(height=5)  # Add some space between tables

        # Second table for Encoding, Size, and Form
        with dpg.table(header_row=False, borders_innerH=True, borders_outerH=True, borders_innerV=True, borders_outerV=True, tag="novel_info_table"):
            dpg.add_table_column(width_stretch=True, init_width_or_weight=0.5)  # Same width as first column of first table
            dpg.add_table_column(width_stretch=True, init_width_or_weight=0.5)
            dpg.add_table_column(width_stretch=True, init_width_or_weight=0.5)
            
            with dpg.table_row():
                dpg.add_text("Encoding")
                dpg.add_text("Size")
                dpg.add_text("Form")
            
            with dpg.table_row():
                dpg.add_text("", tag="encoding")
                dpg.add_text("", tag="size")
                dpg.add_text("", tag="chinese_form")

    def add_tooltips(self):
        tooltips = [
            ("load_novel_button", "Click to load a novel file"),
            ("load_novel_menu", "Click to load a novel file"),
            ("reload_names2_button", "Click to reload Names2 data"),
            ("start_conversion_button", "Click to start the conversion process"),
            ("stop_conversion_button", "Click to stop the ongoing conversion"),
            ("tc_to_sc_button", "Click to convert Traditional Chinese to Simplified Chinese"),
            ("conversion_progress", "Shows the progress of the current conversion"),
            ("start_hanlp_button", "Click to start HanLP name analysis"),
            ("stop_hanlp_button", "Click to stop HanLP name analysis"),
            ("pause_resume_hanlp_button", "Click to pause or resume HanLP name analysis"),
            ("reanalyze_hanlp_button", "Click to reset cache and start a new HanLP analysis"),
            ("hanlp_progress", "Shows the progress of HanLP name analysis"),
            ("export_names_button", "Click to export analyzed names to CSV"),
            ("open_csv_button", "Click to open the exported CSV file"),
            ("csv_to_names2_button", "Click to convert CSV data to Names2.txt"),
            ("min_appearances_input", "Set the minimum number of appearances for a name to be included in Names2.txt")
        ]

        for tag, text in tooltips:
            try:
                if dpg.does_item_exist(tag):
                    with dpg.tooltip(tag):
                        dpg.add_text(text)
                else:
                    logging.warning(f"Item with tag '{tag}' does not exist. Skipping tooltip.")
            except Exception as e:
                logging.error(f"Error adding tooltip for {tag}: {str(e)}")

    def load_fonts(self):
        with dpg.font_registry():
            chinese_font_loaded = False
            vietnamese_font_loaded = False

            if os.path.exists(config.CHINESE_FONT_PATH):
                chinese_font = dpg.add_font(config.CHINESE_FONT_PATH, config.FONT_SIZE)
                dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Full, parent=chinese_font)
                chinese_font_loaded = True
            else:
                logging.warning(f"Chinese font not found: {config.CHINESE_FONT_PATH}")

            if os.path.exists(config.VIETNAMESE_FONT_PATH):
                vietnamese_font = dpg.add_font(config.VIETNAMESE_FONT_PATH, config.FONT_SIZE)
                dpg.add_font_range_hint(dpg.mvFontRangeHint_Vietnamese, parent=vietnamese_font)
                vietnamese_font_loaded = True
            else:
                logging.warning(f"Vietnamese font not found: {config.VIETNAMESE_FONT_PATH}")

            if chinese_font_loaded and vietnamese_font_loaded:
                dpg.add_font_range_hint(dpg.mvFontRangeHint_Vietnamese, parent=chinese_font)
                dpg.bind_font(chinese_font)
            elif chinese_font_loaded:
                dpg.bind_font(chinese_font)
            elif vietnamese_font_loaded:
                dpg.bind_font(vietnamese_font)
            else:
                logging.error("No fonts loaded. Using default font.")

    def run(self):
        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()
        dpg.destroy_context()

    def update_status(self, loading_info):
        for key, info in loading_info.items():
            self._update_status_item(key, info)

    def _update_status_item(self, key, info):
        try:
            status_text = "Loaded" if info['loaded'] else "Not loaded"
            if key == "names2" and hasattr(self, 'names2_reloaded') and self.names2_reloaded:
                status_text = "Reloaded"

            status_color = self.colors["success"] if info['loaded'] else self.colors["error"]
            
            dpg.set_value(f"{key}_status", status_text)
            dpg.configure_item(f"{key}_status", color=status_color)

            if info['loaded']:
                dpg.set_value(f"{key}_count", f"{info['count']}")
                if 'time' in info:
                    dpg.set_value(f"{key}_time", f"{info['time']:.2f}s")

            self.update_status_bar(f"{key.capitalize()} {status_text}")
        except Exception as e:
            logging.error(f"Error updating {key}: {str(e)}")
            logging.error(f"Info for {key}: {info}")

    def update_novel_status(self, novel_name: str, encoding: str, size_str: str, chinese_form: str):
        dpg.set_value("loaded_file", novel_name)
        dpg.set_value("encoding", encoding)
        dpg.set_value("size", size_str)
        dpg.set_value("chinese_form", chinese_form)
        self.update_status_bar(f"Novel loaded: {novel_name}")

    def update_novel_preview(self, preview: str):
        dpg.set_value("novel_preview", preview)

    def update_conversion_preview(self, preview: str):
        # Process the preview text using the same workflow as QuickTranslator.py
        processed_preview = self.process_preview_text(preview)
        dpg.set_value("conversion_preview", processed_preview)

    def process_preview_text(self, text: str) -> str:
        names2, names, viet_phrase, chinese_phien_am = self.get_conversion_data()
        
        # Split the text into paragraphs
        paragraphs = text.split('\n')
        
        # Process each paragraph
        processed_paragraphs = []
        for paragraph in paragraphs:
            if paragraph.strip():  # Skip empty paragraphs
                converted = qt.process_paragraph(paragraph, names2, names, viet_phrase, chinese_phien_am)
                processed_paragraphs.append(converted)
        
        # Join the processed paragraphs with line breaks
        return '\n'.join(processed_paragraphs)

    def get_conversion_data(self):
        if self.conversion_data is None:
            raise ValueError("Conversion data not set. Make sure to call set_conversion_data() first.")
        return self.conversion_data

    def set_conversion_data(self, names2, names, viet_phrase, chinese_phien_am):
        self.conversion_data = (names2, names, viet_phrase, chinese_phien_am)

    def update_conversion_status(self, status: str, color: tuple = None):
        dpg.set_value("conversion_status", status)
        if color:
            dpg.configure_item("conversion_status", color=color)
        self.update_status_bar(f"Conversion: {status}")

    def update_conversion_progress(self, progress: float):
        dpg.set_value("conversion_progress", progress)
        
    def update_conversion_percent(self, progress: float, color: tuple = None):
        percentage = progress * 100
        dpg.set_value("conversion_percentage", f"{percentage:.2f}%")
        if color:
            dpg.configure_item("conversion_percentage", color=color)
        else:
            dpg.configure_item("conversion_percentage", color=self.colors["success"])

    def update_conversion_time(self, time: float):
        if time:
            dpg.set_value("conversion_time", f"Time taken: {time:.2f} seconds")
            dpg.configure_item("conversion_time", color=self.colors["success"])
        else:
            dpg.set_value("conversion_time", "")

    def update_hanlp_progress(self, progress: float):
        dpg.set_value("hanlp_progress", progress)
        percentage = progress * 100
        dpg.set_value("hanlp_percentage", f"{percentage:.2f}%")

    def update_hanlp_estimated_time(self, estimated_time: float):
        dpg.set_value("hanlp_estimated_time", f"Estimated time: {estimated_time:.2f} seconds")

    def update_name_analyzing_status(self, status: dict):
        for category, count in status.items():
            tag = f"{category.lower().replace(' ', '_')}_count"
            if dpg.does_item_exist(tag):
                dpg.set_value(tag, str(count))
            else:
                logging.warning(f"Tag '{tag}' does not exist for category '{category}'")

    def toggle_pause_hanlp(self):
        if self.hanlp_paused:
            self.resume_hanlp_callback()
            self.hanlp_paused = False
            dpg.configure_item("pause_resume_hanlp_button", label="Pause HanLP")
        else:
            self.pause_hanlp_callback()
            self.hanlp_paused = True
            dpg.configure_item("pause_resume_hanlp_button", label="Resume HanLP")

    def open_csv_file(self):
        try:
            subprocess.Popen(['start', 'AnalyzedNames.csv'], shell=True)
        except Exception as e:
            logging.error(f"Error opening CSV file: {str(e)}")
            self.update_status_bar("Error opening CSV file")

    def update_status_bar(self, message: str):
        dpg.set_value("status_bar_text", message)

    def show_about(self):
        with dpg.window(label="About", modal=True, width=400, height=200):
            dpg.add_text("QuickTranslator Batch Ver 2.5.0")
            dpg.add_text("Created thanks to Perplexity.ai + Claude.ai")
            dpg.add_text("Source: https://github.com/SmashPhoenix272/QTBatch")
            dpg.add_button(label="Close", callback=lambda: dpg.delete_item(dpg.get_item_parent(dpg.last_item())))

    def update_min_appearances(self, sender, app_data):
        self.min_appearances = app_data
        self.update_status_bar(f"Minimum appearances set to {self.min_appearances}")
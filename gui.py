import os
import dearpygui.dearpygui as dpg
from typing import Callable
import config
import logging
import QuickTranslator as qt
import pywinstyles
from detect_chapters_methods import CHAPTER_MATCHERS
from utils import detect_chapters
from name_analyzer import CATEGORY_TRANSLATION
from gui_utils import process_preview_text, open_csv_file, safe_callback
from gui_updates import GUIUpdater
from gui_dialogs import show_about, show_progress_dialog, close_progress_dialog, show_error_dialog
from ai_proofread import AIProofreader
from gui_ai_proofread import create_ai_proofread_settings_gui
from export_names2_settings_gui import create_export_names2_settings_gui

class GUI:
    def __init__(self, load_novel_callback: Callable, reload_names2_callback: Callable,
                 start_conversion_callback: Callable, stop_conversion_callback: Callable,
                 start_hanlp_callback: Callable, stop_hanlp_callback: Callable,
                 pause_hanlp_callback: Callable, resume_hanlp_callback: Callable,
                 export_names_to_csv_callback: Callable, csv_to_names2_callback: Callable,
                 reanalyze_hanlp_callback: Callable, tc_to_sc_callback: Callable,
                 chapter_range_callback: Callable, pause_conversion_callback: Callable,
                 resume_conversion_callback: Callable, set_max_workers_callback: Callable):
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
        self.chapter_range_callback = chapter_range_callback
        self.pause_conversion_callback = pause_conversion_callback
        self.resume_conversion_callback = resume_conversion_callback
        self.set_max_workers_callback = set_max_workers_callback
        self.csv_to_names2_callback = lambda: csv_to_names2_callback(self.export_names2_settings, self.name_length_range)
        self.export_names2_settings_gui = None
        self.export_names2_settings = {
            "Person Name": 1,
            "Place Name": 1,
            "Organization Name": 1
        }
        self.name_length_range = (1, 4)
        self.names2_reloaded = False
        self.hanlp_paused = False
        self.conversion_paused = False
        self.export_names2_settings_gui = None
        self.conversion_data = None
        self.advanced_options_visible = False
        self.detect_chapters = False
        self.current_detect_method = list(CHAPTER_MATCHERS.keys())[0]  # Set default to first method
        self.chapter_detection_settings_window = None
        self.detected_chapters = 0
        self.start_chapter = 1
        self.end_chapter = 999999
        self.chapter_range_applied = False
        self.novel_text = ""
        self.export_filename = ""
        self.novel_path = ""
        self.ai_proofreader = AIProofreader(self, self.update_ai_proofread_settings)
        self.ai_proofread_enabled = False
        self.ai_proofread_settings_gui = None
        self.max_workers = 4

    def create_gui(self):
        dpg.create_context()

        # Define color scheme
        self.colors = {
            "bg_primary": (30, 30, 30),
            "bg_secondary": (45, 45, 45),
            "text_primary": (220, 220, 220),
            "text_header": (195, 145, 255),
            "accent": (0, 120, 215),
            "success": (0, 200, 0),
            "warning": (255, 165, 0),
            "error": (255, 0, 0),
            "input_bg": (60, 60, 60),
            "input_border": (100, 100, 100)
        }

        self.gui_updater = GUIUpdater(self.colors)

        with dpg.theme() as global_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, self.colors["bg_primary"])
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, self.colors["bg_secondary"])
                dpg.add_theme_color(dpg.mvThemeCol_Text, self.colors["text_primary"])
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 5)
                dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 5)

            # Button theme
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, self.colors["accent"])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [c + 30 for c in self.colors["accent"]])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [c + 50 for c in self.colors["accent"]])

            # Input box theme
            for component in [dpg.mvInputInt, dpg.mvInputFloat, dpg.mvInputText]:
                with dpg.theme_component(component):
                    dpg.add_theme_color(dpg.mvThemeCol_FrameBg, self.colors["input_bg"])
                    dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, [c + 20 for c in self.colors["input_bg"]])
                    dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, [c + 40 for c in self.colors["input_bg"]])
                    dpg.add_theme_color(dpg.mvThemeCol_Border, self.colors["input_border"])
                    dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)

            # Checkbox theme
            with dpg.theme_component(dpg.mvCheckbox):
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, self.colors["input_bg"])
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, [c + 20 for c in self.colors["input_bg"]])
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, [c + 40 for c in self.colors["input_bg"]])
                dpg.add_theme_color(dpg.mvThemeCol_Border, self.colors["input_border"])
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
                dpg.add_theme_color(dpg.mvThemeCol_CheckMark, self.colors["accent"])

        dpg.bind_theme(global_theme)

        with dpg.window(label="QuickTranslator Batch", tag="main_window", width=1204, height=800):
            with dpg.menu_bar():
                with dpg.menu(label="File"):
                    dpg.add_menu_item(label="Load Novel", callback=lambda: dpg.show_item("file_dialog_id"), tag="load_novel_menu")
                    dpg.add_menu_item(label="Exit", callback=lambda: dpg.stop_dearpygui())
                with dpg.menu(label="FAQ"):
                    dpg.add_menu_item(label="About", callback=lambda: show_about())

            with dpg.group(horizontal=True):
                with dpg.group():
                    with dpg.child_window(width=304, height=200):
                        self.add_data_status_window()
                    dpg.add_spacer(height=10)
                    with dpg.child_window(width=304, height=-35):
                        self.add_hanlp_analysis_window()

                with dpg.child_window(width=859, height=684):
                    with dpg.group():
                        with dpg.group(horizontal=True):
                            dpg.add_button(label="Load Novel", callback=lambda: dpg.show_item("file_dialog_id"), tag="load_novel_button")
                            dpg.add_button(label="Convert TC to SC", callback=lambda: safe_callback(self.tc_to_sc_callback), tag="tc_to_sc_button")
                            dpg.add_button(label="Reload Names2", callback=lambda: safe_callback(self.reload_names2_callback), tag="reload_names2_button")
                            dpg.add_button(label="Start Conversion", callback=lambda: self.start_conversion(), tag="start_conversion_button")
                            dpg.add_button(label="Stop Conversion", callback=lambda: safe_callback(self.stop_conversion_callback), tag="stop_conversion_button")
                            dpg.add_button(label="Pause/Resume", callback=self.toggle_pause_conversion, tag="pause_resume_conversion_button")
                            dpg.add_button(label="Advanced Options", callback=lambda: self.toggle_advanced_options(), tag="advanced_options_button")
                                                
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

                with dpg.child_window(width=270, height=684, show=False, tag="advanced_options_window"):
                    self.add_advanced_options()

            with dpg.group(horizontal=True):
                dpg.add_text("Status: ", tag="status_bar_label")
                dpg.add_text("Ready", tag="status_bar_text")

            with dpg.window(label="Chapter Detection Settings", width=400, height=400, show=False, tag="chapter_detection_settings_window"):
                dpg.add_text("Select a chapter detection method:")
                dpg.add_radio_button(
                    items=list(CHAPTER_MATCHERS.keys()),
                    default_value=self.current_detect_method,
                    callback=self.update_detect_method,
                    horizontal=False,
                    tag="chapter_detection_methods"
                )
        with dpg.file_dialog(directory_selector=False, show=False, callback=lambda sender, app_data: self.load_novel(sender, app_data), tag="file_dialog_id", width=700, height=600):
            dpg.add_file_extension(".txt", color=(255, 255, 0, 255))

        dpg.create_viewport(title="QuickTranslator Batch", width=1204, height=800)
        dpg.set_viewport_small_icon("icons/icon_32x32.ico")
        dpg.set_viewport_large_icon("icons/icon_256x256.ico")
        dpg.setup_dearpygui()
        dpg.show_viewport()
        pywinstyles.apply_style(self,"dark")
        dpg.set_primary_window("main_window", True)
        self.add_tooltips()
        self.gui_updater.update_novel_status("", "", "", "")


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
                dpg.add_button(label="Start", callback=lambda: safe_callback(self.start_hanlp_callback), tag="start_hanlp_button")
                dpg.add_button(label="Stop", callback=lambda: safe_callback(self.stop_hanlp_callback), tag="stop_hanlp_button")
                dpg.add_button(label="Pause/Resume", callback=lambda: safe_callback(self.toggle_pause_hanlp), tag="pause_resume_hanlp_button")
                dpg.add_button(label="ReAnalyze", callback=lambda: safe_callback(self.reanalyze_hanlp_callback), tag="reanalyze_hanlp_button")
             
            dpg.add_text("HanLP Progress", color=self.colors["text_header"])
            dpg.add_text("0%", tag="hanlp_percentage", before="hanlp_progress")
            dpg.add_progress_bar(label="HanLP Progress", width=-1, tag="hanlp_progress")
            dpg.add_text("Estimated time: N/A", tag="hanlp_estimated_time")

            dpg.add_text("Name Analyzing Status", color=self.colors["text_header"])
            self.add_name_analyzing_status_table()
            dpg.add_spacer(height=5)

            with dpg.group(horizontal=True):
                dpg.add_button(label="Export Names to CSV", callback=lambda: safe_callback(self.export_names_to_csv_callback), tag="export_names_button", width=150)
                dpg.add_button(label="Open CSV File", callback=lambda: safe_callback(open_csv_file), tag="open_csv_button", width=-1)
                
            dpg.add_spacer(height=5)
            dpg.add_separator()
            dpg.add_spacer(height=5)
            with dpg.group(horizontal=True):
                dpg.add_button(label="CSV To Names2", callback=lambda: safe_callback(self.csv_to_names2_callback), tag="csv_to_names2_button", width=150)
                dpg.add_button(label="Settings", callback=lambda: self.create_export_names2_settings_gui(), tag="export_names2_settings_button", width=-1)

    def add_name_analyzing_status_table(self):
        with dpg.table(header_row=True, borders_innerH=True, borders_outerH=True, borders_innerV=True, borders_outerV=True):
            dpg.add_table_column(label="Category", width_stretch=True)
            dpg.add_table_column(label="Count", width_stretch=True)

            for category in ['Person Name', 'Place Name', 'Organization Name']:
                with dpg.table_row():
                    dpg.add_text(category)
                    dpg.add_text("0", tag=f"{category.lower().replace(' ', '_')}_count")

    def add_novel_status_tables(self):
        with dpg.table(header_row=False, borders_innerH=True, borders_outerH=True, borders_innerV=True, borders_outerV=True, tag="loaded_file_table"):
            dpg.add_table_column(width_fixed=True, init_width_or_weight=100)
            dpg.add_table_column(width_stretch=True)
            
            with dpg.table_row():
                dpg.add_text("Loaded File")
                dpg.add_text("", tag="loaded_file")

        dpg.add_spacer(height=5)

        with dpg.table(header_row=False, borders_innerH=True, borders_outerH=True, borders_innerV=True, borders_outerV=True, tag="novel_info_table"):
            dpg.add_table_column(width_stretch=True, init_width_or_weight=0.5)
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

    def add_advanced_options(self):
        dpg.add_text("Chapters Function", color=self.colors["text_header"])

        with dpg.group(horizontal=True):
            dpg.add_checkbox(label="Detect Chapters", callback=lambda sender, app_data: self.toggle_detect_chapters(sender, app_data), tag="detect_chapters_checkbox")
            dpg.add_button(label="Settings", callback=self.show_chapter_detection_settings, width=-1)

        dpg.add_text("Current Detection Method:", tag="current_method_label")
        with dpg.child_window(width=255, height=65):
            dpg.add_text(self.current_detect_method, wrap=235, tag="current_method")

        dpg.add_text("Detected Chapters: 0", tag="detected_chapters_text")

        with dpg.group(tag="chapter_range_group"):
            dpg.add_input_int(label="Start Chapter", default_value=self.start_chapter, callback=lambda sender, app_data: self.update_start_chapter(sender, app_data), width=150, tag="start_chapter_input", min_value=1)
            dpg.add_input_int(label="End Chapter", default_value=self.end_chapter, callback=lambda sender, app_data: self.update_end_chapter(sender, app_data), width=150, tag="end_chapter_input", min_value=1)
        dpg.add_checkbox(label="Apply to Conversion", tag="apply_to_conversion_checkbox")
        dpg.add_checkbox(label="Apply to HanLP", tag="apply_to_hanlp_checkbox")
        dpg.add_button(label="Apply Chapter Range", callback=lambda: self.apply_chapter_range(), tag="apply_chapter_range_button", width=-1)
        dpg.add_separator()
        dpg.add_text("Parallel Processing", color=self.colors["text_header"])
        dpg.add_input_int(label="Max Workers", default_value=self.max_workers, callback=self.update_max_workers, min_value=1, max_value=16)
        dpg.add_separator()
        dpg.add_text("AI Proofread", color=self.colors["text_header"])
        dpg.add_checkbox(label="Enable AI Proofread", callback=self.toggle_ai_proofread, tag="ai_proofread_checkbox")
        dpg.add_spacer(height=5)
        dpg.add_button(label="AI Proofread Settings", callback=self.create_ai_proofread_settings_gui)
        dpg.add_text("Tokens: 0", tag="ai_proofread_tokens")
        dpg.add_text("Cost: $0.00", tag="ai_proofread_cost")
        dpg.add_spacer(height=3)
        dpg.add_text("Cache: 0%", tag="ai_proofread_cache_percentage")
        dpg.add_button(label="Reset AI Proofread Cache", callback=self.reset_ai_proofread_cache)
        dpg.add_spacer(height=3)
        dpg.add_text("Status: Idle", tag="ai_proofread_status")

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
            ("min_appearances_input", "Set the minimum number of appearances for a name to be included in Names2.txt"),
            ("advanced_options_button", "Click to toggle advanced options"),
            ("detect_chapters_checkbox", "Enable or disable chapter detection"),
            ("start_chapter_input", "Set the starting chapter for conversion"),
            ("end_chapter_input", "Set the ending chapter for conversion"),
            ("apply_chapter_range_button", "Apply the selected chapter range for conversion"),
            ("export_names2_settings_button", "Click to open Export Names2 settings")
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
        self.gui_updater.update_status(loading_info, self.names2_reloaded)

    def get_conversion_data(self):
        if self.conversion_data is None:
            raise ValueError("Conversion data not set. Make sure to call set_conversion_data() first.")
        return self.conversion_data

    def set_conversion_data(self, names2, names, viet_phrase, chinese_phien_am):
        self.conversion_data = (names2, names, viet_phrase, chinese_phien_am)
        self.gui_updater.set_conversion_data(self.conversion_data)

    def toggle_pause_hanlp(self):
        if self.hanlp_paused:
            self.resume_hanlp_callback()
            self.hanlp_paused = False
            dpg.configure_item("pause_resume_hanlp_button", label="Pause HanLP")
        else:
            self.pause_hanlp_callback()
            self.hanlp_paused = True
            dpg.configure_item("pause_resume_hanlp_button", label="Resume HanLP")

    def update_min_appearances(self, sender, app_data):
        self.min_appearances = app_data
        self.gui_updater.update_min_appearances(self.min_appearances)

    def toggle_advanced_options(self):
        self.advanced_options_visible = not self.advanced_options_visible
        if self.advanced_options_visible:
            dpg.configure_viewport(0, width=1482)
            dpg.show_item("advanced_options_window")
        else:
            dpg.configure_viewport(0, width=1204)
            dpg.hide_item("advanced_options_window")
            dpg.set_value("detect_chapters_checkbox", False)
            self.detect_chapters = False
            self.gui_updater.update_status_bar("Chapter detection disabled")
            
            self.detected_chapters = 0
            dpg.set_value("detected_chapters_text", "Detected Chapters: 0")
            
            self.end_chapter = 999999
            dpg.set_value("end_chapter_input", self.end_chapter)
            
            self.start_chapter = 1
            dpg.set_value("start_chapter_input", self.start_chapter)
            dpg.configure_item("chapter_range_group", show=True)
            dpg.set_value("apply_to_conversion_checkbox", False)
            self.apply_to_conversion = False
            dpg.set_value("apply_to_hanlp_checkbox", False)
            self.apply_to_hanlp = False
            self.chapter_range_applied = False

    def toggle_detect_chapters(self, sender, app_data):
        self.detect_chapters = app_data
        if self.detect_chapters:
            self.gui_updater.update_status_bar("Chapter detection enabled")
            self.detect_chapters_in_novel()
        else:
            self.gui_updater.update_status_bar("Chapter detection disabled")
            self.detected_chapters = 0
            dpg.set_value("detected_chapters_text", "Detected Chapters: 0")
            self.end_chapter = 999999
            dpg.set_value("end_chapter_input", self.end_chapter)
            self.start_chapter = 1
            dpg.set_value("start_chapter_input", self.start_chapter)
            self.temp_file_path = None
            dpg.set_value("apply_to_conversion_checkbox", False)
            self.apply_to_conversion = False
            dpg.set_value("apply_to_hanlp_checkbox", False)
            self.apply_to_hanlp = False
            self.chapter_range_applied = False

        dpg.configure_item("chapter_range_group", show=True)

        if not self.detect_chapters:
            dpg.set_value("start_chapter_input", 1)
            dpg.set_value("end_chapter_input", self.end_chapter)

    def update_detect_method(self, sender, app_data, user_data):
        self.current_detect_method = str(app_data)
        dpg.set_value("current_method", self.current_detect_method)
        self.detect_chapters_in_novel()
        dpg.hide_item("chapter_detection_settings_window")

    def show_chapter_detection_settings(self):
        dpg.set_value("chapter_detection_methods", self.current_detect_method)
        dpg.set_value("current_method", self.current_detect_method)
        dpg.show_item("chapter_detection_settings_window")

    def update_start_chapter(self, sender, app_data):
        self.start_chapter = app_data
        self.gui_updater.update_status_bar(f"Start chapter set to {self.start_chapter}")
        if app_data < 1:
            dpg.set_value(sender, 1)

    def update_end_chapter(self, sender, app_data):
        self.end_chapter = app_data
        self.gui_updater.update_status_bar(f"End chapter set to {self.end_chapter}")
        if app_data < 1:
            dpg.set_value(sender, 1)

    def apply_chapter_range(self):
        apply_to_conversion = dpg.get_value("apply_to_conversion_checkbox")
        apply_to_hanlp = dpg.get_value("apply_to_hanlp_checkbox")

        if not (apply_to_conversion or apply_to_hanlp):
            show_error_dialog("Warning: Please select at least one option (Conversion or HanLP) to apply the chapter range.")
            return

        if self.start_chapter > self.end_chapter:
            show_error_dialog("Start chapter cannot be greater than end chapter.")
            return

        self.gui_updater.update_status_bar(f"Chapter range applied: {self.start_chapter} - {self.end_chapter}")

        # Create temporary file with selected chapter range
        if self.detect_chapters:
            temp_folder = "temp"
            os.makedirs(temp_folder, exist_ok=True)
            temp_file_path = os.path.join(temp_folder, f"temp_chapter_{self.start_chapter}_{self.end_chapter}.txt")
            
            chapters = detect_chapters(self.novel_text, self.current_detect_method)
            if not chapters:
                show_error_dialog("No chapters detected. Please check your chapter detection method.")
                return

            start_index = max(0, min(self.start_chapter - 1, len(chapters) - 1))
            end_index = min(self.end_chapter, len(chapters))

            start_pos = chapters[start_index][0]
            end_pos = chapters[end_index][0] if end_index < len(chapters) else len(self.novel_text)

            selected_text = self.novel_text[start_pos:end_pos]
            
            with open(temp_file_path, "w", encoding="utf-8") as temp_file:
                temp_file.write(selected_text)
            
            self.temp_file_path = temp_file_path
        else:
            self.temp_file_path = None

        self.apply_to_conversion = apply_to_conversion
        self.apply_to_hanlp = apply_to_hanlp

        # Notify QTBatch about the chapter range change
        if hasattr(self, 'chapter_range_callback'):
            self.chapter_range_callback(self.start_chapter, self.end_chapter, self.detect_chapters)
        self.chapter_range_applied = True
        self.gui_updater.update_status_bar(f"Chapter range applied: {self.start_chapter} - {self.end_chapter}")

        # Only check/reset HanLP if "Apply to HanLP" is checked
        if apply_to_hanlp:
            cache_file = f"{os.path.basename(self.novel_path)}_{self.start_chapter}_{self.end_chapter}.db"
            cache_path = os.path.join('caches', cache_file)

            if os.path.exists(cache_path):
                # Notify that a cache exists for this range
                self.gui_updater.update_status_bar(f"HanLP cache found for chapters {self.start_chapter}-{self.end_chapter}. It will be used in the next analysis.")
            else:
                # Reset HanLP progress and status if no cache exists
                self.gui_updater.update_hanlp_progress(0.0)
                initial_status = {category: 0 for category in CATEGORY_TRANSLATION.values()}
                self.gui_updater.update_name_analyzing_status(initial_status)
                self.gui_updater.update_status_bar("No HanLP cache found. Progress and status reset for new analysis.")

    def detect_chapters_in_novel(self):
        if not self.novel_text:
            self.gui_updater.update_status_bar("No novel loaded. Please load a novel first.")
            return

        try:
            chapters = detect_chapters(self.novel_text, self.current_detect_method)
            self.gui_updater.update_detected_chapters(len(chapters))
            
            self.end_chapter = len(chapters)
            dpg.set_value("end_chapter_input", self.end_chapter)
        except ValueError as e:
            self.gui_updater.update_status_bar(str(e))

    def load_novel(self, sender, app_data):
        try:
            file_path = app_data['file_path_name']
            self.novel_text, encoding = qt.read_novel_file(file_path)
            self.novel_path = file_path
            self.load_novel_callback(sender, app_data)
            if self.detect_chapters:
                self.detect_chapters_in_novel()
            self.update_ai_proofread_cache_percentage()
        except Exception as e:
            show_error_dialog(f"Error loading novel: {str(e)}")

    def start_conversion(self):
        if not self.novel_text:
            show_error_dialog("No novel loaded. Please load a novel first.")
            return
        try:
            if self.conversion_data is None:
                show_error_dialog("Conversion data is not set. Please load the necessary data first.")
                return

            # Add this check
            if self.ai_proofread_enabled:
                if not self.ai_proofreader.settings["api_key"]:
                    show_error_dialog("AI Proofread is enabled but API Key is empty. Please enter an API Key in the AI Proofread Settings.")
                    return
                # Here, you should call the AI proofread process

            self.start_conversion_callback()
            self.update_ai_proofread_cache_percentage()
        except Exception as e:
            show_error_dialog(f"Error starting conversion: {str(e)}")

    def toggle_pause_conversion(self):
        if self.conversion_paused:
            self.resume_conversion_callback()
            self.conversion_paused = False
            dpg.configure_item("pause_resume_conversion_button", label="Pause Conversion")
        else:
            self.pause_conversion_callback()
            self.conversion_paused = True
            dpg.configure_item("pause_resume_conversion_button", label="Resume Conversion")

    def update_max_workers(self, sender, app_data):
        self.max_workers = app_data
        self.set_max_workers_callback(self.max_workers)

    def update_novel_status(self, *args):
        self.gui_updater.update_novel_status(*args)

    def update_novel_preview(self, *args):
        self.gui_updater.update_novel_preview(*args)

    def update_conversion_preview(self, *args):
        self.gui_updater.update_conversion_preview(*args)

    def update_conversion_status(self, status: str, color: tuple = None, ai_proofread_enabled: bool = False):
        if ai_proofread_enabled:
            dpg.set_value("conversion_status", status)
        else:
            # Extract only the "Converted" part if AI proofread is not enabled
            converted_part = status.split(',')[0] if ',' in status else status
            dpg.set_value("conversion_status", converted_part)
        
        if color:
            dpg.configure_item("conversion_status", color=color)
        self.update_status_bar(f"Conversion: {status}")

    def update_conversion_progress(self, *args):
        self.gui_updater.update_conversion_progress(*args)

    def update_conversion_percent(self, *args):
        self.gui_updater.update_conversion_percent(*args)

    def update_conversion_percent_color(self, *args):
        self.gui_updater.update_conversion_percent_color(*args)

    def update_conversion_time(self, *args):
        self.gui_updater.update_conversion_time(*args)

    def update_hanlp_progress(self, *args):
        self.gui_updater.update_hanlp_progress(*args)

    def update_hanlp_estimated_time(self, *args):
        self.gui_updater.update_hanlp_estimated_time(*args)

    def update_name_analyzing_status(self, *args):
        self.gui_updater.update_name_analyzing_status(*args)

    def update_status_bar(self, *args):
        self.gui_updater.update_status_bar(*args)

    def update_progress_dialog(self, *args):
        self.gui_updater.update_progress_dialog(*args)

    def create_export_names2_settings_gui(self):
        if self.export_names2_settings_gui is None:
            self.export_names2_settings_gui = create_export_names2_settings_gui(self, self.update_export_names2_settings)
        self.export_names2_settings_gui.show_settings_window()

    def update_export_names2_settings(self, settings, name_length_range):
        self.export_names2_settings = settings
        self.name_length_range = name_length_range
        self.gui_updater.update_status_bar(f"Export Names2 settings updated: {settings}, Name length range: {name_length_range}")

    def toggle_ai_proofread(self, sender, app_data):
        self.ai_proofread_enabled = app_data
        self.gui_updater.update_status_bar(f"AI Proofread {'enabled' if self.ai_proofread_enabled else 'disabled'}")

    def create_ai_proofread_settings_gui(self):
        if self.ai_proofread_settings_gui is None:
            self.ai_proofread_settings_gui = create_ai_proofread_settings_gui(self, self.update_ai_proofread_settings)
        self.ai_proofread_settings_gui.show_settings_window()

    def update_ai_proofread_settings(self, settings):
        self.ai_proofreader.update_settings(settings)
        self.gui_updater.update_status_bar("AI Proofread settings updated")
        if self.ai_proofread_settings_gui:
            self.ai_proofread_settings_gui.update_settings(settings)
        
        # Update GUI elements with new settings
        dpg.set_value("ai_proofread_tokens", f"Tokens: {self.ai_proofreader.get_stats()['total_tokens']}")
        dpg.set_value("ai_proofread_cost", f"Cost: ${self.ai_proofreader.get_stats()['total_cost']}")

    def toggle_context_aware(self, sender, app_data):
        self.ai_proofreader.settings["context_aware"] = app_data
        self.gui_updater.update_status_bar(f"AI Proofread context-aware {'enabled' if app_data else 'disabled'}")

    def toggle_adaptive_learning(self, sender, app_data):
        self.ai_proofreader.settings["adaptive_learning"] = app_data
        self.gui_updater.update_status_bar(f"AI Proofread adaptive learning {'enabled' if app_data else 'disabled'}")

    def reset_ai_proofread_cache(self):
        if self.novel_path:
            cache_file = self.ai_proofreader.cache.get_cache_path(self.novel_path)
            if os.path.exists(cache_file):
                os.remove(cache_file)
            self.ai_proofreader.clear_cache(self.novel_path)
            self.gui_updater.update_status_bar("AI Proofread cache reset and file deleted")
            self.update_ai_proofread_cache_percentage()
            dpg.set_value("ai_proofread_status", "Status: Cache cleared and file deleted")
        else:
            self.gui_updater.update_status_bar("No novel loaded. Cannot reset cache.")

    def update_ai_proofread_cache_percentage(self, percentage=None):
        if percentage is None and hasattr(self, 'ai_proofreader') and self.novel_path:
            percentage = self.ai_proofreader.get_cache_percentage(self.novel_path)
        if percentage is not None:
            dpg.set_value("ai_proofread_cache_percentage", f"Cache: {percentage:.2f}%")

    def update_proofreading_progress(self, progress):
        self.gui_updater.update_proofreading_progress(progress)

    def add_log_message(self, message):
        # Add this method to handle log messages
        logging.info(message)
        self.update_status_bar(message)

    def update_ai_proofread_stats(self, total_tokens: int, total_cost: float):
        self.gui_updater.update_ai_proofread_stats(total_tokens, total_cost)
import os
import dearpygui.dearpygui as dpg
from typing import Callable
import config
import logging

class GUI:
    def __init__(self, load_novel_callback: Callable, reload_names2_callback: Callable,
                 start_conversion_callback: Callable, stop_conversion_callback: Callable):
        self.load_novel_callback = load_novel_callback
        self.reload_names2_callback = reload_names2_callback
        self.start_conversion_callback = start_conversion_callback
        self.stop_conversion_callback = stop_conversion_callback
        self.names2_reloaded = False

    def create_gui(self):
        dpg.create_context()

        # Define color scheme
        self.colors = {
            "bg_primary": (30, 30, 30),
            "bg_secondary": (45, 45, 45),
            "text_primary": (220, 220, 220),
            "text_secondary": (180, 180, 180),
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

        with dpg.window(label="QuickTranslator Batch", tag="main_window", width=800, height=700):
            with dpg.menu_bar():
                with dpg.menu(label="File"):
                    dpg.add_menu_item(label="Load Novel", callback=lambda: dpg.show_item("file_dialog_id"), tag="load_novel_menu")
                    dpg.add_menu_item(label="Exit", callback=lambda: dpg.stop_dearpygui())
                with dpg.menu(label="Settings"):
                    dpg.add_menu_item(label="About", callback=self.show_about)

            with dpg.group(horizontal=True):
                with dpg.child_window(width=360, height=-35):
                    dpg.add_text("Data Status", color=self.colors["text_secondary"])
                    dpg.add_separator()
                    self.add_data_status_table()

                with dpg.child_window(width=-1, height=-35):
                    with dpg.group():
                        with dpg.group(horizontal=True):
                            dpg.add_button(label="Load Novel", callback=lambda: dpg.show_item("file_dialog_id"), tag="load_novel_button")
                            dpg.add_button(label="Reload Names2", callback=self.reload_names2_callback, tag="reload_names2_button")
                            dpg.add_button(label="Start Conversion", callback=self.start_conversion_callback, tag="start_conversion_button")
                            dpg.add_button(label="Stop Conversion", callback=self.stop_conversion_callback, tag="stop_conversion_button")
                    
                    dpg.add_separator()
                    dpg.add_text("Novel Status", color=self.colors["text_secondary"])
                    dpg.add_text("Not loaded", tag="novel_status")
                    
                    dpg.add_separator()
                    dpg.add_text("Novel Preview", color=self.colors["text_secondary"])
                    with dpg.child_window(height=200):
                        dpg.add_text("", tag="novel_preview", wrap=480)
                    
                    dpg.add_separator()
                    dpg.add_text("Conversion Status", color=self.colors["text_secondary"])
                    dpg.add_text("Not started", tag="conversion_status")
                    dpg.add_text("", tag="conversion_time")
                    dpg.add_text("0%", tag="conversion_percentage", before="conversion_progress")
                    dpg.add_progress_bar(label="Conversion Progress", width=-1, tag="conversion_progress")

            # Add status bar
            with dpg.group(horizontal=True):
                dpg.add_text("Status: ", tag="status_bar_label")
                dpg.add_text("Ready", tag="status_bar_text")

        with dpg.file_dialog(directory_selector=False, show=False, callback=self.load_novel_callback, tag="file_dialog_id"):
            dpg.add_file_extension(".txt", color=(255, 255, 0, 255))

        dpg.create_viewport(title="QuickTranslator Batch", width=875, height=700)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("main_window", True)

        self.add_tooltips()

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

    def add_tooltips(self):
        tooltips = [
            ("load_novel_button", "Click to load a novel file"),
            ("load_novel_menu", "Click to load a novel file"),
            ("reload_names2_button", "Click to reload Names2 data"),
            ("start_conversion_button", "Click to start the conversion process"),
            ("stop_conversion_button", "Click to stop the ongoing conversion"),
            ("conversion_progress", "Shows the progress of the current conversion")
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

    def update_novel_status(self, novel_name: str, encoding: str, size_str: str):
        dpg.set_value("novel_status", f"Loaded: {novel_name}\nEncoding: {encoding}\nSize: {size_str}")
        dpg.configure_item("novel_status", color=self.colors["success"])
        self.update_status_bar(f"Novel loaded: {novel_name}")

    def update_novel_preview(self, preview: str):
        dpg.set_value("novel_preview", preview)

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

    def update_status_bar(self, message: str):
        dpg.set_value("status_bar_text", message)

    def show_about(self):
        with dpg.window(label="About", modal=True, width=400, height=200):
            dpg.add_text("QuickTranslator Batch Ver 1.0.0")
            dpg.add_text("Created thanks to Perplexity.ai + Claude.ai")
            dpg.add_text("Source: https://github.com/SmashPhoenix272/QTBatch")
            dpg.add_button(label="Close", callback=lambda: dpg.delete_item(dpg.get_item_parent(dpg.last_item())))
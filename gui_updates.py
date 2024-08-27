import dearpygui.dearpygui as dpg
from gui_utils import process_preview_text
import logging
import traceback

class GUIUpdater:
    def __init__(self, colors):
        self.colors = colors
        self.conversion_data = None

    def update_status(self, loading_info, names2_reloaded=False):
        for key, info in loading_info.items():
            self._update_status_item(key, info, names2_reloaded)

    def _update_status_item(self, key, info, names2_reloaded):
        try:
            status_text = "Loaded" if info['loaded'] else "Not loaded"
            if key == "names2" and names2_reloaded:
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
        if self.conversion_data is None:
            logging.error("Conversion data is not set. Cannot process preview text.")
            return
        processed_preview = process_preview_text(preview, self.conversion_data)
        dpg.set_value("conversion_preview", processed_preview)

    def set_conversion_data(self, conversion_data):
        self.conversion_data = conversion_data

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

    def update_conversion_progress(self, progress: float):
        dpg.set_value("conversion_progress", progress)
        
    def update_conversion_percent(self, progress: float):
        percentage = progress * 100
        dpg.set_value("conversion_percentage", f"{percentage:.2f}%")

    def update_conversion_percent_color(self, color: tuple):
        dpg.configure_item("conversion_percentage", color=color)

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
        try:
            for category, count in status.items():
                tag = f"{category.lower().replace(' ', '_')}_count"
                if dpg.does_item_exist(tag):
                    dpg.set_value(tag, str(count))
                else:
                    logging.warning(f"Tag '{tag}' does not exist for category '{category}'")
            
            total_count = sum(status.values())
            self.update_status_bar(f"HanLP Analysis completed: {total_count} names analyzed")
            
            logging.info(f"Name Analyzing Status updated: {status}")
        except Exception as e:
            logging.error(f"Error in update_name_analyzing_status: {str(e)}")
            logging.error(f"Full traceback: {traceback.format_exc()}")

    def update_status_bar(self, message: str):
        dpg.set_value("status_bar_text", message)

    def update_min_appearances(self, min_appearances):
        self.update_status_bar(f"Minimum appearances set to {min_appearances}")

    def update_progress_dialog(self, progress: float):
        dpg.set_value("progress_dialog_bar", progress)

    def update_detected_chapters(self, count: int):
        dpg.set_value("detected_chapters_text", f"Detected Chapters: {count}")
        self.update_status_bar(f"Detected {count} chapters")

    def update_export_filename(self, filename: str):
        self.update_status_bar(f"Export filename updated: {filename}")

    def update_ai_proofread_stats(self, total_tokens: int, total_cost: float):
        dpg.set_value("ai_proofread_tokens", f"Tokens: {total_tokens}")
        dpg.set_value("ai_proofread_cost", f"Cost: ${total_cost}")
        dpg.set_value("ai_proofread_status", "Status: Complete")

    def update_proofreading_progress(self, progress: float):
        percentage = progress * 100
        dpg.set_value("proofreading_progress", progress)
        dpg.set_value("proofreading_percentage", f"{percentage:.2f}%")
        self.update_status_bar(f"Proofreading progress: {percentage:.2f}%")
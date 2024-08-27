import dearpygui.dearpygui as dpg
from typing import Dict, Callable, Tuple

class ExportNames2SettingsGUI:
    def __init__(self, main_gui, update_settings_callback: Callable):
        self.main_gui = main_gui
        self.update_settings_callback = update_settings_callback
        self.settings: Dict[str, int] = {
            "Person Name": 1,
            "Place Name": 1,
            "Organization Name": 1
        }
        self.name_length_range: Tuple[int, int] = (1, 4)

    def create_settings_window(self):
        with dpg.window(label="Export Names2 Settings", width=360, height=265, show=False, tag="export_names2_settings_window"):
            dpg.add_text("Minimum Appearances for Each Category")
            for category in self.settings.keys():
                dpg.add_input_int(label=category, default_value=self.settings[category], callback=lambda sender, app_data, user_data: self.update_category_setting(sender, app_data, user_data), user_data=category, width=200, min_value=1)
            
            dpg.add_separator()
            dpg.add_text("Person Name Length Range")
            with dpg.group(horizontal=True):
                dpg.add_input_int(label="Min", default_value=self.name_length_range[0], callback=lambda sender, app_data: self.update_name_length_min(sender, app_data), width=100, min_value=1)
                dpg.add_input_int(label="Max", default_value=self.name_length_range[1], callback=lambda sender, app_data: self.update_name_length_max(sender, app_data), width=100, min_value=1)
            
            dpg.add_separator()
            dpg.add_button(label="Apply Settings", callback=lambda: self.apply_settings())

    def show_settings_window(self):
        dpg.show_item("export_names2_settings_window")

    def update_category_setting(self, sender, app_data, user_data):
        corrected_value = max(1, app_data)
        self.settings[user_data] = corrected_value
        dpg.set_value(sender, corrected_value)

    def update_name_length_min(self, sender, app_data):
        self.name_length_range = (max(1, app_data), max(self.name_length_range[1], max(1, app_data)))
        dpg.set_value(sender, self.name_length_range[0])

    def update_name_length_max(self, sender, app_data):
        self.name_length_range = (self.name_length_range[0], max(self.name_length_range[0], max(1, app_data)))
        dpg.set_value(sender, self.name_length_range[1])

    def apply_settings(self):
        self.update_settings_callback(self.settings, self.name_length_range)
        dpg.hide_item("export_names2_settings_window")

def create_export_names2_settings_gui(main_gui, update_settings_callback: Callable):
    settings_gui = ExportNames2SettingsGUI(main_gui, update_settings_callback)
    settings_gui.create_settings_window()
    return settings_gui
import dearpygui.dearpygui as dpg
from typing import Dict, Callable, Any

class AIProofreadSettingsGUI:
    def __init__(self, main_gui, update_settings_callback: Callable):
        self.main_gui = main_gui
        self.update_settings_callback = update_settings_callback
        self.settings = self.main_gui.ai_proofreader.settings.copy()  # Create a copy of the settings
        self.providers = ["Google GenerativeAI", "Vertex AI"]
        self.gemini_models = ["gemini-1.5-pro-001", "gemini-1.5-flash-001", "gemini-1.0-pro"]
        self.vertex_models = ["gemini-1.5-pro-001", "gemini-1.5-flash-001", "gemini-1.0-pro"]  # Add Vertex AI models here
        self.settings["provider"] = "Google GenerativeAI"  # Default provider

    def create_settings_window(self):
        with dpg.window(label="AI Proofread Settings", width=515, height=500, show=False, tag="ai_proofread_settings_window"):
            dpg.add_combo(label="Provider", items=self.providers, default_value=self.settings["provider"], callback=self.update_provider, width=200, tag="ai_proofread_provider")
            dpg.add_spacer(height=5)
            dpg.add_input_text(label="API Key", default_value=self.settings.get("api_key", ""), callback=self.update_api_key, width=350, tag="ai_proofread_api_key")
            dpg.add_spacer(height=5)
            dpg.add_combo(label="Model", items=self.gemini_models, default_value=self.settings["model"], callback=self.update_model, width=200, tag="ai_proofread_model")
            dpg.add_spacer(height=5)
            with dpg.table(header_row=False):
                dpg.add_table_column()
                dpg.add_table_column()
                with dpg.table_row():
                    with dpg.group():
                        dpg.add_checkbox(label="Context Caching", default_value=self.settings["context_caching"], 
                                        callback=self.update_context_caching, tag="ai_proofread_context_caching")
                    with dpg.group():
                        dpg.add_checkbox(label="Batch Predictions", default_value=self.settings["batch_predictions"], 
                                        callback=self.update_batch_predictions, tag="ai_proofread_batch_predictions")
                with dpg.table_row():
                    with dpg.group():
                        dpg.add_checkbox(label="Adaptive Learning", default_value=self.settings["adaptive_learning"], 
                                        callback=self.update_adaptive_learning, tag="ai_proofread_adaptive_learning")
            dpg.add_spacer(height=5)
            
            with dpg.group():
                with dpg.group(horizontal=True):
                    dpg.add_text("Prompt Template")
                    dpg.add_button(label="Edit", callback=self.edit_prompt_template)
                with dpg.child_window(width=-1, height=170):
                    dpg.add_text(self.settings["prompt_template"], wrap=475, tag="prompt_template_text")
            dpg.add_spacer(height=20)
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=175)
                dpg.add_button(label="Apply Settings", callback=self.apply_settings)

    def show_settings_window(self):
        self.refresh_settings()
        dpg.show_item("ai_proofread_settings_window")

    def refresh_settings(self):
        self.settings = self.main_gui.ai_proofreader.settings.copy()  # Create a copy of the settings
        dpg.set_value("ai_proofread_provider", self.settings.get("provider", "Google GenerativeAI"))
        dpg.set_value("ai_proofread_api_key", self.settings.get("api_key", ""))
        dpg.set_value("ai_proofread_model", self.settings["model"])
        dpg.set_value("ai_proofread_context_caching", self.settings["context_caching"])
        dpg.set_value("ai_proofread_batch_predictions", self.settings["batch_predictions"])
        dpg.set_value("prompt_template_text", self.settings["prompt_template"])
        
        # Update checkbox states
        self.update_batch_predictions_state(self.settings["provider"])
        self.update_context_caching_state(self.settings["model"])

    def update_provider(self, sender, app_data):
        self.settings["provider"] = app_data
        if app_data == "Google GenerativeAI":
            dpg.configure_item("ai_proofread_model", items=self.gemini_models)
        elif app_data == "Vertex AI":
            dpg.configure_item("ai_proofread_model", items=self.vertex_models)
        
        self.update_batch_predictions_state(app_data)

    def update_api_key(self, sender, app_data):
        self.settings["api_key"] = app_data

    def update_model(self, sender, app_data):
        self.settings["model"] = app_data
        self.update_context_caching_state(app_data)

    def update_context_caching(self, sender, app_data):
        self.settings["context_caching"] = app_data

    def update_batch_predictions(self, sender, app_data):
        self.settings["batch_predictions"] = app_data

    def update_batch_predictions_state(self, provider):
        if provider == "Google GenerativeAI":
            dpg.disable_item("ai_proofread_batch_predictions")
            self.settings["batch_predictions"] = False
            dpg.set_value("ai_proofread_batch_predictions", False)
        else:
            dpg.enable_item("ai_proofread_batch_predictions")

    def update_context_caching_state(self, model):
        if model == "gemini-1.0-pro":
            dpg.disable_item("ai_proofread_context_caching")
            self.settings["context_caching"] = False
            dpg.set_value("ai_proofread_context_caching", False)
        else:
            dpg.enable_item("ai_proofread_context_caching")

    def edit_prompt_template(self):
        with dpg.window(label="Edit Prompt Template", width=500, height=300, modal=True, tag="edit_prompt_template_window"):
            dpg.add_input_text(multiline=True, width=480, height=200, default_value=self.settings["prompt_template"], tag="prompt_template_edit")
            dpg.add_button(label="Save", callback=self.save_prompt_template)

    def save_prompt_template(self):
        new_template = dpg.get_value("prompt_template_edit")
        self.settings["prompt_template"] = new_template
        dpg.set_value("prompt_template_text", new_template)
        dpg.delete_item("edit_prompt_template_window")

    def apply_settings(self):
        self.update_settings_callback(self.settings)
        dpg.hide_item("ai_proofread_settings_window")

    def update_settings(self, new_settings):
        self.settings = new_settings.copy()  # Create a copy of the new settings
        self.refresh_settings()

    def update_adaptive_learning(self, sender, app_data):
        self.settings["adaptive_learning"] = app_data

def create_ai_proofread_settings_gui(main_gui, update_settings_callback: Callable):
    settings_gui = AIProofreadSettingsGUI(main_gui, update_settings_callback)
    settings_gui.create_settings_window()
    return settings_gui
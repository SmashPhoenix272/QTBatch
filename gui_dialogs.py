import dearpygui.dearpygui as dpg
import pyperclip

def show_about():
    with dpg.window(label="About", modal=True, width=400, height=200):
        dpg.add_text("QuickTranslator Batch Ver 2.9.0")
        dpg.add_text("Created thanks to Perplexity.ai + Claude.ai")
        dpg.add_text("Source: https://github.com/SmashPhoenix272/QTBatch")
        dpg.add_button(label="Close", callback=lambda: dpg.delete_item(dpg.get_item_parent(dpg.last_item())))

def show_progress_dialog(title: str, message: str):
    with dpg.window(label=title, modal=True, no_close=True) as progress_window:
        dpg.add_text(message)
        dpg.add_progress_bar(label="Progress", width=-1, height=20, tag="progress_dialog_bar")
    return progress_window

def close_progress_dialog(progress_window):
    dpg.delete_item(progress_window)

def show_error_dialog(message: str):
    with dpg.window(label="Error", modal=True, width=500, height=250, tag="error_window"):
        dpg.add_text(message, wrap=485)
        dpg.add_spacer(height=120)
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=125)
            dpg.add_button(label="OK and Close", callback=lambda: dpg.delete_item("error_window"))
            dpg.add_button(label="Copy Error Log", callback=lambda: pyperclip.copy(message))
            dpg.add_spacer(width=135)
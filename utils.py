import os
import requests
import shutil
import logging
from typing import Tuple, List

def check_and_download_fonts(font_dir: str, fonts: List[Tuple[str, str, str]]) -> None:
    """
    Check if fonts exist and download them if not.

    :param font_dir: Directory to store fonts
    :param fonts: List of tuples containing (font_path, font_url, font_name)
    """
    if not os.path.exists(font_dir):
        os.makedirs(font_dir)

    for font_path, font_url, font_name in fonts:
        if not os.path.exists(font_path):
            logging.info(f"{font_name} font not found. Downloading...")
            try:
                response = requests.get(font_url, stream=True)
                response.raise_for_status()
                with open(font_path, 'wb') as out_file:
                    shutil.copyfileobj(response.raw, out_file)
                logging.info(f"{font_name} font downloaded successfully.")
            except Exception as e:
                logging.error(f"Error downloading {font_name} font: {str(e)}")
        else:
            logging.info(f"{font_name} font found.")

def get_file_size_str(file_path: str) -> str:
    """
    Get the file size as a formatted string.

    :param file_path: Path to the file
    :return: Formatted file size string
    """
    file_size = os.path.getsize(file_path)
    if file_size < 1024:
        return f"{file_size} bytes"
    elif file_size < 1024 * 1024:
        return f"{file_size / 1024:.2f} KB"
    else:
        return f"{file_size / (1024 * 1024):.2f} MB"
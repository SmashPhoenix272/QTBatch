import subprocess
import logging
import traceback
import QuickTranslator as qt

def process_preview_text(text: str, conversion_data) -> str:
    names2, names, viet_phrase, chinese_phien_am = conversion_data
    
    paragraphs = text.split('\n')
    
    processed_paragraphs = []
    for paragraph in paragraphs:
        if paragraph.strip():
            converted = qt.process_paragraph(paragraph, names2, names, viet_phrase, chinese_phien_am)
            processed_paragraphs.append(converted)
    
    return '\n'.join(processed_paragraphs)

def open_csv_file():
    try:
        subprocess.Popen(['start', 'AnalyzedNames.csv'], shell=True)
    except Exception as e:
        logging.error(f"Error opening CSV file: {str(e)}")
        raise

def safe_callback(callback, *args, **kwargs):
    try:
        return callback(*args, **kwargs)
    except Exception as e:
        error_message = f"An error occurred: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        logging.error(error_message)
        raise

def detect_chapters_in_novel(novel_text):
    if not novel_text:
        raise ValueError("No novel loaded. Please load a novel first.")

    chapters = qt.detect_chapters(novel_text)
    return len(chapters)
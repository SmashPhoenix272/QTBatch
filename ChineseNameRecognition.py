import hanlp
import pandas as pd
from collections import defaultdict

# Load models
recognizer = hanlp.load(hanlp.pretrained.ner.MSRA_NER_BERT_BASE_ZH)
tokenizer = hanlp.load(hanlp.pretrained.tok.COARSE_ELECTRA_SMALL_ZH)
sentence_segmenter = hanlp.load(hanlp.pretrained.mtl.CLOSE_TOK_POS_NER_SRL_DEP_SDP_CON_ELECTRA_SMALL_ZH)

def read_dictionary(file_path):
    mapping = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                if '=' in line:
                    chinese_word, sino_vietnamese_word = line.strip().split('=')
                    mapping[chinese_word] = sino_vietnamese_word.capitalize()  # Convert to proper case
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
    return mapping

def translate_to_sino_vietnamese(chinese_name, dictionary):
    return ' '.join(dictionary.get(char, char) for char in chinese_name)

def split_sentence(sentence, max_chars=126):
    if len(sentence) <= max_chars:
        return [sentence]
    
    # First, try to split by '，'
    parts = sentence.split('，')
    if max(len(part) for part in parts) <= max_chars:
        return parts
    
    # If still too long, split by characters
    return [sentence[i:i+max_chars] for i in range(0, len(sentence), max_chars)]

def export_ner_results_to_excel(all_entities, dictionary, output_file='ner_results.xlsx'):
    # Dictionary to store entity information
    entity_info = defaultdict(lambda: {'category': '', 'appearances': 0})
    
    # Process all entities
    for entities in all_entities:
        for entity, category, _, _ in entities:
            entity_info[entity]['category'] = category
            entity_info[entity]['appearances'] += 1
    
    # Prepare data for DataFrame
    data = []
    for entity, info in entity_info.items():
        sino_vietnamese_name = translate_to_sino_vietnamese(entity, dictionary)
        data.append({
            'Category': info['category'],
            'Name': entity,
            'NameSinoVietnamese': sino_vietnamese_name,
            'Appearances': info['appearances']
        })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Sort by appearances in descending order
    df = df.sort_values('Appearances', ascending=False)
    
    # Translate category acronyms to full names
    category_translation = {
        'NR': 'Person Name',
        'NS': 'Place Name',
        'NT': 'Organization Name',
        'NW': 'Work Name',
        'NZ': 'Other Proper Noun'
    }
    df['Category'] = df['Category'].map(lambda x: category_translation.get(x, x))
    
    # Export to Excel
    df.to_excel(output_file, index=False, header=True)
    print(f"Results exported to {output_file}")

# Read the dictionary file
dictionary_mapping = read_dictionary('ChinesePhienAmWords.txt')

# Read the novel file
encodings_to_try = ['utf-8', 'gbk', 'gb2312', 'big5', 'ascii']
novel_text = ""

for encoding in encodings_to_try:
    try:
        with open('novel.txt', 'r', encoding=encoding) as file:
            novel_text = file.read()
        print(f"Successfully read the file using {encoding} encoding.")
        break
    except UnicodeDecodeError:
        print(f"Failed to read with {encoding} encoding.")

if not novel_text:
    print("Failed to read the file with any of the attempted encodings.")
    exit()

# Split the novel text into paragraphs
paragraphs = novel_text.split('\n')

all_entities = []

# Process each paragraph
for paragraph in paragraphs:
    # Split sentences using multiple punctuation marks
    sentences = []
    current_sentence = ""
    for char in paragraph:
        current_sentence += char
        if char in ['。', '！', '？']:
            sentences.append(current_sentence)
            current_sentence = ""
    if current_sentence:  # Add any remaining text as a sentence
        sentences.append(current_sentence)

    for sentence in sentences:
        if sentence:
            # Split long sentences
            segments = split_sentence(sentence)
            for segment in segments:
                tokens = tokenizer(segment)
                if len(tokens) > 126:  # Double-check length
                    print(f"Warning: Segment still too long: {len(tokens)} tokens")
                    continue  # Skip this segment or further process it
                entities = recognizer(tokens)
                all_entities.append(entities)
                
                print("Segment:", segment)
                print("Entities:", entities)
                print()

# Export results to Excel
export_ner_results_to_excel(all_entities, dictionary_mapping, 'ner_results.xlsx')
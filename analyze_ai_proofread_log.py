'''To verify if the AI proofread cache is being properly utilized during the conversion process, please follow these steps:

Run the QuickTranslator Batch application and open the GUI.
In the "Advanced Options" section, enable AI Proofread by checking the "Enable AI Proofread" checkbox.
Click on "AI Proofread Settings" and ensure that an API key is set and other settings are configured.
Load a novel file using the "Load Novel" button.
Start the conversion process by clicking the "Start Conversion" button.
Monitor the GUI for updates on the conversion progress, AI proofreading progress, and cache usage.
After the conversion is complete, note down the cache percentage displayed in the GUI.
Run the analyze_ai_proofread_log.py script to get a summary of the cache usage for the first run.
Run the conversion process again on the same file.
Monitor the GUI and observe if the conversion is faster this time.
Run the analyze_ai_proofread_log.py script again to get a summary of the cache usage for the second run.
Compare the results of the two log analyses. In the second run, you should see:

A higher cache hit rate
More cache hits and fewer cache misses
A faster overall conversion time
If you observe these changes, it indicates that the AI proofread cache is being properly utilized during the conversion process. Please run these steps and provide feedback on the results, including the cache hit rates and conversion times for both runs.'''


import re
from collections import Counter

def analyze_log(log_file_path):
    cache_hits = 0
    cache_misses = 0
    total_chunks = 0
    cache_keys = Counter()

    with open(log_file_path, 'r') as log_file:
        for line in log_file:
            if "Proofreading chunk for file:" in line:
                total_chunks += 1
            elif "Using cached result for key:" in line:
                cache_hits += 1
                key = re.search(r'key: (\w+)', line)
                if key:
                    cache_keys[key.group(1)] += 1
            elif "No cached result found for key:" in line:
                cache_misses += 1
                key = re.search(r'key: (\w+)', line)
                if key:
                    cache_keys[key.group(1)] += 1

    cache_hit_rate = cache_hits / total_chunks if total_chunks > 0 else 0
    print(f"Total chunks processed: {total_chunks}")
    print(f"Cache hits: {cache_hits}")
    print(f"Cache misses: {cache_misses}")
    print(f"Cache hit rate: {cache_hit_rate:.2%}")
    print("\nTop 10 most common cache keys:")
    for key, count in cache_keys.most_common(10):
        print(f"{key}: {count}")

if __name__ == "__main__":
    log_file_path = "ai_proofread.log"
    analyze_log(log_file_path)
import sqlite3
import os
import hashlib

class ProofreadCache:
    def __init__(self, cache_dir='proofread_caches'):
        self.cache_dir = cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

    def get_cache_path(self, filename):
        base_name = os.path.basename(filename)
        return os.path.join(self.cache_dir, f"{base_name}.db")

    def get_cache_key(self, chinese_text, sino_vietnamese_text, names):
        key = f"{chinese_text}|{sino_vietnamese_text}|{'|'.join(names)}"
        return hashlib.md5(key.encode()).hexdigest()

    def get_cached_result(self, filename, chinese_text, sino_vietnamese_text, names):
        cache_path = self.get_cache_path(filename)
        cache_key = self.get_cache_key(chinese_text, sino_vietnamese_text, names)
        
        conn = sqlite3.connect(cache_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS proofread_cache
                          (cache_key TEXT PRIMARY KEY, result TEXT)''')
        
        cursor.execute("SELECT result FROM proofread_cache WHERE cache_key = ?", (cache_key,))
        result = cursor.fetchone()
        
        conn.close()
        
        return result[0] if result else None

    def cache_result(self, filename, chinese_text, sino_vietnamese_text, names, result):
        cache_path = self.get_cache_path(filename)
        cache_key = self.get_cache_key(chinese_text, sino_vietnamese_text, names)
        
        conn = sqlite3.connect(cache_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS proofread_cache
                          (cache_key TEXT PRIMARY KEY, result TEXT)''')
        
        cursor.execute("INSERT OR REPLACE INTO proofread_cache (cache_key, result) VALUES (?, ?)",
                       (cache_key, result))
        
        # Update total items count
        cursor.execute('''CREATE TABLE IF NOT EXISTS cache_stats
                          (total_items INTEGER)''')
        cursor.execute("INSERT OR REPLACE INTO cache_stats (rowid, total_items) VALUES (1, coalesce((SELECT total_items FROM cache_stats WHERE rowid = 1), 0) + 1)")
        
        conn.commit()
        conn.close()

    def clear_cache(self, filename):
        cache_path = self.get_cache_path(filename)
        if os.path.exists(cache_path):
            conn = sqlite3.connect(cache_path)
            cursor = conn.cursor()
            
            # Clear proofread_cache table
            cursor.execute("DELETE FROM proofread_cache")
            
            # Reset cache_stats
            cursor.execute("UPDATE cache_stats SET total_items = 0 WHERE rowid = 1")
            
            conn.commit()
            conn.close()

    def get_cache_percentage(self, filename):
        cache_path = self.get_cache_path(filename)
        if not os.path.exists(cache_path):
            return 0

        conn = sqlite3.connect(cache_path)
        cursor = conn.cursor()

        # Get total items
        cursor.execute("SELECT total_items FROM cache_stats WHERE rowid = 1")
        total_items = cursor.fetchone()
        total_items = total_items[0] if total_items else 0

        # Get cached items
        cursor.execute("SELECT COUNT(*) FROM proofread_cache")
        cached_items = cursor.fetchone()[0]

        conn.close()

        if total_items == 0:
            return 0
        return (cached_items / total_items) * 100
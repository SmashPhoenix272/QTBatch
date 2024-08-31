import unittest
import sys
import os
import traceback
import time
import re

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Starting test_split_into_parts.py")

try:
    from ai_proofread import AIProofreader
    print("Successfully imported AIProofreader")
except Exception as e:
    print(f"Error importing AIProofreader: {str(e)}")
    print(traceback.format_exc())
    sys.exit(1)

class TestSplitIntoParts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            # Create a minimal AIProofreader instance for testing
            cls.proofreader = AIProofreader(main_gui=None, update_settings_callback=lambda: None)
            print("Successfully created AIProofreader instance")
        except Exception as e:
            print(f"Error in setUpClass: {str(e)}")
            print(traceback.format_exc())
            raise

    def run_test_with_timeout(self, test_method, timeout=5):
        start_time = time.time()
        try:
            test_method()
            print(f"{test_method.__name__} completed successfully")
        except Exception as e:
            print(f"Error in {test_method.__name__}: {str(e)}")
            print(traceback.format_exc())
        finally:
            end_time = time.time()
            duration = end_time - start_time
            print(f"{test_method.__name__} took {duration:.2f} seconds")
            if duration > timeout:
                print(f"Warning: {test_method.__name__} exceeded timeout of {timeout} seconds")

    def test_split_text_even(self):
        print("Running test_split_text_even")
        chinese_text = "段落1。\n段落2。\n段落3。\n段落4。"
        sino_vietnamese_text = "Đoạn 1.\nĐoạn 2.\nĐoạn 3.\nĐoạn 4."
        zh_parts, vi_parts = self.proofreader.split_text(chinese_text, sino_vietnamese_text)
        print(f"Chinese parts: {zh_parts}")
        print(f"Sino-Vietnamese parts: {vi_parts}")
        self.assertEqual(len(zh_parts), 2)
        self.assertEqual(len(vi_parts), 2)
        self.assertEqual(len(zh_parts[0].split('\n')), 2)
        self.assertEqual(len(zh_parts[1].split('\n')), 2)
        self.assertEqual(len(vi_parts[0].split('\n')), 2)
        self.assertEqual(len(vi_parts[1].split('\n')), 2)

    def test_split_text_odd(self):
        print("Running test_split_text_odd")
        chinese_text = "段落1。\n段落2。\n段落3。"
        sino_vietnamese_text = "Đoạn 1.\nĐoạn 2.\nĐoạn 3."
        zh_parts, vi_parts = self.proofreader.split_text(chinese_text, sino_vietnamese_text)
        print(f"Chinese parts: {zh_parts}")
        print(f"Sino-Vietnamese parts: {vi_parts}")
        self.assertEqual(len(zh_parts), 2)
        self.assertEqual(len(vi_parts), 2)
        self.assertEqual(len(zh_parts[0].split('\n')), 1)
        self.assertEqual(len(zh_parts[1].split('\n')), 2)
        self.assertEqual(len(vi_parts[0].split('\n')), 1)
        self.assertEqual(len(vi_parts[1].split('\n')), 2)

    def test_split_text_uneven_paragraphs(self):
        print("Running test_split_text_uneven_paragraphs")
        chinese_text = "段落1。\n段落2。\n段落3。"
        sino_vietnamese_text = "Đoạn 1.\nĐoạn 2.\nĐoạn 3.\nĐoạn 4."
        zh_parts, vi_parts = self.proofreader.split_text(chinese_text, sino_vietnamese_text)
        print(f"Chinese parts: {zh_parts}")
        print(f"Sino-Vietnamese parts: {vi_parts}")
        self.assertEqual(len(zh_parts), 2)
        self.assertEqual(len(vi_parts), 2)
        self.assertEqual(len(zh_parts[0].split('\n')), 1)
        self.assertEqual(len(zh_parts[1].split('\n')), 2)
        self.assertEqual(len(vi_parts[0].split('\n')), 1)
        self.assertEqual(len(vi_parts[1].split('\n')), 2)

    def test_split_text_from_file(self):
        print("Running test_split_text_from_file")
        try:
            with open('TestSplit.txt', 'r', encoding='utf-8') as file:
                content = file.read()

            zh_pattern = r'<ZH>(.*?)</ZH>'
            vi_pattern = r'<VI>(.*?)</VI>'

            zh_match = re.search(zh_pattern, content, re.DOTALL)
            vi_match = re.search(vi_pattern, content, re.DOTALL)

            if zh_match and vi_match:
                chinese_text = zh_match.group(1).strip()
                sino_vietnamese_text = vi_match.group(1).strip()

                zh_parts, vi_parts = self.proofreader.split_text(chinese_text, sino_vietnamese_text)
                print(f"Number of Chinese parts: {len(zh_parts)}")
                print(f"Number of Sino-Vietnamese parts: {len(vi_parts)}")

                self.assertEqual(len(zh_parts), len(vi_parts), "Number of Chinese and Sino-Vietnamese parts should be equal")
                self.assertGreater(len(zh_parts), 1, "There should be more than one part")

                for i, (zh_part, vi_part) in enumerate(zip(zh_parts, vi_parts)):
                    print(f"Part {i + 1}:")
                    zh_paragraphs = zh_part.split('\n')
                    vi_paragraphs = vi_part.split('\n')
                    print(f"Chinese characters: {len(zh_part)}")
                    print(f"Chinese paragraphs: {len(zh_paragraphs)}")
                    print(f"Sino-Vietnamese characters: {len(vi_part)}")
                    print(f"Sino-Vietnamese paragraphs: {len(vi_paragraphs)}")
                    self.assertGreater(len(zh_part), 0, f"Chinese part {i + 1} should not be empty")
                    self.assertGreater(len(vi_part), 0, f"Sino-Vietnamese part {i + 1} should not be empty")
                    self.assertEqual(len(zh_paragraphs), len(vi_paragraphs), f"Number of paragraphs in part {i + 1} should be equal for both languages")
            else:
                self.fail("Could not find ZH and VI tags in TestSplit.txt")
        except Exception as e:
            self.fail(f"Error in test_split_text_from_file: {str(e)}")

if __name__ == '__main__':
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestSplitIntoParts)
    unittest.TextTestRunner(verbosity=2).run(test_suite)
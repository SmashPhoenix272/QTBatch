import unittest
import sys
import os
import traceback
import time

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

class TestProofreadRecursive(unittest.TestCase):
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

    def test_proofread_recursive_even(self):
        print("Running test_proofread_recursive_even")
        chinese_text = "段落1。\n段落2。\n段落3。\n段落4。"
        sino_vietnamese_text = "Đoạn 1.\nĐoạn 2.\nĐoạn 3.\nĐoạn 4."
        result = self.proofreader._proofread_recursive(chinese_text, sino_vietnamese_text, [], "test_file", 3)
        print(f"Result: {result}")
        self.assertEqual(len(result.split('\n')), 4)
        self.assertTrue(all(part.strip() for part in result.split('\n')))  # All parts should be non-empty

    def test_proofread_recursive_empty(self):
        print("Running test_proofread_recursive_empty")
        chinese_text = ""
        sino_vietnamese_text = ""
        result = self.proofreader._proofread_recursive(chinese_text, sino_vietnamese_text, [], "test_file", 3)
        print(f"Result: {result}")
        self.assertEqual(result, "")

    def test_proofread_recursive_uneven_paragraphs(self):
        print("Running test_proofread_recursive_uneven_paragraphs")
        chinese_text = "段落1。\n段落2。\n段落3。"
        sino_vietnamese_text = "Đoạn 1.\nĐoạn 2.\nĐoạn 3."
        result = self.proofreader._proofread_recursive(chinese_text, sino_vietnamese_text, [], "test_file", 3)
        print(f"Result: {result}")
        self.assertEqual(len(result.split('\n')), 3)
        self.assertTrue(all(part.strip() for part in result.split('\n')))  # All parts should be non-empty

    def test_proofread_recursive_chinese(self):
        print("Running test_proofread_recursive_chinese")
        chinese_text = "第一段。这是第一段的内容。\n第二段。这是第二段的内容。\n第三段。这是第三段的内容。"
        sino_vietnamese_text = "Đoạn đầu tiên. Đây là nội dung của đoạn đầu tiên.\nĐoạn thứ hai. Đây là nội dung của đoạn thứ hai.\nĐoạn thứ ba. Đây là nội dung của đoạn thứ ba."
        result = self.proofreader._proofread_recursive(chinese_text, sino_vietnamese_text, [], "test_file", 3)
        print(f"Result: {result}")
        self.assertEqual(len(result.split('\n')), 3)
        self.assertTrue(all("。" in part for part in chinese_text.split('\n')))  # Each part should contain full sentences
        self.assertTrue(all("." in part for part in result.split('\n')))  # Each part should contain full sentences

    def test_proofread_recursive_long_text(self):
        print("Running test_proofread_recursive_long_text")
        chinese_text = "长段落。\n" * 100
        sino_vietnamese_text = "Đoạn dài.\n" * 100
        result = self.proofreader._proofread_recursive(chinese_text, sino_vietnamese_text, [], "test_file", 3)
        print(f"Result length: {len(result)}")
        self.assertEqual(len(result.split('\n')), 100)
        self.assertTrue(all(part.strip() for part in result.split('\n')))  # All parts should be non-empty

    def test_proofread_recursive_real_content(self):
        print("Running test_proofread_recursive_real_content")
        with open('TestSplit.txt', 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Split the content into Chinese and Sino-Vietnamese parts
        zh_content = text.split('<ZH>')[1].split('</ZH>')[0].strip()
        vi_content = text.split('<VI>')[1].split('</VI>')[0].strip()

        # Test proofreading both Chinese and Sino-Vietnamese content
        result = self.proofreader._proofread_recursive(zh_content, vi_content, [], "test_file", 3)
        print(f"Result length: {len(result)}")
        self.assertTrue(len(result) > 0)
        self.assertTrue(all(part.strip() for part in result.split('\n')))  # All parts should be non-empty
        print("Chinese and Sino-Vietnamese content proofread successfully")

        # Check if the result has a similar number of paragraphs as the input
        zh_paragraphs = zh_content.split('\n')
        vi_paragraphs = vi_content.split('\n')
        result_paragraphs = result.split('\n')

        print(f"Chinese content paragraphs: {len(zh_paragraphs)}")
        print(f"Sino-Vietnamese content paragraphs: {len(vi_paragraphs)}")
        print(f"Result paragraphs: {len(result_paragraphs)}")

        self.assertTrue(abs(len(result_paragraphs) - len(zh_paragraphs)) <= 1)
        self.assertTrue(abs(len(result_paragraphs) - len(vi_paragraphs)) <= 1)
        print("Result has a similar number of paragraphs as the input")

if __name__ == '__main__':
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestProofreadRecursive)
    unittest.TextTestRunner(verbosity=2).run(test_suite)
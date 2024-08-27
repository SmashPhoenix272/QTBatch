import unittest
from QuickTranslator import convert_to_sino_vietnamese, rephrase, replace_special_chars
from models.trie import Trie

class TestQuickTranslator(unittest.TestCase):
    def setUp(self):
        self.names2 = Trie()
        self.names = Trie()
        self.viet_phrase = Trie()
        self.chinese_phien_am = {}

        # Add some test data
        self.names2.insert("张三", "Trương Tam")
        self.names.insert("李四", "Lý Tứ")
        self.viet_phrase.insert("你好", "Xin chào")
        self.chinese_phien_am = {"我": "Ngã", "是": "Thị"}

    def test_convert_to_sino_vietnamese(self):
        text = "张三和李四说你好，我是中国人。"
        expected = "Trương Tam và Lý Tứ nói Xin chào, Ngã Thị trung quốc nhân."
        result = convert_to_sino_vietnamese(text, self.names2, self.names, self.viet_phrase, self.chinese_phien_am)
        self.assertEqual(result, expected)

    def test_rephrase(self):
        tokens = ["hello", " ", "world", "!", " ", "how", " ", "are", " ", "you", "?"]
        expected = "Hello world! How are you?"
        result = rephrase(tokens)
        self.assertEqual(result, expected)

    def test_replace_special_chars(self):
        text = "这是一个测试。"
        expected = "Đây là một bài kiểm tra."
        result = replace_special_chars(text)
        self.assertEqual(result, expected)

if __name__ == '__main__':
    unittest.main()
import unittest
from name_analyzer import HanLPAnalyzer

class TestHanLPAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = HanLPAnalyzer('test_novel.txt', 'test_dictionary.txt')

    def test_read_dictionary(self):
        self.analyzer.dictionary_path = 'test_dictionary.txt'
        with open('test_dictionary.txt', 'w', encoding='utf-8') as f:
            f.write("张=Trương\n李=Lý\n")
        
        result = self.analyzer.read_dictionary()
        self.assertEqual(result, {"张": "Trương", "李": "Lý"})

    def test_translate_to_sino_vietnamese(self):
        self.analyzer.dictionary_mapping = {"张": "Trương", "三": "Tam"}
        result = self.analyzer.translate_to_sino_vietnamese("张三")
        self.assertEqual(result, "Trương Tam")

    def test_split_sentence(self):
        sentence = "这是一个很长的句子，需要被分割成多个部分。"
        result = self.analyzer.split_sentence(sentence, max_chars=10)
        self.assertEqual(len(result), 3)
        self.assertTrue(all(len(part) <= 10 for part in result))

    def test_update_entity_info(self):
        entities = [
            {'entity': '张三', 'type': 'PERSON'},
            {'entity': '北京', 'type': 'LOCATION'},
            {'entity': '张三', 'type': 'PERSON'}
        ]
        self.analyzer.update_entity_info(entities)
        self.assertEqual(self.analyzer.entity_info['张三']['category'], 'PERSON')
        self.assertEqual(self.analyzer.entity_info['张三']['appearances'], 2)
        self.assertEqual(self.analyzer.entity_info['北京']['category'], 'LOCATION')
        self.assertEqual(self.analyzer.entity_info['北京']['appearances'], 1)

if __name__ == '__main__':
    unittest.main()
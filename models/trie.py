from typing import Dict, List, Tuple, Optional

class TrieNode:
    __slots__ = ['children', 'is_end_of_word', 'value']
    def __init__(self):
        self.children: Dict[str, 'TrieNode'] = {}
        self.is_end_of_word: bool = False
        self.value: Optional[str] = None

class Trie:
    def __init__(self):
        self.root: TrieNode = TrieNode()
        self.word_count: int = 0

    def insert(self, word: str, value: str) -> None:
        current = self.root
        for char in word:
            if char not in current.children:
                current.children[char] = TrieNode()
            current = current.children[char]
        current.is_end_of_word = True
        current.value = value
        self.word_count += 1

    def batch_insert(self, words: List[Tuple[str, str]]) -> None:
        for word, value in words:
            self.insert(word, value)

    def count(self) -> int:
        return self.word_count

    def find_longest_prefix(self, text: str) -> Tuple[str, Optional[str]]:
        current = self.root
        longest_prefix = ""
        longest_value = None
        prefix = []
        for i, char in enumerate(text):
            if char not in current.children:
                break
            current = current.children[char]
            prefix.append(char)
            if current.is_end_of_word:
                longest_prefix = ''.join(prefix)
                longest_value = current.value
        return longest_prefix, longest_value
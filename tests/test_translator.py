import unittest
from translator import BalancedTranslator

class TranslatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = BalancedTranslator(flair_probability=0)

    def check(self, source, expected):
        self.assertEqual(self.t.translate(source), expected)

    def test_questions(self):
        self.check("Can you help me?", "Canst thou help me?")
        self.check("How are you?", "How art thou?")

    def test_negation(self):
        self.check("I don't know.", "I know not.")

    def test_pronouns(self):
        self.check("I saw you yesterday.", "I saw thee yesterday.")
        self.check("Your friend is here.", "Thy good fellow is here.")

    def test_ambiguity(self):
        self.check("The fire is hot.", "The fire is hot.")
        self.check("I drank tea.", "I drank tea.")

    def test_protected(self):
        self.check("Hello <@12345>, see https://example.com/you",
                   "Well met <@12345>, see https://example.com/you")
        self.check("Hello "+chr(96)+"you are"+chr(96),
                   "Well met "+chr(96)+"you are"+chr(96))

    def test_single_pass(self):
        self.check("You are great.", "Thou art splendid.")
        self.check("You will see.", "Thou wilt see.")

if __name__ == "__main__":
    unittest.main()

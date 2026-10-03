import unittest

from golden_pot.i18n import LANGUAGES, TRANSLATIONS, translate


class TranslationTests(unittest.TestCase):
    def test_all_languages_have_every_english_key(self) -> None:
        expected = set(TRANSLATIONS["en"])
        for language in LANGUAGES:
            self.assertEqual(expected, set(TRANSLATIONS[language]), language)

    def test_unknown_language_falls_back_to_english(self) -> None:
        self.assertEqual("Analyze folders", translate("unknown", "analyze"))


if __name__ == "__main__":
    unittest.main()

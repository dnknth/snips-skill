import unittest
from unittest.mock import patch

from snips_skill import i18n


class TranslationTest(unittest.TestCase):
    def test_fallback_when_locale_unset(self):
        with patch(
            "snips_skill.i18n.locale.getlocale", return_value=(None, None)
        ) as getlocale:
            gettext, ngettext = i18n.get_translations("/tmp/test", "some_domain")
        getlocale.assert_called_once()
        self.assertEqual(gettext("kitchen"), "kitchen")
        self.assertEqual(ngettext("one", "many", 1), "one")
        self.assertEqual(ngettext("one", "many", 2), "many")

    def test_cache_identity(self):
        first = i18n.get_translations("/tmp/cache", "some_domain")
        second = i18n.get_translations("/tmp/cache", "some_domain")
        self.assertIs(first, second)


class RoomNameTest(unittest.TestCase):
    def test_rooms_keys_are_lowercase(self):
        for key in i18n.ROOMS:
            self.assertEqual(key, key.lower())

    def test_room_with_article_known(self):
        self.assertEqual(i18n.room_with_article("kitchen"), "the kitchen")

    def test_room_with_article_unknown(self):
        self.assertEqual(i18n.room_with_article("cellar"), "the cellar")

    def test_room_with_preposition_known(self):
        self.assertEqual(i18n.room_with_preposition("kitchen"), "in the kitchen")

    def test_room_with_preposition_unknown(self):
        self.assertEqual(i18n.room_with_preposition("cellar"), "in the cellar")


if __name__ == "__main__":
    unittest.main()

import os
import unittest
from unittest.mock import patch
from codex_cockpit import i18n


class LocaleTests(unittest.TestCase):
    def tearDown(self):
        i18n.use('auto')

    def test_generic_tooling_locale_does_not_hide_desktop_language(self):
        with patch.dict(os.environ, {'LC_ALL':'C.UTF-8', 'LANG':'pt_BR.UTF-8'}, clear=True):
            self.assertEqual(i18n.detect(), ('pt', 'pt-BR'))

    def test_language_preference_list(self):
        with patch.dict(os.environ, {'LANGUAGE':'de:pt_BR:en', 'LANG':'en_US.UTF-8'}, clear=True):
            self.assertEqual(i18n.detect(), ('pt', 'pt-BR'))

    def test_english_and_fallback(self):
        for env in ({'LANG':'en_US.UTF-8'}, {'LC_ALL':'POSIX'}, {'LANG':'ja_JP.UTF-8'}, {}):
            with patch.dict(os.environ, env, clear=True):
                self.assertEqual(i18n.detect(), ('en', 'en-US'))

    def test_explicit_override_and_aliases(self):
        with patch.dict(os.environ, {'LANG':'pt_BR.UTF-8'}, clear=True):
            i18n.use('en')
            self.assertEqual(i18n.t('open_dashboard'), 'Open dashboard')
            for alias in ('pt', 'pt_BR', 'pt-BR', 'pt_BR.UTF-8'):
                i18n.use(alias)
                self.assertEqual(i18n.t('open_dashboard'), 'Abrir dashboard')
                self.assertEqual(i18n.money(1234.56), 'US$ 1.234,56')

    def test_catalogues_have_matching_keys_and_placeholders(self):
        from string import Formatter
        english = i18n.CATALOG['en']
        portuguese = i18n.CATALOG['pt']
        self.assertEqual(set(english), set(portuguese))
        def fields(text):
            return {name for _, name, _, _ in Formatter().parse(text) if name}
        for key, text in english.items():
            self.assertEqual(fields(text), fields(portuguese[key]), key)

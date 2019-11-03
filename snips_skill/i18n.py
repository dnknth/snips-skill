import gettext as gettext_module, locale, os
from threading import local


_TRANSLATIONS = { None: gettext_module.NullTranslations() }
_CURRENT = local()
_CURRENT.locale = 'en_US'

_DEFAULT_LOCALE_PATH = os.path.join( os.path.dirname(__file__), 'locale')


def get_translation():
    try:
        return _TRANSLATIONS[_CURRENT.locale]
    except (AttributeError, KeyError):
        return _TRANSLATIONS[None]


def use_language( language, domain='messages', path=None):
    """
        Set 'language' as current locale.
        Optionally search for locale in directory 'path'.
        :param locale: language name, eg 'en_GB'
    """
    
    if path is None:
        path = _DEFAULT_LOCALE_PATH
    if locale not in _TRANSLATIONS:
        translation = gettext_module.translation( domain, path, [language])
        _TRANSLATIONS[language] = translation
    _CURRENT.locale = language
    return _TRANSLATIONS[language]


def get_language():
    return _CURRENT.locale


def gettext( message):
    return get_translation().gettext(message)


def ngettext( message, plural, num):
    return get_translation().ngettext(message, plural, num)

import gettext, locale, os

# Install translations
_language, _encoding = locale.getlocale()
_translation = gettext.translation( 'messages', 
    languages=[_language], fallback=True,
    localedir=os.path.join( os.path.dirname( __file__), 'locale'))
_  = _translation.gettext
ngettext = _translation.ngettext
del _language, _encoding, _translation

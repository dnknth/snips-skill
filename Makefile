export PATH := $(PATH)/opt/homebrew/bin:/usr/local/bin
export SNIPS_CONFIG = /usr/local/etc/snips.toml

POT = snips_skill/locale/snips_skill.pot
LOCALE = snips_skill/locale/de/LC_MESSAGES/snips_skill.po
SOURCES = $(wildcard snips_skill/*.py)

log: $(POT) .venv3
	.venv3/bin/python3 -m snips_skill

trace:
	.venv3/bin/python3 -m snips_skill.mqtt -H home -j

test:
	.venv3/bin/python3 -m unittest discover snips_skill

messages: $(POT)

$(POT): $(SOURCES)
	xgettext -L python -o $@ $^

%.mo: %.po
	msgfmt -o $@ $<

clean:
	rm -rf build dist *.egg-info __pycache__

tidy: clean
	rm -rf .venv3

dist: setup.cfg .venv3 $(LOCALE:.po=.mo) $(POT)
	.venv3/bin/python3 -m build -n
	
pypi: clean dist
	.venv3/bin/twine upload dist/*

.venv3:
	[ -d $@ ] || python3 -m venv $@
	.venv3/bin/pip3 install -U pip wheel build twine
	.venv3/bin/pip3 install --editable .
	touch $@

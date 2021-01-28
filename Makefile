GETTEXT = /usr/local/opt/gettext

POT = snips_skill/locale/snips_skill.pot
LOCALE = snips_skill/locale/de/LC_MESSAGES/snips_skill.po
SOURCES = $(wildcard snips_skill/*.py)

log: $(POT) .venv3
	.venv3/bin/python3 -m snips_skill

trace:
	.venv3/bin/python3 -m snips_skill.mqtt -H home -j

build: $(LOCALE:.po=.mo) $(POT)
	python3 setup.py build

test:
	.venv3/bin/python3 -m snips_skill.test -s study tests/*.json

.venv3: setup.cfg
	[ -d $@ ] || python3 -m venv $@
	.venv3/bin/pip3 install -U pip wheel
	.venv3/bin/pip3 install --editable .
	touch $@

messages: $(POT)

$(POT): $(SOURCES)
	$(GETTEXT)/bin/xgettext -L python -o $@ $^

%.mo: %.po
	$(GETTEXT)/bin/msgfmt -o $@ $<

clean:
	rm -rf build dist *.egg-info

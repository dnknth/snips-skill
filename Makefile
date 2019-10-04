GETTEXT = /usr/local/opt/gettext

POT = snips_skill/locale/messages.pot
LOCALE = snips_skill/locale/de/LC_MESSAGES/messages.po

build: $(LOCALE:.po=.mo) $(POT)
	python3 setup.py build

.venv3: requirements.txt
	[ -d $@ ] || python3 -m venv $@
	.venv3/bin/pip3 install -r $<
	touch $@

messages: $(POT)

$(POT): snips_skill/multi_room.py
	$(GETTEXT)/bin/xgettext -L python -o $@ $^

%.mo: %.po
	$(GETTEXT)/bin/msgfmt -o $@ $<

clean:
	rm -rf build *.egg-info $(LOCALE:.po=.mo)

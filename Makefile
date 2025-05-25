export PATH := $(PATH)/opt/homebrew/bin:/usr/local/bin
export SNIPS_CONFIG = /usr/local/etc/snips.toml

POT = snips_skill/locale/snips_skill.pot
LOCALE = snips_skill/locale/de/LC_MESSAGES/snips_skill.po
SOURCES = $(wildcard snips_skill/*.py)

log: $(POT) .venv
	uv run intent-log

trace:
	uv run mqtt-log -H home -j

recordings:
	mkdir -p $@
	uv run recorder -d $@ --loop

test:
	.venv/bin/python3 -m unittest discover snips_skill

messages: $(POT)

$(POT): $(SOURCES)
	xgettext -L python -o $@ $^

%.mo: %.po
	msgfmt -o $@ $<

clean:
	rm -rf build dist *.egg-info __pycache__

tidy: clean
	rm -rf .venv

dist: pyproject.toml .venv $(LOCALE:.po=.mo) $(POT)
	uv build
	
pypi: clean dist
	uv publish dist/*

.venv:
	uv sync

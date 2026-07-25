# AGENTS.md

## Project overview

`snips-skill` is a Python library providing boilerplate-free helpers for building
Snips/Hermes MQTT skills (voice assistant actions). It wraps `paho-mqtt`, adds
intent/session decorators, state tracking, scheduling, multi-room config, and
i18n helpers. MIT-licensed, maintained by `dnknth`, published on PyPI.

## Layout

- `snips_skill/` — the library package (imported as `snips_skill`).
- `tests/` — unit tests, one `test_*.py` per module, using `unittest`.
- `snips_skill/locale/` — gettext catalogs (`pot`/`po`/`mo`), German (`de`) currently.
- `recordings/` — sample intent recordings used as test fixtures.
- `build/`, `dist/`, `*.egg-info` — generated artifacts (gitignored).

## Key modules (all exported from `snips_skill/__init__.py`)

- `mqtt.py` — `MqttClient`, `CommandLineClient`, `@topic`, `decode_json`.
- `snips.py` — `SnipsClient` and `@on_*` session event decorators.
- `skill.py` — `Skill` base class, `@intent`, `@min_confidence`, `@require_slot`.
- `state.py` — `StateAwareMixin`, `@when`, `@conditional`; depends on `expr.py`.
- `expr.py` — boolean-expression parser (PLY) used by state tracking.
- `tasks.py` — `Scheduler`, `Tasks` priority queue, `@cron`, `@delay`.
- `multi_room.py` — `MultiRoomConfig`, room helpers.
- `i18n.py` — `get_translations`, `room_with_article`, `room_with_preposition`.
- `intent.py` — `IntentPayload` (pydantic model of intent JSON).
- `log.py` — `LoggingMixin`; `exceptions.py` — `SnipsError`, `SnipsClarificationError`.
- `dialogue.py` — internal pydantic session-init payload models (`ActionInit`, `NotificationInit`, ...), used by `snips.py`/`recorder.py`; NOT re-exported from `__init__.py`.
- `__main__.py` — `intent-log` CLI entry point; `recorder.py` — `recorder` CLI.

## Generated files (gotcha)

- `expr.py` uses PLY, which writes `parser.out` and `parsetab.py` into `snips_skill/` at import time. `parser.out` is gitignored; `parsetab.py` is committed. Don't treat them as source.

## Conventions

- Python `>=3.12`, uses modern typing (`str | None`, `Callable`, `ClassVar`).
- Type hints on all public functions and methods; docstrings in double quotes
  (single-sentence summaries).
- Classes are mixins: `class MySkill(StateAwareMixin, Skill)` — mixins come first.
- Decorators (`@intent`, `@when`, `@cron`, etc.) wrap methods (`self, userdata, msg`)
  or standalone functions (`client, userdata, msg`).
- Each module defines `__all__`; the public API is re-exported in `__init__.py`
  and the version lives there (`__version__`).
- Do not add comments unless needed; the codebase keeps them minimal.

## Tooling

- Package manager: `uv` (see `uv.lock`). Sync with `uv sync`.
- Tests: `unittest` discovery (`tests/`), not pytest.
  - Local: `make test` (runs `.venv/bin/python3 -m unittest discover -s tests`).
  - CI: `uv run -w unittest-xml-reporting -m xmlrunner discover -s tests` (see `.github/workflows/ci.yml`).
- Linting/formatting: Ruff (configured as the default formatter in `.vscode/settings.json`).
- Coverage: `coverage` dev dependency; `.coverage` present in repo root.

## Makefile targets

- `test` — run unit tests. `messages` — regenerate the `.pot` from sources via `xgettext`.
- `dist` — build the package (`uv build`). `pypi` — clean + build + `uv publish` (pulls the token via the `pass` password manager: `` uv publish --token `pass token/pypi.org` dist/* ``).
- `log` — run `intent-log`; `trace` — run `mqtt-log -H home -j`; `recordings` — run recorder.
- `clean` / `tidy` — remove build artifacts / `.venv` respectively.
- The Makefile exports `SNIPS_CONFIG=/usr/local/etc/snips.toml` and prepends brew paths to `PATH`; these env vars apply to any `make` target.

## Commands to verify work

```sh
make test                      # run the full test suite
uv run ruff check snips_skill tests   # lint (ruff is the configured linter)
```

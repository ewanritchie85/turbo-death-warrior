# Configuration lives in .env (TDW_HOST / TDW_PORT).
# Override on the command line if needed:  make run PORT=9000

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
RUN_ENV = $(if $(HOST),TDW_HOST=$(HOST)) $(if $(PORT),TDW_PORT=$(PORT))

.PHONY: run check test requirements clean

run:
	$(RUN_ENV) $(PYTHON) -m turbo_death_warrior.server

check:
	$(PYTHON) -m py_compile src/turbo_death_warrior/server.py src/turbo_death_warrior/game_engine.py

requirements:
	$(PYTHON) -m pip install -r requirements.txt

test: requirements
	$(PYTHON) -m pytest test/ -v

clean:
	rm -rf __pycache__ .pytest_cache src/turbo_death_warrior/__pycache__
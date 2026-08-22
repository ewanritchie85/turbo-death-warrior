# Configuration lives in .env (TDW_HOST / TDW_PORT).
# Override on the command line if needed:  make run PORT=9000

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
RUN_ENV = $(if $(HOST),TDW_HOST=$(HOST)) $(if $(PORT),TDW_PORT=$(PORT))

.PHONY: run check test requirements clean

run:
	$(RUN_ENV) $(PYTHON) server.py

check:
	$(PYTHON) -m py_compile server.py game_engine.py

requirements:
	$(PYTHON) -m pip install -r requirements.txt

test: requirements
	$(PYTHON) -m pytest test_game_engine.py -v

clean:
	rm -rf __pycache__ .pytest_cache

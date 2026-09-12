.PHONY: help install replay run run-fast test report clean

help:
	@echo "make install   install dependencies"
	@echo "make replay    reproduce the published numbers from the committed cache (no API key)"
	@echo "make run       run the full benchmark live (needs GEMINI_API_KEY)"
	@echo "make run-fast  run only the two cheap arms, live"
	@echo "make test      run the offline test suite"
	@echo "make report    print the committed report"

install:
	python3 -m pip install -r requirements.txt

replay:
	python3 -m src.benchmark run --offline

run:
	python3 -m src.benchmark run

run-fast:
	python3 -m src.benchmark run --agents rag,closedbook

test:
	python3 -m pytest tests -q

report:
	@cat results/latest/report.md

clean:
	rm -rf __pycache__ src/__pycache__ tests/__pycache__ .pytest_cache

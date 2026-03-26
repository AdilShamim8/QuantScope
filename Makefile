.PHONY: run serve test docker clean

run:
	python main.py --symbols AAPL MSFT NVDA 7203.T VOD.L RELIANCE.NS

serve:
	python main.py --serve

dev:
	uvicorn api.app:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v --cov=core --cov=llm --cov-report=term-missing

docker:
	docker-compose up --build

clean:
	rm -rf output/*.csv output/*.json output/logs/*.log
	rm -rf __pycache__ */__pycache__ .pytest_cache .coverage
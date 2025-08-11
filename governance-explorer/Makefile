.PHONY: setup dev run
setup:
	python3 -m venv .venv && . .venv/bin/activate && pip install -U pip -r requirements.txt
dev:
	. .venv/bin/activate && streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0
run:
	streamlit run src/app.py --server.port=8501 --server.address=0.0.0.0

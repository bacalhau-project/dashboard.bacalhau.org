web: smashing start -p $PORT
build: poetry install && poetry run python3 raw_data/download.py
rebuild: poetry install && FROM_SCRATCH=true poetry run python3 raw_data/download.py

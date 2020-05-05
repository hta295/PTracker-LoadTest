# Default parameters for load test
TARGET_PORT=8000
NUM_ITERATIONS=15
ITERATION_LENGTH_SECONDS=180
START_NUM_WORKERS=30
NUM_WORKERS_SKIP=10
OUTPUT_CSV_FILENAME=data.csv


# Kill any ptracker servers in docker
kill-server:
	for i in `docker ps | awk '/ptracker-server/{print $$1}'`; do \
		docker kill $$i; \
	done

# Launch ptracker server container in docker and forward web server endpoint to TARGET_PORT on localhost
server:
	docker run -p ${TARGET_PORT}:80 ptracker-server &

# Install dependencies for load tester
reqs:
	pip3 install -r requirements.txt

# Runs load test against ptracker server in docker w/ port forwarded to TARGET_PORT on localhost
load-test: clean kill-server server
	sleep 2
	./main.py -u http://localhost:$(TARGET_PORT) -n $(NUM_ITERATIONS) -l $(ITERATION_LENGTH_SECONDS) -w $(START_NUM_WORKERS) -s $(NUM_WORKERS_SKIP) -f $(OUTPUT_CSV_FILENAME)

# Unit tests for load test
test:
	coverage run -m pytest -s tests.py
	coverage report -m

# Cleans the load tester package
clean:
	rm -f $(OUTPUT_CSV_FILENAME)

.PHONY: clean init

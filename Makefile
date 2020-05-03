# Default parameters for load test
OUTPUT_CSV_FILENAME=data.csv
TARGET_PORT=8000

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
load: check-num-workers clean kill-server server
	sleep 3
	./main.py -u http://localhost:$(TARGET_PORT) -n $(NUM_WORKERS) -f $(OUTPUT_CSV_FILENAME)

# Unit tests for load test
test:
	coverage run -m pytest -s tests.py
	coverage report -m

# Validates NUM_WORKERS was defined in make call
check-num-workers:
ifndef NUM_WORKERS
	$(error NUM_WORKERS is undefined)
endif

# Cleans the load tester package
clean:
	rm -f $(OUTPUT_CSV_FILENAME)

.PHONY: clean init

# PTracker-LoadTest

## Overview

Spins up a pool of worker threads which simulate load against the [PTracker](https://github.com/hta295/PTracker) web service.

*This is not standardized load testing tooling and is primarily for demonstrative purposes.*

## Package Structure

* `requirements.txt` - list of `pip3` package dependencies
* `ptracker_loadtest/` - source files
	* `load_test.py` - entry point to the load test
	* `metrics.py` - class definition for global metrics container
	* `utils/` - common utility module. __User needs to create a `secrets.py` file which defines a `TEST_USER` and `TEST_PASSWORD`__

## Usage

### Automated - Makefile

This spins up a `ptracker-server` container (killing those that already exist) and runs the load test against it, outputting the results to `data.csv`. This method *does not* assume PTracker is running already and offers end-to-end automation for setup and the actual load testing. To run:

```
make load NUM_WORKERS=<int>
```

* `NUM_WORKERS`: maximum number of worker threads to create (each thread makes calls to PTracker in a tight loop)

### Manual

This method provides finer-granularity, but it assumes that a PTracker web service is running at the `root_url` already. To run:

```
ptracker_loadtest/load_test.py -u root_url [-n num_workers] [-f csv_output_filename]
```

* `root_url`: The root url for the running PTracker web server (e.g. `http://localhost:8000`)
* `num_workers`: maximum number of worker threads to create (each thread makes calls to PTracker in a tight loop) 
* `csv_output_filename`: filename for the csv to write load test results to

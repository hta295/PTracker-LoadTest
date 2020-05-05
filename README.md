# PTracker-LoadTest

## Overview

Performs a series of load tests against the PTracker web service and writes the results to a csv file (1 row per test)

Each test spins up a pool of worker threads which simulate load against the [PTracker](https://github.com/hta295/PTracker) web service.

*This is not standardized load testing tooling and is primarily for demonstrative purposes.*

## Package Structure

* `main.py` - entry point for the load test
* `Makefile` - make directives to automate build and testing
* `requirements.txt` - list of `pip3` package dependencies
* `tests.py` - unit tests for load test
* `ptracker_loadtest/` - source files
	* `load_test.py` - controller for the load test
	* `metrics.py` - class definition for global metrics container
	* `ptracker_session.py` - class definition for an http session to PTracker web server
	* `thread_factory.py` - class definition for static factory that builds threads for the test
	* `utils/` - common utility module. __User needs to create a `secrets.py` file which defines a `TEST_USER` and `TEST_PASSWORD`__

## Usage

### Automated - Makefile

This spins up a `ptracker-server` container (killing those that already exist) and runs the load tests against it, outputting the results to `data.csv`. This method *does not* assume PTracker is running already and offers end-to-end automation for setup and the actual load testing. To run:

```
make load-test
```

The test is run with default parameters (see `Makefile`)

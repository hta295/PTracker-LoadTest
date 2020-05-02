# PTracker-LoadTest

## Overview

Spins up a pool of worker threads which simulate load against the PTracker web service

## Package Structure

* `requirements.txt` - list of `pip3` package dependencies
* `ptracker_loadtest/` - source files
	* `load_test.py` - entry point to the load test
	* `metrics.py` - class definition for global metrics container
	* `utils/` - common utility module. __User needs to create a `secrets.py` file which defines a `TEST_USER` and `TEST_PASSWORD`__

## Usage

```
ptracker_loadtest/load_test.py -u root_url [-n num_workers] [-f csv_output_filename]
```

* root_url: The root url for the running PTracker web server (e.g. `http://localhost:8000`)
* num_workers: maximum number of worker threads to create (each thread makes calls to PTracker in a tight loop)
* csv_output_filename: filename for the csv to write load test results to

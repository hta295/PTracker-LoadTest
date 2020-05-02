# PTracker-LoadTest

## Overview

Spins up a pool of worker threads which simulate load against the PTracker web service

## Usage

```
python3 load_test.py -u root_url [-n num_workers] [-f csv_output_filename]
```

* root_url: The root url for the running PTracker web server (e.g. `http://localhost:8000`)
* num_workers: maximum number of worker threads to create (each thread makes calls to PTracker in a tight loop)
* csv_output_filename: filename for the csv to write load test results to

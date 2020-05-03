#!/usr/bin/env python3

import sys

import ptracker_loadtest.load_test as load_test


def main():
    load_test.run(sys.argv[1:])


if __name__ == '__main__':
    main()

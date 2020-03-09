# factfinder-migration
Code related to migration of the https://factfinder.census.gov/ website

Please see https://en.wikipedia.org/wiki/Wikipedia:US_Census_Migration

## transform.py
```
usage: transform.py [-h] [-i INFILE] [-o OUTFILE] [-s] [--continue-on-err]
                    [-v] [-q]
                    [url [url ...]]

Transform US Census American Fact Finder URLs into data.census.gov URLs

positional arguments:
  url                   AFF url(s) to convert

optional arguments:
  -h, --help            show this help message and exit
  -i INFILE, --infile INFILE
                        File containing AFF urls to convert, one on each line
  -o OUTFILE, --outfile OUTFILE
                        File to output converted URLs to
  -s, --strict          Causes warnings to be interpreted as errors
  --continue-on-err     Treats errors as warnings and continues processing.
                        URLs that could not be converted will become a blank
                        line.
  -v, --verbose         Print more information to stderr when things go wrong
  -q, --quiet           Print less information to stderr when things go wrong

If a URL is converted without issue, or with a warning, transform.py exits
with code 0. If a URL could not be converted, If conversion is not and will
not be possible, transform.py exits with code 1. but conversion might be
possible in the future, transform.py exits with code 2.
```

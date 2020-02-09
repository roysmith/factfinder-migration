#!/usr/bin/env python

import argparse
import re
import urllib.parse
from pathlib import Path

import mwclient

SITE = 'en.wikipedia.org'
USER_AGENT = 'User:RoySmith, factfinder'

def main():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    site = mwclient.Site(SITE, clients_useragent=USER_AGENT)
    ns_by_number = site.namespaces
    ns_by_name = {v: k for k, v in site.namespaces.items()}

    pages = site.exturlusage('factfinder.census.gov')
    for page in pages:
        print(page['title'])
    

if __name__ == '__main__':
    main()

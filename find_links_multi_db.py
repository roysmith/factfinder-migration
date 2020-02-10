#!/usr/bin/env python

import argparse
import re

import mwclient
import toolforge

SITE = 'en.wikipedia.org'
USER_AGENT = 'User:RoySmith, factfinder'

def main():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    db = toolforge.connect('enwiki')
    with db.cursor() as cur:
        cur.execute(
            """
            SHOW databases like '%wiki_p'
            """)
        db_names = [row[0] for row in cur.fetchall()]
            
    for db_name in db_names:
        db = toolforge.connect(db_name)
        with db.cursor() as cur:
            cur.execute(
                """
                SELECT el_to, count(el_from) as pages
                FROM externallinks
                WHERE el_index LIKE "https://gov.census.factfinder.%"
                OR el_index LIKE "http://gov.census.factfinder.%"
                GROUP BY el_to
                ORDER BY pages DESC
                """)
            for row in cur.fetchall():
                print(db_name, row)

    

if __name__ == '__main__':
    main()

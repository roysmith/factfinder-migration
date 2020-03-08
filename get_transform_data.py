#!/bin/env python3
# python 3.5+
# SPDX-License-Identifier: MIT

import json
import csv
import requests

codes = []


def get_topic_codes():
    def extract(item):
        if isinstance(item, dict):
            for key, value in item.items():
                if key == "code":
                    codes.append(value)
                else:
                    extract(value)
        elif isinstance(item, list):
            for litem in item:
                extract(litem)

    url = (
        "https://data.census.gov/api/search?y=2018&from=0&facets=topics&services=facets"
        "&d=ACS%201-Year%20Estimates%20Selected%20Population%20Profiles"
    )
    req = requests.get(url)
    req.raise_for_status()
    topics = req.json()["response"]["facets"]["topics"][9]

    extract(topics)

    allcodes = {}
    for code in codes:
        codeid, sep, codename = code.partition("-")
        if not codeid:
            codeid = sep + codename.partition("-")[0]

        allcodes[codeid.strip()] = code

    return allcodes


def get_cf_states():
    url = "https://www2.census.gov/geo/docs/reference/state.txt"
    req = requests.get(url)
    req.raise_for_status()
    reader = csv.DictReader(req.text.split("\n"), delimiter="|")
    data = {line["STATE"]: line["STATE_NAME"] for line in reader}
    return data


if __name__ == "__main__":
    data = {"topics": get_topic_codes(), "states": get_cf_states()}
    with open("transform_data.json", "w") as f:
        json.dump(data, f, sort_keys=True, indent=4)

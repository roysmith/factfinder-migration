#!/bin/env python3
# python 3.5+
# SPDX-License-Identifier: MIT

import json
import requests

codes = []


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

with open("topiccodes.json", "w") as f:
    json.dump(allcodes, f, sort_keys=True, indent=4)

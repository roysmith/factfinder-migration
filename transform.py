#!/bin/env python3
# python 3.5+
# SPDX-License-Identifier: MIT

import sys
from urllib.parse import urlencode
from collections import OrderedDict

aff_table = ("version", "lang", "program", "dataset", "product", "geoids", "codes")
aff_cf = ("version", "lang", "geo_type", "geo_name", "topic", "object")

cedsci = (
    "target",
    "q",  # query
    "t",  # topics
    "g",  # geoids, underscore list
    "y",  # year
    "d",  # dataset
    "n",  # NAICS code
    "p",  # product/service code(s)
    "table",  # table id
    "tid",  # {dataset}{year}.{table id}
    "comm",  # commodity code
    # table-specific parameters
    "hidePreview",
    "moe",
    "tp",
    # map-specific parameters
    "layer",
    "cid",
    "palette",
    "break",
    "classification",
    "mode",
    "vintage",
)


def main(raw_url):
    # remove protocol scheme
    scheme, sep, old_url = raw_url.partition("//")
    if not sep:
        raise ValueError("Malformed URL")

    # split into data fields
    domain, tool, target, *data = old_url.split("/")
    if tool not in {"bkmk"}:
        # bkmk links have well-defined information
        # faces links have little to no information
        # servlet links may have useful information, but are not well-defined
        raise ValueError("Not a stable deep link")

    # handle different endpoints differently
    if target == "table":
        new_url = table(data)
    # elif target == "navigation":
    #     new_url = navigation(data)
    # elif target == "qs":
    #     new_url = qs(data)
    elif target == "cf":
        new_url = cf(data)
    # elif target == "sm":
    #     new_url = sm(data)
    # elif target == "select":
    #     new_url = select(data)
    else:
        raise NotImplementedError("No transformation rule for that data type")

    return build_url(new_url)


def table(data):
    """Transforms AFF table URL data to CEDSCI table URL data"""
    raw_data = OrderedDict(zip(aff_table, data))
    survey, year, table_id = dataset_transform(
        raw_data["program"], raw_data["dataset"], raw_data["product"]
    )
    new_data = OrderedDict(
        target="table",
        g=pipe_to_underscore(raw_data.get("geoids", "")),
        y=year,
        tid=survey + year + "." + table_id,
    )
    return new_data


def navigation(raw_data):
    """AFF search results to CEDSCI search results"""
    raise NotImplementedError


def qs(raw_data):
    """AFF advanced search results to CEDSCI search results"""
    raise NotImplementedError


def cf(data):
    """AFF Community Facts"""
    # AFF linked to Community Facts by place name
    # CEDSCI links to Community Profiles by GEOID, but we can get around
    # that by using search instead
    raw_data = OrderedDict(zip(aff_cf, data))
    if raw_data["geo_type"] == "zip":
        raise KeyError("CEDSCI does not support profiles for zipcodes")
    new_data = OrderedDict(target="profile", q=raw_data["geo_name"])
    return new_data


def sm(raw_data):
    """Transforms AFF reference map to CEDSCI map"""
    raise NotImplementedError


def select(raw_data):
    """AFF overlay tabs"""
    raise NotImplementedError


def dataset_transform(program, dataset, ds_table):
    """Transforms an AFF dataset identifier into the corresponding CEDSCI tid

    Not all American FactFinder data has been moved to CEDSI.
    Some is avaliable in other systems or the census website, while
    other datasets will just plain become unavailable.
    """
    survey, year = "", ""
    # Programs not available at all
    if program in {"ASM", "COG", "CFS", "PEP"}:
        raise KeyError(program + " not yet available in CEDSCI")
    elif program in {"AHS", "PP", "GEP", "SSF", "SGF", "STC", "BES", "SLF"}:
        raise KeyError(program + " uses a different data access system")
    elif program == "EEO":
        raise KeyError("2010 EEO data not available on CEDSCI")
    elif program == "ECN":
        # TODO: Data likely exists, but tables don't line up
        raise NotImplementedError("ECN tables don't line up between AFF and CEDSCI")
    elif program == "BP":
        # TODO No matter what the US Census Bureau says, CB1600CZ21 != CB1600ZBP
        raise NotImplementedError(
            "Table IDs for business patterns are not consistent between AFF and CEDSCI"
        )
        year = dataset
        if int(year) < 2012 and survey == "CBP":
            raise KeyError("Pre-2012 County Business Patterns not available in CEDSCI")
    # Available or partially-available programs
    elif program == "ACS":
        new_table = ds_table
        year = "20" + dataset[0:2]
        if dataset.endswith("YR"):
            survey = "ACSDT" + dataset[3:5]
        else:
            raise KeyError("Dataset does not exist on CEDSCI")
        if int(year) < 2010:
            raise KeyError("Pre-2010 ACS data not available on CEDSCI")
    elif program == "DEC":
        decennial = {
            "113": "DECENNIALCD113",
            "115": "DECENNIALCD115",
            "SF1": "DECENNIALSF1",
        }
        year = "20" + dataset[0:2]
        survey = decennial.get(dataset[-3:])
        new_table = ds_table
        if not survey:
            raise KeyError("Decennial censusus data is not all available on CEDSCI")
    elif program == "NES":
        year = dataset
        survey = "NONEMP"
        new_table = "NS{0}00NONEMP".format(year[2:4])
        if int(year) < 2012:
            raise KeyError("Pre-2012 Nonemployer data not available on CEDSCI")
    elif program == "SBO":
        year = dataset
        new_table = "SB" + year[-2:] + ds_table
        if ds_table[-3] == "A":
            survey = "SBOCS"
        else:
            raise KeyError(
                "Survey of Business Owners tables other than "
                "the company summary are not available on CEDSCI"
            )

    if not (survey and year and new_table):
        raise KeyError(
            "{0}/{1} could not be transformed to a CEDSCI survey".format(
                program, dataset
            )
        )
    else:
        return survey, year, new_table


def pipe_to_underscore(pipelist):
    """Converts an AFF pipe-seperated list to a CEDSCI underscore-seperated list"""
    return pipelist.replace("|", "_")


def build_url(data):
    """Builds a CEDSCI url from a Cedsci named tuple"""
    assert set(data.keys()) <= set(cedsci)
    base = "https://data.census.gov/cedsci/{0}?".format(data.pop("target"))
    query = urlencode(OrderedDict((k, v) for k, v in sorted(data.items()) if v))
    return base + query


if __name__ == "__main__":
    if len(sys.argv) == 1 or sys.argv[1] == "-":
        input_src = sys.stdin
    else:
        input_src = sys.argv[1:]

    for line in input_src:
        if line:
            res = main(line.strip())
            print(res)

#!/bin/env python3
# python 3.5+
# SPDX-License-Identifier: MIT

import fileinput
import sys
from urllib.parse import urlencode

aff_table = ("version", "lang", "program", "dataset", "product", "geoids", "codes")

cedsci = frozenset(
    {
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
    }
)


def main(raw_url):
    # remove protocol scheme
    scheme, sep, old_url = raw_url.partition("//")
    if not sep:
        raise ValueError("Malformed URL")

    # split into data fields
    domain, tool, target, *raw_data = old_url.split("/")
    if tool not in {"bkmk"}:
        # bkmk links have well-defined information
        # faces links have little to no information
        # servlet links may have useful information, but are not well-defined
        raise ValueError("Not a stable deep link")

    data = dict(zip(aff_table, raw_data))

    # handle different endpoints differently
    if target == "table":
        new_url = table(data)
    # elif target == "navigation":
    #     new_url = navigation(data)
    # elif target == "qs":
    #     new_url = qs(data)
    # elif target == "cf":
    #     new_url = cf(data)
    # elif target == "sm":
    #     new_url = sm(data)
    # elif target == "select":
    #     new_url = select(data)
    else:
        raise NotImplementedError("No transformation rule for that data type")

    return build_url(new_url)


def table(raw_data):
    """Transforms AFF table URL data to CEDSCI table URL data"""
    survey, year, table_id = dataset_transform(
        raw_data["program"], raw_data["dataset"], raw_data["product"]
    )
    new_data = dict(
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


def cf(raw_data):
    """AFF Community Facts"""
    raise NotImplementedError


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
    assert set(data.keys()) <= cedsci
    base = "https://data.census.gov/cedsci/{0}?".format(data.pop('target'))
    query = urlencode({k: v for k, v in data.items() if v})
    return base + query


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] != "-":
        res = main(sys.argv[1].strip())
        print(res)
    else:
        for line in fileinput.input():
            if line:
                res = main(line.strip())
                print(res)

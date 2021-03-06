#!/bin/env python3
# python 3.5+
# SPDX-License-Identifier: MIT

import sys
from urllib.parse import urlencode, urlparse, parse_qs
from collections import OrderedDict
import warnings
import traceback
import json
import argparse
import os

__version__ = "1.2"

transform_data = os.path.join(os.path.dirname(__file__), "transform_data.json")

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


class Error(Exception):
    pass


class InputError(Error, ValueError):
    """Exception raised for errors from input, like an invalid URL"""

    def __init__(self, message):
        self.message = message


class UnsupportedCensusData(Error):
    """Exception raised for URLs where the data is unavailable on CEDSCI"""

    def __init__(self, message):
        self.message = message


class LowConfidenceTransformation(Warning, Error):
    """Warning raised for URLs where the script must make assumptions"""
    pass


def main(raw_url):
    # remove protocol scheme
    scheme, sep, old_url = raw_url.partition("//")
    if not sep:
        raise InputError("Input is not a valid URL")

    # remove query string
    old_url = old_url.partition("?")[0]
    # split into data fields
    domain, tool, target, *data = old_url.split("/")

    # handle different endpoints differently
    new_url = ""
    if tool == "bkmk":
        if target == "table":
            new_url = table(data)
        elif target == "cf":
            new_url = cf(data)
        else:
            raise NotImplementedError("No transformation rule for that data type")
    elif tool == "faces":
        parsed = urlparse(raw_url)
        path = parsed.path.split("/")[1:]
        data = OrderedDict(parse_qs(parsed.query))
        if path[-1] == "productview.xhtml":
            if "pid" in data.keys():
                new_url = productview_pid(data)
    elif tool == "servlet":
        parsed = urlparse(raw_url)
        tool, target = parsed.path.split("/")[1:]
        data = OrderedDict(parse_qs(parsed.query))
        if target in {"SAFFFacts", "ACSSAFFFacts", "SAFFPopulation"}:
            new_url = servlet_facts(data)
        else:
            new_url = servlet_table(target, data)

    if not new_url:
        raise InputError("Not a stable deep link")

    return build_url(new_url)


# /bkmk/
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
    codetype, _, raw_codes = raw_data.get("codes", "").partition("~")
    if codetype == "naics":
        new_data["n"] = pipe_to_underscore(raw_codes)
    elif codetype == "popgroup":
        new_data["t"] = popgroup_lookup(raw_codes)
    return new_data


def cf(data):
    """AFF Community Facts"""
    # AFF linked to Community Facts by place name
    # CEDSCI links to Community Profiles by GEOID, but we can get around
    # that by using search instead
    raw_data = OrderedDict(zip(aff_cf, data))
    if raw_data["geo_type"] == "zip":
        raise UnsupportedCensusData("CEDSCI does not support profiles for zipcodes")
    new_data = OrderedDict(target="profile", q=raw_data["geo_name"])
    return new_data


def servlet_table(servlet, data):
    """Transforms AFF /servlet/ links to CEDSCI table links"""
    keys = {"GCTTable": "-mt_name", "QTTable": "-qr_name", "DTTable": "-mt_name"}
    table_name = data.get(keys.get(servlet, ""), [""])[0]
    if not table_name:
        try:
            table_name = "_".join(
                (
                    data["-ds_name"][0],
                    data["-_box_head_nbr"][0],
                    data.get("-format", [""])[0].replace("-", ""),
                )
            )
        except KeyError:
            raise NotImplementedError(
                "No transformation rule for that servlet or insufficient data"
            )

    table_data = table_name.split("_")
    program, year, dataset = table_data[0:3]
    geoid = "_".join(data.get("-geo_id", data.get("geo_id", [""])))

    ds_table = table_data[4]
    if ds_table == "U":
        ds_table = table_data[5]

    survey, year, new_table = dataset_transform(program, dataset, ds_table, year)
    new_data = OrderedDict(
        target="table", g=geoid, y=year, tid=survey + year + "." + new_table
    )
    warnings.warn(
        "Servlet transformations are untesed, this link may not work.",
        LowConfidenceTransformation,
    )
    return new_data


def servlet_facts(data):
    """Convert servlet Community Facts links to CEDSCI profile"""
    raw_geo_id = data.get("geo_id", [""])[0]
    geo_lvc = raw_geo_id.partition("US")[0]
    # Some geographic identifiers seem to be missing geo component or variant
    if len(geo_lvc) == 5:
        # Use default value of 00 for missing component/varient
        geo_id = raw_geo_id[0:2] + "00" + raw_geo_id[2:]
    elif len(geo_lvc) == 7:
        # Prefix is correct length already, do nothing
        geo_id = raw_geo_id
    elif not raw_geo_id:
        # Construct a search query from URL data
        return OrderedDict(
            target="profile",
            q=data["_cityTown"][0] + ", " + short_state_id_to_name(data["_state"][0]),
        )
    else:
        raise InputError("Geographic Idnetifier is malformed")

    # Check if geo id indicates a zip code
    if geo_id[0:3] in {"850", "851", "860", "871"}:
        raise UnsupportedCensusData("CEDSCI does not support profiles for zipcodes")

    new_data = OrderedDict(target="profile", g=geo_id)
    return new_data


def short_state_id_to_name(stateid):
    """Converts a state-level GEOID to a state name. Requires transform_data.json"""
    with open(transform_data) as f:
        data = json.load(f)["states"]

    return data[stateid.partition("US")[2][-2:]]


def productview_pid(data):
    """Converts a productview.xhtml?pid= url"""
    pid = data["pid"]
    if isinstance(pid, list):
        pid = pid[0]
    pid_data = pid.split("_")
    program = pid_data[0]
    ds_table = pid_data[-1]
    dataset = "_".join(pid_data[1:-1])

    survey, year, table_id = dataset_transform(program, dataset, ds_table)
    new_data = OrderedDict(target="table", y=year, tid=survey + year + "." + table_id,)
    return new_data


def popgroup_lookup(popgroup_list):
    """Takes a pipe-seperated list of POPGROUP ID numbers
    and transforms them to a colon-seperated list of full strings

    Requires a transform_data.json file in the current working directory.
    One is included in this repo, but a new one can be generated with extractcodes.py

    Raises an exception if the POPGROUP is not found.
    """
    with open(transform_data) as f:
        popgroups = json.load(f)["topics"]

    popgroup_strs = []
    for popgroup_id in popgroup_list.split("|"):
        popgroup_strs.append(popgroups[popgroup_id])

    return ":".join(popgroup_strs)


def dataset_transform(program, dataset, ds_table, year=""):
    """Transforms an AFF dataset identifier into the corresponding CEDSCI tid

    Not all American FactFinder data has been moved to CEDSCI.
    Some is avaliable in other systems or the census website, while
    other datasets will just plain become unavailable.
    """
    survey = ""
    # Programs not available at all
    if program in {"ASM", "COG", "CFS", "PEP"}:
        raise UnsupportedCensusData(program + " not yet available in CEDSCI")
    elif program in {"AHS", "PP", "GEP", "SSF", "SGF", "STC", "BES", "SLF"}:
        raise UnsupportedCensusData(program + " uses a different data access system")
    elif program == "EEO":
        raise UnsupportedCensusData("2010 EEO data not available on CEDSCI")
    elif program == "ECN":
        # TODO: Data likely exists, but tables don't line up
        raise NotImplementedError("ECN tables don't line up between AFF and CEDSCI")
    elif program == "BP":
        # TODO No matter what the US Census Bureau says, CB1600CZ21 != CB1600ZBP
        raise NotImplementedError(
            "Table IDs for business patterns are not consistent between AFF and CEDSCI"
        )
        # year = dataset
        # if int(year) < 2012 and survey == "CBP":
        #     raise UnsupportedCensusData(
        #         "Pre-2012 County Business Patterns not available in CEDSCI"
        #     )
    # Available or partially-available programs
    elif program == "ACS":
        new_table = ds_table
        if not year:
            year = "20" + dataset[0:2]

        if dataset.endswith("YR"):
            if ds_table in {"S0201", "S0201PR"}:
                survey = "ACSSPP" + dataset[3:5]
            else:
                survey = "ACSDT" + dataset[3:5]
        else:
            raise UnsupportedCensusData("Dataset does not exist on CEDSCI")

        if int(year) < 2010:
            raise UnsupportedCensusData("Pre-2010 ACS data not available on CEDSCI")
    elif program == "DEC":
        decennial = {
            "113": "DECENNIALCD113",
            "115": "DECENNIALCD115",
            "SF1": "DECENNIALSF1",
        }
        if not year:
            year = "20" + dataset[0:2]
        survey = decennial.get(dataset[-3:])
        if ds_table == "GCT":
            raise UnsupportedCensusData(
                "Geographic Comparison Tables are no longer available"
            )
        new_table = ds_table
        if not survey or int(year) < 2010:
            raise UnsupportedCensusData(
                "Decennial censusus data is not all available on CEDSCI"
            )
    elif program == "NES":
        year = dataset
        survey = "NONEMP"
        new_table = "NS{0}00NONEMP".format(year[2:4])
        if int(year) < 2012:
            raise UnsupportedCensusData(
                "Pre-2012 Nonemployer data not available on CEDSCI"
            )
    elif program == "SBO":
        year = dataset
        new_table = "SB" + year[-2:] + ds_table
        if ds_table[-3] == "A":
            survey = "SBOCS"
        else:
            raise UnsupportedCensusData(
                "Survey of Business Owners tables other than "
                "the company summary are not available on CEDSCI"
            )

    if not (survey and year and new_table):
        raise InputError(
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
    """Builds a CEDSCI url from a dict of query params"""
    assert set(data.keys()) <= set(cedsci)
    base = "https://data.census.gov/cedsci/{0}?".format(data.pop("target"))
    query = urlencode(OrderedDict((k, v) for k, v in sorted(data.items()) if v))
    return base + query


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Transform US Census American Fact Finder URLs "
        "into data.census.gov URLs",
        epilog="If a URL is converted without issue, or with a warning, "
        "%(prog)s exits with code 0. If a URL could not be converted, "
        "If conversion is not and will not be possible, %(prog)s exits with code 1. "
        "but conversion might be possible in the future, %(prog)s exits with code 2.",
        prog="transform.py"
    )
    parser.add_argument(
        "url", default="", nargs="*", help="AFF url(s) to convert"
    )
    parser.add_argument(
        "-i",
        "--infile",
        type=argparse.FileType("r"),
        default=sys.stdin,
        help="File containing AFF urls to convert, one on each line",
    )
    parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("w"),
        default=sys.stdout,
        help="File to output converted URLs to",
    )
    parser.add_argument(
        "-s",
        "--strict",
        action="store_true",
        help="Causes warnings to be interpreted as errors",
    )
    parser.add_argument(
        "--continue-on-err",
        action="store_true",
        help="Treats errors as warnings and continues processing. "
        "URLs that could not be converted will become a blank line.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Print more information to stderr when things go wrong",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="count",
        default=0,
        help="Print less information to stderr when things go wrong",
    )
    args = parser.parse_args()
    verbosity = args.verbose - args.quiet
    if args.url:
        input_src = args.url
    else:
        input_src = args.infile

    if args.strict:
        warnings.filterwarnings(action="error")

    for line in input_src:
        try:
            result = main(line.strip())
        except Exception as err:
            result = ""
            if verbosity >= 1:
                traceback.print_exception(
                    type(err), err, err.__traceback__, file=sys.stderr
                )
            elif verbosity >= 0:
                traceback.print_exception(type(err), err, None, file=sys.stderr)

            if not args.continue_on_err:
                if type(err) in {
                    NotImplementedError,
                    UnsupportedCensusData,
                    LowConfidenceTransformation,
                }:
                    sys.exit(2)
                else:
                    sys.exit(1)

        finally:
            if result or args.outfile is not sys.stdout:
                print(result, file=args.outfile)

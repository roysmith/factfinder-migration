#!/bin/env python3
# python 3.5+
# SPDX-License-Identifier: MIT

import transform
import subprocess
import pytest


def test_pipe_to_underscore():
    old = "0100000US|0400000US01|0500000US01001"
    new = "0100000US_0400000US01_0500000US01001"
    single = "0100000US"
    assert transform.pipe_to_underscore(old) == new
    assert transform.pipe_to_underscore(single) == single


def test_dataset_transform_stated_unavailable():
    tests = [
        ("ACS", "09_1YR", ""),
        ("NES", "2011", ""),
        ("EEO", "2010", ""),
        ("DEC", "10_SF2", ""),
        ("DEC", "10_SF1", "GCT"),
    ]
    for test in tests:
        with pytest.raises(transform.UnsupportedCensusData):
            transform.dataset_transform(*test)


@pytest.mark.xfail
def test_dataset_transform_ecn():
    assert transform.dataset_transform("ECN", "2013", "US")


@pytest.mark.xfail
def test_dataset_transform_bp():
    assert transform.dataset_transform("BP", "2016", "00CZ2") == (
        "ZBP",
        "2016",
        "00CZ2",
    )


def test_dataset_tranform_supported():
    data = [
        (("ACS", "13_5YR", "B07010"), ("ACSDT5Y", "2013", "B07010")),
        (("DEC", "10_113", "H1"), ("DECENNIALCD113", "2010", "H1")),
        (("DEC", "10_SF1", "H10"), ("DECENNIALSF1", "2010", "H10")),
        (("NES", "2016", "00A1"), ("NONEMP", "2016", "NS1600NONEMP")),
        (("SBO", "2012", "00CSA01"), ("SBOCS", "2012", "SB1200CSA01")),
    ]
    for old, new in data:
        assert transform.dataset_transform(*old) == new


def test_dataset_transform_malformed():
    with pytest.raises(transform.InputError):
        transform.dataset_transform("foo", "bar", "baz")


def test_main():
    urls = [
        (
            "https://factfinder.census.gov/bkmk/table/1.0/en/"
            "ACS/13_5YR/B07010/0100000US|0400000US01|0500000US01001",
            "https://data.census.gov/cedsci/table?g="
            "0100000US_0400000US01_0500000US01001&tid=ACSDT5Y2013.B07010&y=2013",
        ),
        (
            "https://factfinder.census.gov/bkmk/table/1.0/en/DEC/10_113/H1",
            "https://data.census.gov/cedsci/table?tid=DECENNIALCD1132010.H1&y=2010",
        ),
        (
            "http://factfinder.census.gov/bkmk/table/1.0/en/DEC/10_SF1/H10",
            "https://data.census.gov/cedsci/table?tid=DECENNIALSF12010.H10&y=2010",
        ),
        (
            "https://factfinder.census.gov/bkmk/table/1.0/en/NES/2016/00A1",
            "https://data.census.gov/cedsci/table?tid=NONEMP2016.NS1600NONEMP&y=2016",
        ),
        (
            "https://factfinder.census.gov/bkmk/table/1.0/en/SBO/2012/00CSA01",
            "https://data.census.gov/cedsci/table?tid=SBOCS2012.SB1200CSA01&y=2012",
        ),
        (
            "http://factfinder.census.gov/bkmk/cf/1.0/en/place/Chicago city, Illinois"
            "/POPULATION/DECENNIAL_CNT",
            "https://data.census.gov/cedsci/profile?q=Chicago+city%2C+Illinois",
        ),
        (
            "http://factfinder.census.gov/servlet/SAFFPopulation?_event=Search"
            "&geo_id=04000US06",
            "https://data.census.gov/cedsci/profile?g=0400000US06",
        ),
        (
            "http://factfinder.census.gov/servlet/SAFFFacts?_event=Search"
            "&geo_id=16000US3546310&_geoContext=01000US%7C04000US35%7C16000US3546310"
            "&_street=&_county=Magdalena&_cityTown=Magdalena&_state=04000US35&_zip="
            "&_lang=en&_sse=on&ActiveGeoDiv=geoSelect&_useEV=&pctxt=fph&pgsl=160"
            "&_submenuId=factsheet_1&ds_name=DEC_2000_SAFF&_ci_nbr=null&qr_name=null"
            "&reg=null:null&_keyword=&_industry=",
            "https://data.census.gov/cedsci/profile?g=1600000US3546310",
        ),
        (
            "http://factfinder.census.gov/servlet/ACSSAFFFacts?_event="
            "&geo_id=16000US3137000&_geoContext=01000US%7C04000US31%7C16000US3137000"
            "&_street=&_county=omaha&_cityTown=omaha&_state=04000US31&_zip=&_lang=en"
            "&_sse=on&ActiveGeoDiv=&_useEV=&pctxt=fph&pgsl=160",
            "https://data.census.gov/cedsci/profile?g=1600000US3137000",
        ),
    ]
    for old, new in urls:
        assert transform.main(old) == new


def test_main_fail():
    tests = [
        ("NotARealURL", transform.InputError),
        (
            "https://factfinder.census.gov/faces/nav/jsf/pages/index.xhtml",
            transform.InputError,
        ),
        (
            "http://factfinder.census.gov/bkmk/cf/1.0/en/zip/17215/ALL",
            transform.UnsupportedCensusData,
        ),
        (
            "http://factfinder.census.gov/servlet/ACSSAFFFacts?_event=ChangeGeoContext"
            "&geo_id=160000US0644000",
            transform.InputError,
        ),
        (
            "http://factfinder.census.gov/servlet/SAFFFacts?_event=Search"
            "&geo_id=86000US78516",
            transform.UnsupportedCensusData,
        ),
    ]
    for url, err in tests:
        with pytest.raises(err):
            transform.main(url)


@pytest.mark.xfail
def test_main_ni():
    urls = [
        "http://factfinder.census.gov/servlet/ACSSAFFFacts?_event=Search&geo_id="
        "&_geoContext=&_street=&_county=Brevard+county&_cityTown=Brevard+county"
        "&_state=04000US12&_zip=&_lang=en&_sse=on&pctxt=fph&pgsl=010",
    ]
    for url in urls:
        assert transform.main(url)


def test_integration_valid():
    old = (
        "https://factfinder.census.gov/bkmk/table/1.0/en/"
        "ACS/13_5YR/B07010/0100000US|0400000US01|0500000US01001"
    )
    new = (
        "https://data.census.gov/cedsci/table"
        "?g=0100000US_0400000US01_0500000US01001&tid=ACSDT5Y2013.B07010&y=2013\n"
    )

    r = subprocess.run(
        ["python3", "transform.py", old],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    assert r.stdout == new
    assert not r.stderr
    assert r.returncode == 0


def test_integration_invalid():
    r = subprocess.run(
        ["python3", "transform.py", "NotARealURL"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    assert not r.stdout
    assert "InputError" in r.stderr
    assert r.returncode > 0

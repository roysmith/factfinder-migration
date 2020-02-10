#!/bin/env python3
# python 3.7+
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
    with pytest.raises(KeyError):
        # American Community Survey Data Prior to 2010
        transform.dataset_transform("ACS", "09_1YR", "")
    with pytest.raises(KeyError):
        # Nonemployer Data Prior to 2012
        transform.dataset_transform("NES", "2011", "")
    # with pytest.raises(KeyError):
        # # County Business Patterns Prior to 2012
        # transform.dataset_transform("BP", "2011", "CBP")
    # with pytest.raises(KeyError):
        # # Economic Census and Economic Census Island Area Prior to 2012
        # transform.dataset_transform("ECN", "2011", "IA")
    with pytest.raises(KeyError):
        # 2010 EEO
        transform.dataset_transform("EEO", "2010", "")


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


def test_dataset_transform_decennial_sf2():
    with pytest.raises(KeyError):
        transform.dataset_transform("DEC", "10_SF2", "")


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
    with pytest.raises(KeyError):
        transform.dataset_transform("foo", "bar", "baz")


def test_main():
    urls = [
        (
            "https://factfinder.census.gov/bkmk/table/1.0/en/"
            "ACS/13_5YR/B07010/0100000US|0400000US01|0500000US01001",
            "https://data.census.gov/cedsci/table?g="
            "0100000US_0400000US01_0500000US01001&y=2013&tid=ACSDT5Y2013.B07010",
        ),
        (
            "https://factfinder.census.gov/bkmk/table/1.0/en/DEC/10_113/H1",
            "https://data.census.gov/cedsci/table?y=2010&tid=DECENNIALCD1132010.H1",
        ),
        (
            "http://factfinder.census.gov/bkmk/table/1.0/en/DEC/10_SF1/H10",
            "https://data.census.gov/cedsci/table?y=2010&tid=DECENNIALSF12010.H10",
        ),
        (
            "https://factfinder.census.gov/bkmk/table/1.0/en/NES/2016/00A1",
            "https://data.census.gov/cedsci/table?y=2016&tid=NONEMP2016.NS1600NONEMP",
        ),
        (
            "https://factfinder.census.gov/bkmk/table/1.0/en/SBO/2012/00CSA01",
            "https://data.census.gov/cedsci/table?y=2012&tid=SBOCS2012.SB1200CSA01"
        )
    ]
    for old, new in urls:
        assert transform.main(old) == new


def test_integration_valid():
    old = (
        "https://factfinder.census.gov/bkmk/table/1.0/en/"
        "ACS/13_5YR/B07010/0100000US|0400000US01|0500000US01001"
    )
    new = (
        "https://data.census.gov/cedsci/table?"
        "g=0100000US_0400000US01_0500000US01001&y=2013&tid=ACSDT5Y2013.B07010\n"
    )

    r = subprocess.run(
        ["python3", "transform.py", old], capture_output=True, text=True,
    )
    assert r.stdout == new
    assert not r.stderr
    assert r.returncode == 0


def test_integration_invalid():
    r = subprocess.run(
        ["python3", "transform.py", "NotARealURL"], capture_output=True, text=True
    )
    assert not r.stdout
    assert "ValueError" in r.stderr
    assert r.returncode > 0

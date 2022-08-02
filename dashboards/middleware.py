from typing import OrderedDict
from django.shortcuts import render
from django.http import HttpResponse
from django.http import HttpResponse
from pathlib import Path
from box import Box
import statistics
import math


def getGrafanaPerfStats() -> dict:
    jsonFileName = Path(__file__).parent / "statsDBFile.json"
    rawStats = Box.from_json(jsonFileName.read_text())
    returnStats = []
    for sha in rawStats:
        entry = {}
        run = rawStats[sha]
        entry["commit_sha"] = sha
        entry["short_sha"] = sha[0:7]
        entry["benchmark_time"] = run["benchmark_time"]
        allRuns = []
        allExits = []
        for i in run["runs"]:
            allRuns += run["runs"][i]["times"]

        entry["mean"] = statistics.mean(allRuns)
        entry["min"] = min(allRuns)
        entry["max"] = max(allRuns)
        entry["stddev"] = statistics.stdev(allRuns)
        entry["number_of_non_zeros"] = allExits.count("!=0")
        returnStats.append(entry)

    returnStats.sort(key=lambda x: x["benchmark_time"])

    return returnStats

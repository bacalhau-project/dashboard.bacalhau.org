from typing import OrderedDict
from django.shortcuts import render
from django.http import HttpResponse
from django.http import HttpResponse
from pathlib import Path
from box import Box
import statistics
import math

import json, box

import dotenv

import os
import psycopg2
import psycopg2.extensions
import logging

DATABASE_URL = os.environ["DATABASE_URL"]
statsDBBlobName = "statsDB"


def getGrafanaPerfStats() -> dict:
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    rawStats = Box()
    with conn:
        with conn.cursor() as cursor:
            postgreSQL_select_statsDB = f"select content from text_blobs where name = %s"
            cursor.execute(postgreSQL_select_statsDB, (statsDBBlobName,))
            statsDBresults = cursor.fetchall()

            if len(statsDBresults) == 1:
                print("Blob found. Loading...")
                try:
                    rawStats = Box.from_json(statsDBresults[0][0])
                    print(f"Loaded records: {len(rawStats.items())}")
                except (json.decoder.JSONDecodeError, box.exceptions.BoxError):
                    pass

        conn.commit()

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

        entry["branch"] = run["branch"]
        entry["tag"] = run["tag"]
        entry["mean"] = statistics.mean(allRuns)
        entry["min"] = min(allRuns)
        entry["max"] = max(allRuns)
        entry["stddev"] = statistics.stdev(allRuns)
        entry["number_of_non_zeros"] = allExits.count("!=0")
        returnStats.append(entry)

    returnStats.sort(key=lambda x: x["benchmark_time"])

    return returnStats

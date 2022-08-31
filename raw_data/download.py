from fileinput import filename
import pathlib
from random import randint, random
from typing import OrderedDict, TypedDict, List
from google.cloud import storage
import os
import datetime
from datetime import date
from dateutil.parser import parse
import operator
from pprint import pp

import box
from box import Box

import glob
import json
import statistics
from collections import defaultdict
from pathlib import Path
import json

import ast

import dotenv

import os
import psycopg2
import psycopg2.extensions
import logging

import re


class LoggingCursor(psycopg2.extensions.cursor):
    def execute(self, sql, args=None):
        logger = logging.getLogger("sql_debug")
        logger.info(self.mogrify(sql, args))

        try:
            psycopg2.extensions.cursor.execute(self, sql, args)
        except Exception as exc:
            logger.error("%s: %s" % (exc.__class__.__name__, exc))
            raise


dotenv.load_dotenv()
DATABASE_URL = os.environ["DATABASE_URL"]


class Parameters(Box):
    TOTAL_JOBS: int
    BATCH_SIZE: int
    CONCURRENCY: int


class Run(Box):
    run_number: int
    command: str
    mean: float
    stddev: float
    median: float
    user: float
    system: float
    min: float
    max: float
    times: List[float]
    exit_codes: List[int]


class Result(Box):
    benchmark_time: date
    commit_sha: str
    parameters: Parameters
    runs: dict[str, Run]
    branch: str
    tag: str


os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", ".bacalhau-global-storage-reader.json")
if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_CONTENT", ""):
    Path(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]).write_text(os.environ["GOOGLE_APPLICATION_CREDENTIALS_CONTENT"])

from_scratch = os.environ.get("FROM_SCRATCH", "false")
BUCKET_NAME = "bacalhau-global-storage"
storage_client = storage.Client()

statsDBBlobName = "statsDB"
statsDB = Box()
max_date = parse("1901-01-01")  # arbitrary date in history


conn = psycopg2.connect(DATABASE_URL, sslmode="require")
with conn:
    if from_scratch != "true":
        print(f"Loading from {statsDBBlobName}...")

        with conn.cursor(cursor_factory=LoggingCursor) as cursor:
            postgreSQL_select_statsDB = f"select content from text_blobs where name = %s"
            cursor.execute(postgreSQL_select_statsDB, (statsDBBlobName,))
            statsDBresults = cursor.fetchall()

            if len(statsDBresults) == 1:
                print("Blob found. Loading...")
                try:
                    statsDB = statsDB.from_json(statsDBresults[0][0])
                    print(f"Loaded records: {len(statsDB)}")
                    if len(statsDB) > 0:
                        for k, v in statsDB.items():
                            if parse(v["benchmark_time"]).timestamp() > max_date.timestamp():
                                max_date = parse(v["benchmark_time"])
                except (json.decoder.JSONDecodeError, box.exceptions.BoxError):
                    pass
    conn.commit()

print(f"Number of files in the DB: {len(statsDB)}")
storedResultsDict = {}

fullRe = re.compile(r"perf-results\/([^Z]+Z)-(.*)\-(v[0-9]+\.[0-9]+\.[0-9]+(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z-]+)?|NOTAG)-(.*)\/(.*)$")
shortRe = re.compile(r"perf-results\/([^Z]+Z)-(.*)\/(.*)$")

for blob in storage_client.list_blobs(BUCKET_NAME, prefix="perf-results/"):
    print(f"Parsing - {blob.name}")
    longMatches = re.match(fullRe, blob.name)
    if longMatches is not None and len(longMatches.groups()) == 6:
        benchmark_time, branch, tag, empty, sha, result_filename = longMatches.groups()[0:6]
    else:
        shortMatches = re.match(shortRe, blob.name)
        if len(shortMatches.groups()) == 3:
            benchmark_time, sha, result_filename = shortMatches.groups()[0:3]
            branch = "main"
            tag = "NOTAG"
        else:
            continue  # Doesn't match either regex, skip to next

    filetype = result_filename.split("-", 1)[0]
    if sha not in storedResultsDict:
        storedResultsDict[sha] = {}
        storedResultsDict[sha]["benchmark_time"] = parse(benchmark_time + "Z")
        storedResultsDict[sha]["branch"] = branch
        storedResultsDict[sha]["tag"] = tag
        storedResultsDict[sha]["parameter_file"] = ""
        storedResultsDict[sha]["result_files"] = []

    match filetype:
        case "parameters":
            storedResultsDict[sha]["parameters_file"] = blob.name
        case "run":
            storedResultsDict[sha]["result_files"].append(blob.name)

print(f"Total number of shas found on server: {len(storedResultsDict.keys())}")

bucket = storage_client.get_bucket(BUCKET_NAME)
filteredFiles = {k: v for k, v in storedResultsDict.items() if v["benchmark_time"].timestamp() > max_date.timestamp()}

print(f"Processing new SHAs: {len(filteredFiles.keys())}")
for sha in filteredFiles:
    fileDict = filteredFiles[sha]
    result = Result()
    result.benchmark_time = fileDict["benchmark_time"].isoformat()
    result.commit_sha = sha
    parametersRaw = bucket.get_blob(fileDict["parameters_file"]).download_as_text()
    parametersDict = ast.literal_eval(parametersRaw)
    result.TOTAL_JOBS = parametersDict["TOTAL_JOBS"]
    result.BATCH_SIZE = parametersDict["BATCH_SIZE"]
    result.CONCURRENCY = parametersDict["CONCURRENCY"]
    result.branch = fileDict["branch"]
    result.tag = fileDict["tag"]
    result.runs = defaultdict()

    for resultsFileName in fileDict["result_files"]:
        resultsRaw = bucket.get_blob(resultsFileName).download_as_text()
        resultsDict = json.loads(resultsRaw)["results"][0]

        resultFileContent = Run()
        resultFileContent.run_number = resultsFileName.rsplit(".")[0].rsplit("-")[-1]
        resultFileContent.command = resultsDict["command"]
        resultFileContent.mean = resultsDict["mean"]
        resultFileContent.stddev = resultsDict["stddev"]
        resultFileContent.median = resultsDict["median"]
        resultFileContent.user = resultsDict["user"]
        resultFileContent.system = resultsDict["system"]
        resultFileContent.min = resultsDict["min"]
        resultFileContent.max = resultsDict["max"]
        resultFileContent.times = resultsDict["times"]
        resultFileContent.exit_codes = resultsDict["exit_codes"]
        result.runs[resultFileContent.run_number] = resultFileContent

    statsDB[sha] = result

with conn:
    with conn.cursor(cursor_factory=LoggingCursor) as cursor:
        postgreSQL_insert_statsDB = "INSERT INTO text_blobs (name, content) VALUES (%s, %s) ON CONFLICT (name) DO UPDATE SET content = EXCLUDED.content;"
        cursor.execute(
            postgreSQL_insert_statsDB,
            (
                statsDBBlobName,
                statsDB.to_json(),
            ),
        )

    conn.commit()

conn.close()

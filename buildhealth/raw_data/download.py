import pathlib
from typing import OrderedDict, TypedDict, List
from google.cloud import storage
import os
import datetime
from datetime import date
from dateutil.parser import parse
import operator
from pprint import pp

from box import Box

import glob
import json
import statistics
from collections import defaultdict
from pathlib import Path
import json


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


os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", ".bacalhau-global-storage-reader.json")
from_scratch = os.environ.get("FROM_SCRATCH", "false")
BUCKET_NAME = "bacalhau-global-storage"
storage_client = storage.Client()

statsDBFile = Path("statsDBFile.txt")
statsDB = Box()
max_date = parse("1901-01-01")  # arbitrary date in history

if from_scratch != "true":
    print(f"Loading from {statsDBFile.absolute().name}...")
    if statsDBFile.exists():
        print("File found. Loading...")
        statsDB = statsDB.from_json(statsDBFile.read_text())
        print(f"Loaded from {statsDBFile.absolute().name}: {len(statsDB)}")
        if len(statsDB) > 0:
            for k, v in statsDB.items():
                if parse(v["benchmark_time"]).timestamp() > max_date.timestamp():
                    max_date = parse(v["benchmark_time"])

print(f"Number of files in the DB: {len(statsDB)}")
storedResultsDict = {}

for blob in storage_client.list_blobs(BUCKET_NAME, prefix="perf-results/"):
    keys, filename = blob.name.split("/")[1:]
    benchmark_time, sha = keys.rsplit("-", 1)
    filetype = filename.split("-", 1)[0]
    if sha not in storedResultsDict:
        storedResultsDict[sha] = {}
        storedResultsDict[sha]["benchmark_time"] = parse(benchmark_time)
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
    parametersDict = json.loads(parametersRaw)
    result.TOTAL_JOBS = parametersDict["TOTAL_JOBS"]
    result.BATCH_SIZE = parametersDict["BATCH_SIZE"]
    result.CONCURRENCY = parametersDict["CONCURRENCY"]
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

statsDBFile.write_text(statsDB.to_json())

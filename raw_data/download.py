import pathlib
from typing import OrderedDict, TypedDict, List
from google.cloud import storage
import os
import datetime
from datetime import date

import glob
import json
import statistics
from collections import defaultdict
from pathlib import Path
import json


class Parameters(TypedDict):
    TOTAL_JOBS: int
    BATCH_SIZE: int
    CONCURRENCY: int


class Run(TypedDict):
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


class Result(TypedDict):
    datetime: date
    commit_sha: str
    parameters: Parameters
    runs: TypedDict[Run]


os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = ".bacalhau-global-storage-reader.json"
storage_client = storage.Client()

statsDBFile = "statsDBFile.txt"
statsDB = {}
if Path(statsDBFile).exists():
    with open(statsDBFile) as f:
        statsDB = json.load(f)

max_date = datetime.datetime.min
for blob in storage_client.list_blobs("bacalhau-global-storage", prefix="perf-results/"):
    print(blob)
    # contents = blob.download_as_string()

#
#   "results": [
#     {
#       "command": "timeout 30s ./submit.sh ../bin/linux_amd64/bacalhau 43295",
#       "mean": 0.18000330800000003,
#       "stddev": 0.005534496809196538,
#       "median": 0.1787459428,
#       "user": 0.10905314000000002,
#       "system": 0.05250425999999999,
#       "min": 0.17564856630000003,
#       "max": 0.1931217993,
#       "times": [
#         0.18549640230000003,
#         0.1931217993,
#         0.1757045563,
#         0.1765007433,
#         0.17564856630000003,
#         0.18031594130000003,
#         0.17770359230000002,
#         0.17572979330000002,
#         0.18002339230000003,
#         0.1797882933
#       ],
#       "exit_codes": [
#         0,
#         0,
#         0,
#         0,
#         0,
#         0,
#         0,
#         0,
#         0,
#         0
#       ]
#     }
#   ]
# }

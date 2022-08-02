from django.shortcuts import render
from django.http import HttpResponse
from django.http import HttpResponse
from pathlib import Path
from box import Box
from dashboards.middleware import getGrafanaPerfStats
import json


def index(request):
    return render(request, "index.html")


def rawStats(request):
    jsonFileName = Path(__file__).parent / "statsDBFile.json"
    response = HttpResponse(jsonFileName.read_text(), content_type="application/json")
    return response


def grafanaPerfStats(request):
    response = HttpResponse(json.dumps(getGrafanaPerfStats()), content_type="application/json")
    return response

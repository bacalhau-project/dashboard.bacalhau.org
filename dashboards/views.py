from django.shortcuts import render
from django.http import HttpResponse
from django.http import HttpResponse
from pathlib import Path


def index(request):
    return render(request, "index.html")


def rawStats(request):
    jsonFileName = Path(__file__).parent / "statsDBFile.json"
    response = HttpResponse(jsonFileName.read_text(), content_type="application/json")
    return response

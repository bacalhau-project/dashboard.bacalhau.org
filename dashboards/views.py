from django.shortcuts import render
from django.http import HttpResponse
from django.http import HttpResponse
from pathlib import Path


def index(request):
    return render(request, "index.html")


def rawStats(request):
    jsonFileName = Path(__file__).parent / "statsDBFile.json"
    with open(jsonFileName, "r") as file:
        response = HttpResponse(file, content_type="application/json")
        response["Content-Disposition"] = f"attachment; filename={jsonFileName}"
        return response

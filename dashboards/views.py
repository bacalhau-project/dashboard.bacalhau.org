from django.shortcuts import render
from django.http import HttpResponse
from django.http import HttpResponse


def index(request):
    return render(request, "index.html")


def statsDB(request):
    jsonFileName = "statsDB.json"
    with open(jsonFileName, "r") as file:
        response = HttpResponse(file, content_type="application/json")
        response["Content-Disposition"] = f"attachment; filename={jsonFileName}"
        return response

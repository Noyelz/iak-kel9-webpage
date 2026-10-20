from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .analytics import get_dashboard

# Create your views here.
def home(request):
    return render(request, "dashboard/home.html")

@login_required
def dashboard(request):
    return render(request, "dashboard/dashboard.html", {'analytics': get_dashboard(request.GET.get('tahun'))})


@login_required
def warehouse(request):
    from django.http import HttpResponse, Http404
    from .warehouse import TABLES, get_warehouse
    import csv

    table = request.GET.get("tabel", "fact_indikator_asuransi")
    if table not in TABLES:
        raise Http404("Tabel tidak tersedia")
    context = get_warehouse(table)
    if request.GET.get("format") == "csv" and context["status"] == "ready":
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{table}.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow(context["columns"])
        # NULL ditulis kosong; desimal diekspor tanpa pembulatan.
        for row in context["rows"]:
            writer.writerow(["" if value is None else str(value) for value in row])
        return response
    return render(request, "dashboard/warehouse.html", {"warehouse": context})

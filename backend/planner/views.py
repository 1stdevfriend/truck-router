from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response

from . import ors
from .plan import build_plan
from .serializers import PlanRequestSerializer
from .weather import WeatherError


@api_view(["GET"])
def health(request):
    return Response({"status": "ok", "ors_configured": bool(settings.ORS_API_KEY)})


@api_view(["GET"])
def geocode(request):
    q = request.query_params.get("q", "").strip()
    if not 2 <= len(q) <= 200:
        return Response({"error": "q must be 2–200 characters"}, status=400)
    try:
        return Response({"results": ors.autocomplete(q)})
    except ors.ORSError as exc:
        return Response({"error": str(exc)}, status=502)


@api_view(["POST"])
def plan(request):
    req = PlanRequestSerializer(data=request.data)
    req.is_valid(raise_exception=True)
    d = req.validated_data
    try:
        result = build_plan(
            [d["origin"]["lon"], d["origin"]["lat"]],
            [d["destination"]["lon"], d["destination"]["lat"]],
            d["departure"],
            d["weight_lb"],
            d["interval_mi"],
        )
    except (ors.ORSError, WeatherError) as exc:
        return Response({"error": str(exc)}, status=502)
    return Response(result)

from datetime import datetime, timedelta, timezone

from rest_framework import serializers


class PointSerializer(serializers.Serializer):
    lon = serializers.FloatField(min_value=-180, max_value=180)
    lat = serializers.FloatField(min_value=-90, max_value=90)


class PlanRequestSerializer(serializers.Serializer):
    origin = PointSerializer()
    destination = PointSerializer()
    departure = serializers.DateTimeField()
    weight_lb = serializers.FloatField(min_value=1, max_value=150_000)
    interval_mi = serializers.ChoiceField(choices=[10, 25, 50], default=25)

    def validate_departure(self, value):
        if value < datetime.now(timezone.utc) - timedelta(hours=1):
            raise serializers.ValidationError("Departure can't be in the past.")
        return value

    def validate(self, data):
        if (data["origin"]["lon"], data["origin"]["lat"]) == (data["destination"]["lon"], data["destination"]["lat"]):
            raise serializers.ValidationError("Origin and destination must differ.")
        return data

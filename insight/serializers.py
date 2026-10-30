from rest_framework import serializers

from .models import Branch, Survey


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ["id", "name", "city", "manager"]


class SurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = Survey
        fields = ["id", "title", "period"]


class AnalyzeRequestSerializer(serializers.Serializer):
    """Validates the body of POST /api/analyze/."""

    branch_id = serializers.IntegerField()
    survey_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_branch_id(self, value):
        if not Branch.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Branch does not exist.")
        return value

    def validate_survey_id(self, value):
        if value is not None and not Survey.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Survey does not exist.")
        return value

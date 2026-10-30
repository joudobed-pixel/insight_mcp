from django.contrib import admin

from .models import Branch, Response, Survey


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "manager")
    search_fields = ("name", "city")


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ("title", "period", "created_at")
    search_fields = ("title", "period")


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ("branch", "survey", "rating", "recommend_score", "submitted_at")
    list_filter = ("branch", "survey", "rating")
    search_fields = ("comment",)

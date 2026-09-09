from django.contrib import admin

from .models import BenefitEnrollment, BenefitPlan, Candidate, EmployeeGoal, JobApplication, JobOpening, OffboardingRecord, PerformanceCycle, PerformanceReview


@admin.register(JobOpening, Candidate, JobApplication, PerformanceCycle, EmployeeGoal, PerformanceReview, BenefitPlan, BenefitEnrollment, OffboardingRecord)
class TalentAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'updated_at')

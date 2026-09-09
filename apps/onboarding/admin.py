from django.contrib import admin

from .models import EmployeeOnboarding, OnboardingTask, OnboardingTaskTemplate, OnboardingWorkflow


@admin.register(OnboardingWorkflow)
class OnboardingWorkflowAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'is_active')


@admin.register(OnboardingTaskTemplate)
class OnboardingTaskTemplateAdmin(admin.ModelAdmin):
    list_display = ('title', 'workflow', 'order', 'is_required')


@admin.register(EmployeeOnboarding)
class EmployeeOnboardingAdmin(admin.ModelAdmin):
    list_display = ('employee', 'workflow', 'status', 'start_date', 'expected_completion_date')


@admin.register(OnboardingTask)
class OnboardingTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'onboarding', 'status', 'due_date', 'assigned_to')

from django.contrib import admin

from .models import AttendanceRecord
from .services import AttendanceCalculator


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
	list_display = ('attendance_date', 'employee', 'status', 'time_in', 'time_out', 'late_minutes', 'overtime_minutes')
	list_filter = ('status', 'attendance_date')
	search_fields = ('employee__employee_number', 'employee__first_name', 'employee__last_name')
	readonly_fields = ('late_minutes', 'undertime_minutes', 'overtime_minutes')

	def save_model(self, request, obj, form, change):
		metrics = AttendanceCalculator.calculate(obj)
		for field, value in metrics.items():
			setattr(obj, field, value)
		super().save_model(request, obj, form, change)

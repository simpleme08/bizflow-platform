from django.contrib import admin

from .models import EmployeeLeaveBalance, LeaveApplication, LeaveType

admin.site.register(LeaveType)
admin.site.register(EmployeeLeaveBalance)
admin.site.register(LeaveApplication)

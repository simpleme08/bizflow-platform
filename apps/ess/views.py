from django.http import JsonResponse
from django.shortcuts import redirect, render

from apps.attendance.models import AttendanceRecord
from apps.leave.models import LeaveApplication
from apps.organization.context import current_membership
from apps.payroll.models import PayrollRecord


def _employee_for_request(request):
    membership = current_membership(request)
    if membership is None:
        return None, None
    try:
        employee = request.user.employee_profile
    except AttributeError:
        return membership, None
    if employee.organization_id != membership.organization_id or not employee.organization.is_active:
        return membership, None
    return membership, employee


def ess_page(request):
    if not request.user.is_authenticated:
        return redirect('login')
    from apps.accounts.views import workspace_url_for_user
    return render(request, 'ess/ess.html', {'workspace_url': workspace_url_for_user(request)})


def ess_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership, employee = _employee_for_request(request)
    if membership is None:
        return JsonResponse({'detail': 'No active organization membership found.'}, status=403)
    if employee is None:
        return JsonResponse({'detail': 'Employee organization access is not available.'}, status=403)
    attendance = employee.attendance_records.order_by('-attendance_date')
    leave = employee.leave_applications.select_related('leave_type').order_by('-created_at')
    payroll = employee.payroll_records.select_related('payroll_period').filter(status__in=(PayrollRecord.Status.APPROVED, PayrollRecord.Status.PAID), payroll_period__organization=membership.organization).order_by('-created_at')
    return JsonResponse({'employee': {
        'number': employee.employee_number,
        'name': f'{employee.first_name} {employee.last_name}',
        'department': employee.department.name if employee.department else None,
        'position': employee.position.title if employee.position else None,
        'employment_type': employee.employment_type.name if employee.employment_type else None,
    }, 'attendance': [{'date': record.attendance_date.isoformat(), 'time_in': record.time_in.isoformat() if record.time_in else None, 'time_out': record.time_out.isoformat() if record.time_out else None, 'hours_worked': str(round(record.hours_worked.total_seconds() / 3600, 2)) if record.hours_worked else None, 'late_minutes': record.late_minutes, 'undertime_minutes': record.undertime_minutes, 'overtime_minutes': record.overtime_minutes, 'status': record.status} for record in attendance[:20]], 'leave': [{'type': application.leave_type.name, 'start_date': application.start_date.isoformat(), 'end_date': application.end_date.isoformat(), 'days': str(application.total_days), 'status': application.status} for application in leave[:20]], 'payroll': [{'id': str(record.id), 'period': record.payroll_period.name, 'net_pay': str(record.net_pay), 'status': record.status} for record in payroll[:20]]})

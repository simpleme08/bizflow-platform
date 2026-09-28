from datetime import date

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.attendance.models import AttendanceRecord
from apps.leave.models import LeaveApplication
from apps.organization.context import current_membership
from apps.payroll.models import PayrollRecord, PayrollPeriod


def reports_page(request):
    if not request.user.is_authenticated:
        return redirect('login')
    from apps.accounts.views import workspace_url_for_user
    return render(request, 'reports/reports.html', {'workspace_url': workspace_url_for_user(request.user)})


def reports_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = current_membership(request)
    if membership is None or not membership.has_permission('view_reports'):
        return JsonResponse({'detail': 'No active organization membership found.'}, status=403)
    organization = membership.organization
    today = timezone.localdate()
    start = request.GET.get('start')
    end = request.GET.get('end')
    try:
        start_date = date.fromisoformat(start) if start else None
        end_date = date.fromisoformat(end) if end else None
    except ValueError:
        return JsonResponse({'detail': 'start/end must be ISO dates (YYYY-MM-DD).'}, status=400)
    if start_date and end_date and end_date < start_date:
        return JsonResponse({'detail': 'end cannot be before start.'}, status=400)

    attendance = AttendanceRecord.objects.filter(employee__organization=organization)
    leave = LeaveApplication.objects.filter(employee__organization=organization)
    payroll = PayrollRecord.objects.filter(employee__organization=organization)
    periods = PayrollPeriod.objects.filter(organization=organization)
    if start_date:
        attendance = attendance.filter(attendance_date__gte=start_date)
        leave = leave.filter(start_date__gte=start_date)
        payroll = payroll.filter(payroll_period__end_date__gte=start_date)
        periods = periods.filter(end_date__gte=start_date)
    if end_date:
        attendance = attendance.filter(attendance_date__lte=end_date)
        leave = leave.filter(start_date__lte=end_date)
        payroll = payroll.filter(payroll_period__start_date__lte=end_date)
        periods = periods.filter(start_date__lte=end_date)

    open_punches = attendance.filter(time_in__isnull=False, time_out__isnull=True).count()
    cover_or_unscheduled = attendance.filter(clock_in_mode__in=(AttendanceRecord.ClockInMode.COVER, AttendanceRecord.ClockInMode.UNSCHEDULED)).count()
    payroll_exceptions = periods.filter(confidence_status__in=('REVIEW', 'BLOCKED')).count()
    billing_exception = organization.subscription_status in ('PAST_DUE', 'CANCELED')
    return JsonResponse({
        'date': today.isoformat(),
        'filters': {'start': start_date.isoformat() if start_date else None, 'end': end_date.isoformat() if end_date else None},
        'attendance': {
            'total': attendance.count(),
            'present': attendance.filter(status=AttendanceRecord.Status.PRESENT).count(),
            'absent': attendance.filter(status=AttendanceRecord.Status.ABSENT).count(),
            'late_minutes': sum(record.late_minutes for record in attendance),
            'overtime_minutes': sum(record.overtime_minutes for record in attendance),
        },
        'leave': {
            'total': leave.count(),
            'pending': leave.filter(status=LeaveApplication.Status.PENDING).count(),
            'approved': leave.filter(status=LeaveApplication.Status.APPROVED).count(),
        },
        'payroll': {
            'total_records': payroll.count(),
            'approved': payroll.filter(status=PayrollRecord.Status.APPROVED).count(),
            'paid': payroll.filter(status=PayrollRecord.Status.PAID).count(),
        },
        'exceptions': {
            'open_attendance_punches': open_punches,
            'cover_or_unscheduled_attendance': cover_or_unscheduled,
            'payroll_review_or_blocked_periods': payroll_exceptions,
            'billing_attention_required': billing_exception,
        },
    })

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.attendance.models import AttendanceRecord
from apps.leave.models import LeaveApplication
from apps.organization.models import OrganizationMembership
from apps.payroll.models import PayrollRecord


def reports_page(request):
	if not request.user.is_authenticated:
		return redirect('login')
	from apps.accounts.views import workspace_url_for_user
	return render(request, 'reports/reports.html', {'workspace_url': workspace_url_for_user(request.user)})


def reports_api(request):
	if not request.user.is_authenticated:
		return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
	membership = OrganizationMembership.objects.filter(user=request.user, is_active=True, organization__is_active=True).first()
	if membership is None or not membership.has_permission('view_reports'):
		return JsonResponse({'detail': 'No active organization membership found.'}, status=403)
	organization = membership.organization
	today = timezone.localdate()
	attendance = AttendanceRecord.objects.filter(employee__organization=organization)
	leave = LeaveApplication.objects.filter(employee__organization=organization)
	payroll = PayrollRecord.objects.filter(employee__organization=organization)
	return JsonResponse({'date': today.isoformat(), 'attendance': {'total': attendance.count(), 'present': attendance.filter(status=AttendanceRecord.Status.PRESENT).count(), 'absent': attendance.filter(status=AttendanceRecord.Status.ABSENT).count(), 'late_minutes': sum(record.late_minutes for record in attendance), 'overtime_minutes': sum(record.overtime_minutes for record in attendance)}, 'leave': {'total': leave.count(), 'pending': leave.filter(status=LeaveApplication.Status.PENDING).count(), 'approved': leave.filter(status=LeaveApplication.Status.APPROVED).count()}, 'payroll': {'total_records': payroll.count(), 'approved': payroll.filter(status=PayrollRecord.Status.APPROVED).count(), 'paid': payroll.filter(status=PayrollRecord.Status.PAID).count()}})

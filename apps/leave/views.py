import json
from datetime import date
from decimal import Decimal

from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.organization.models import OrganizationMembership
from apps.core.services import record_audit

from .models import EmployeeLeaveBalance, LeaveApplication, LeaveType


def _membership(request):
	return OrganizationMembership.objects.filter(user=request.user, is_active=True, organization__is_active=True).select_related('organization').first()


def leave_page(request):
	if not request.user.is_authenticated:
		return redirect('login')
	from apps.accounts.views import workspace_url_for_user
	return render(request, 'leave/leave.html', {'workspace_url': workspace_url_for_user(request.user)})


@require_http_methods(['GET', 'POST'])
def my_leave_api(request):
	if not request.user.is_authenticated:
		return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
	try:
		employee = request.user.employee_profile
	except AttributeError:
		return JsonResponse({'detail': 'No employee profile is linked to this account.'}, status=404)
	current_year = timezone.localdate().year
	if request.method == 'GET':
		balances = {balance.leave_type_id: balance for balance in employee.leave_balances.filter(year=current_year).select_related('leave_type')}
		leave_types = LeaveType.objects.filter(is_active=True).order_by('name')
		return JsonResponse({
			'year': current_year,
			'leave_types': [{'id': str(item.id), 'name': item.name, 'code': item.code, 'is_paid': item.is_paid} for item in leave_types],
			'balances': [{'leave_type_id': str(item.id), 'leave_type': item.name, 'credits': str(balances[item.id].credits if item.id in balances else item.annual_credits), 'used': str(balances[item.id].used if item.id in balances else Decimal('0.00')), 'remaining': str(balances[item.id].remaining if item.id in balances else item.annual_credits)} for item in leave_types],
			'applications': [{'id': str(application.id), 'leave_type': application.leave_type.name, 'start_date': application.start_date.isoformat(), 'end_date': application.end_date.isoformat(), 'total_days': str(application.total_days), 'reason': application.reason, 'status': application.status, 'remarks': application.remarks} for application in employee.leave_applications.select_related('leave_type').order_by('-created_at')],
		})
	try:
		payload = json.loads(request.body or '{}')
		leave_type = LeaveType.objects.get(id=payload['leave_type_id'], is_active=True)
		start_date = date.fromisoformat(payload['start_date'])
		end_date = date.fromisoformat(payload['end_date'])
		if end_date < start_date:
			raise ValueError
		total_days = Decimal((end_date - start_date).days + 1)
		balance, _ = EmployeeLeaveBalance.objects.get_or_create(employee=employee, leave_type=leave_type, year=start_date.year, defaults={'credits': leave_type.annual_credits})
		if balance.remaining < total_days:
			return JsonResponse({'detail': 'Insufficient leave balance.'}, status=400)
		application = LeaveApplication.objects.create(employee=employee, leave_type=leave_type, start_date=start_date, end_date=end_date, total_days=total_days, reason=payload.get('reason', ''))
	except (KeyError, TypeError, ValueError, json.JSONDecodeError, LeaveType.DoesNotExist):
		return JsonResponse({'detail': 'Provide a valid leave type and date range.'}, status=400)
	record_audit(organization=employee.organization, actor=request.user, action='leave.submitted', entity=application)
	return JsonResponse({'id': str(application.id), 'status': application.status, 'total_days': str(application.total_days)}, status=201)


@require_http_methods(['GET', 'POST'])
def leave_api(request):
	if not request.user.is_authenticated:
		return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
	membership = _membership(request)
	if membership is None:
		return JsonResponse({'detail': 'No active organization membership found.'}, status=403)
	if request.method == 'GET':
		if not membership.has_permission('approve_leave'):
			return JsonResponse({'detail': 'Leave management permission is required.'}, status=403)
		applications = LeaveApplication.objects.filter(employee__organization=membership.organization).select_related('employee', 'leave_type').order_by('-created_at')
		return JsonResponse({'applications': [{
			'id': str(application.id), 'employee': f'{application.employee.first_name} {application.employee.last_name}',
			'leave_type': application.leave_type.name, 'start_date': application.start_date.isoformat(),
			'end_date': application.end_date.isoformat(), 'total_days': str(application.total_days), 'status': application.status,
		} for application in applications]})
	if not membership.has_permission('submit_leave'):
		return JsonResponse({'detail': 'Leave submission permission is required.'}, status=403)
	try:
		payload = json.loads(request.body)
		employee = request.user.employee_profile
		leave_type = LeaveType.objects.get(id=payload['leave_type_id'], is_active=True)
		start_date = date.fromisoformat(payload['start_date'])
		end_date = date.fromisoformat(payload['end_date'])
		if end_date < start_date:
			raise ValueError
		total_days = Decimal((end_date - start_date).days + 1)
		balance, _ = EmployeeLeaveBalance.objects.get_or_create(employee=employee, leave_type=leave_type, year=start_date.year, defaults={'credits': leave_type.annual_credits})
		if balance.remaining < total_days:
			return JsonResponse({'detail': 'Insufficient leave balance.'}, status=400)
		application = LeaveApplication.objects.create(employee=employee, leave_type=leave_type, start_date=start_date, end_date=end_date, total_days=total_days, reason=payload.get('reason', ''))
	except (KeyError, TypeError, ValueError, LeaveType.DoesNotExist, AttributeError):
		return JsonResponse({'detail': 'Provide a valid leave type, date range, and employee profile.'}, status=400)
	return JsonResponse({'id': str(application.id), 'status': application.status, 'total_days': str(application.total_days)}, status=201)


@require_http_methods(['POST'])
def leave_decision(request, application_id):
	if not request.user.is_authenticated:
		return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
	membership = _membership(request)
	if membership is None or not membership.has_permission('approve_leave'):
		return JsonResponse({'detail': 'Leave approval permission is required.'}, status=403)
	try:
		application = LeaveApplication.objects.get(id=application_id, employee__organization=membership.organization)
		payload = json.loads(request.body)
		if payload.get('decision') == 'approve':
			application.approve(request.user)
			record_audit(organization=membership.organization, actor=request.user, action='leave.approved', entity=application)
		elif payload.get('decision') == 'reject':
			application.reject(request.user, payload.get('remarks', ''))
			record_audit(organization=membership.organization, actor=request.user, action='leave.rejected', entity=application)
		else:
			return JsonResponse({'detail': 'Decision must be approve or reject.'}, status=400)
	except (LeaveApplication.DoesNotExist, json.JSONDecodeError, ValidationError) as error:
		if isinstance(error, ValidationError):
			return JsonResponse({'detail': error.messages[0]}, status=400)
		return JsonResponse({'detail': 'Leave application was not found.'}, status=404)
	return JsonResponse({'id': str(application.id), 'status': application.status})

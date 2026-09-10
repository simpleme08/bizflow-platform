import json
from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.core.models import AuditEvent
from apps.organization.models import OrganizationMembership

from .models import Employee, EmployeeDocument, EmploymentHistory


def _membership_for(user):
    return OrganizationMembership.objects.filter(user=user, is_active=True, organization__is_active=True).select_related('organization').first()


def _employee_payload(employee, private=False):
    data = {
        'id': str(employee.id), 'employee_number': employee.employee_number,
        'name': f'{employee.first_name} {employee.last_name}', 'first_name': employee.first_name, 'last_name': employee.last_name,
        'is_active': employee.is_active, 'status': employee.status,
        'department': employee.department.name if employee.department else None,
        'position': employee.position.title if employee.position else None,
        'employment_type': employee.employment_type.name if employee.employment_type else None,
        'manager': {'id': str(employee.manager.id), 'name': f'{employee.manager.first_name} {employee.manager.last_name}'} if employee.manager else None,
        'hire_date': employee.hire_date.isoformat() if employee.hire_date else None,
        'regularization_date': employee.regularization_date.isoformat() if employee.regularization_date else None,
        'separation_date': employee.separation_date.isoformat() if employee.separation_date else None,
        'assignments': [{'shift': a.shift_template.name, 'client': a.client.name if a.client else None, 'site': a.client_site.name if a.client_site else None, 'start_date': a.start_date.isoformat(), 'end_date': a.end_date.isoformat() if a.end_date else None, 'is_primary': a.is_primary} for a in employee.assignments.all()],
    }
    if private:
        data.update({'birth_date': employee.birth_date.isoformat() if employee.birth_date else None, 'sex': employee.sex, 'personal_email': employee.personal_email, 'work_email': employee.work_email, 'mobile_number': employee.mobile_number, 'address': employee.address, 'emergency_contact_name': employee.emergency_contact_name, 'emergency_contact_phone': employee.emergency_contact_phone})
    return data


def _parse_date(value, field):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        raise ValueError(f'{field} must use YYYY-MM-DD format.')


def employee_directory(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request.user)
    if membership is None or not membership.has_permission('view_employees'):
        return JsonResponse({'detail': 'No active organization membership found.'}, status=403)
    employees = Employee.objects.filter(organization=membership.organization, is_active=True).select_related('department', 'position', 'employment_type', 'manager').prefetch_related('assignments__shift_template', 'assignments__client', 'assignments__client_site')
    return JsonResponse({'employees': [_employee_payload(employee) for employee in employees]})


def employee_profile_api(request, employee_id):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request.user)
    if membership is None:
        return JsonResponse({'detail': 'Permission denied.'}, status=403)
    employee = Employee.objects.filter(id=employee_id, organization=membership.organization).select_related('department', 'position', 'employment_type', 'manager').prefetch_related('assignments__shift_template', 'assignments__client', 'assignments__client_site', 'employment_history__department', 'employment_history__position', 'employment_history__employment_type', 'employment_history__manager', 'documents').first()
    if employee is None:
        return JsonResponse({'detail': 'Employee not found.'}, status=404)
    is_self = employee.user_id == request.user.id
    if not is_self and not membership.has_permission('view_employees'):
        return JsonResponse({'detail': 'Permission denied.'}, status=403)
    private = is_self or membership.has_permission('manage_employees')
    return JsonResponse({'employee': _employee_payload(employee, private), 'history': [{'id': str(h.id), 'status': h.status, 'effective_date': h.effective_date.isoformat(), 'end_date': h.end_date.isoformat() if h.end_date else None, 'department': h.department.name if h.department else None, 'position': h.position.title if h.position else None, 'employment_type': h.employment_type.name if h.employment_type else None, 'manager': str(h.manager_id) if h.manager_id else None, 'reason': h.reason} for h in employee.employment_history.all()], 'documents': [{'id': str(d.id), 'type': d.document_type, 'name': d.name, 'issued_date': d.issued_date.isoformat() if d.issued_date else None, 'expiry_date': d.expiry_date.isoformat() if d.expiry_date else None, 'required': d.is_required, 'status': d.status} for d in employee.documents.all()]})


def employee_lifecycle_api(request, employee_id):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request.user)
    if membership is None or not membership.has_permission('manage_employees'):
        return JsonResponse({'detail': 'Permission denied.'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed.'}, status=405)
    try:
        payload = request.POST if request.POST else json.loads(request.body or '{}')
        status = str(payload.get('status', '')).upper()
        effective_date = _parse_date(payload.get('effective_date'), 'effective_date') or timezone.localdate()
        end_date = _parse_date(payload.get('end_date'), 'end_date')
        if status not in EmploymentHistory.Status.values:
            raise ValidationError('Invalid employment status.')
        with transaction.atomic():
            employee = Employee.objects.select_for_update().filter(id=employee_id, organization=membership.organization).first()
            if employee is None:
                return JsonResponse({'detail': 'Employee not found.'}, status=404)
            previous_status = employee.status
            employee.status = status
            if status in {EmploymentHistory.Status.RESIGNED, EmploymentHistory.Status.TERMINATED, EmploymentHistory.Status.SEPARATED}:
                employee.is_active = False
                employee.separation_date = effective_date
            elif status in {EmploymentHistory.Status.ONBOARDING, EmploymentHistory.Status.PROBATIONARY, EmploymentHistory.Status.REGULAR}:
                employee.is_active = True
                if status == EmploymentHistory.Status.REGULAR:
                    employee.regularization_date = effective_date
                if status == EmploymentHistory.Status.ONBOARDING and employee.hire_date is None:
                    employee.hire_date = effective_date
            elif status == EmploymentHistory.Status.SUSPENDED:
                employee.is_active = False
            employee.save()
            history = EmploymentHistory(employee=employee, status=status, effective_date=effective_date, end_date=end_date, department=employee.department, position=employee.position, employment_type=employee.employment_type, manager=employee.manager, reason=payload.get('reason', ''))
            history.full_clean()
            history.save()
            AuditEvent.objects.create(organization=employee.organization, actor=request.user, action='EMPLOYEE_LIFECYCLE_CHANGED', entity_type='Employee', entity_id=str(employee.id), details={'status': status, 'previous_status': previous_status, 'effective_date': effective_date.isoformat(), 'reason': history.reason})
    except (ValueError, TypeError, ValidationError, json.JSONDecodeError) as exc:
        return JsonResponse({'detail': str(exc)}, status=400)
    return JsonResponse({'employee': _employee_payload(employee), 'status': status}, status=200)


def employee_directory_page(request):
    if not request.user.is_authenticated:
        return redirect('login')
    from apps.accounts.views import workspace_url_for_user
    return render(request, 'employees/directory.html', {'workspace_url': workspace_url_for_user(request.user)})

import json
from datetime import timedelta

from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.core.models import AuditEvent
from apps.organization.models import Department, EmploymentType, OrganizationMembership, Position

from .models import Employee, EmployeeDocument, EmployeeEmploymentHistory


def _membership_for(user):
    return OrganizationMembership.objects.filter(user=user, is_active=True, organization__is_active=True).select_related('organization').first()


def _employee_payload(employee, include_private=True):
    data = {
        'id': str(employee.id), 'employee_number': employee.employee_number,
        'name': f'{employee.first_name} {employee.last_name}', 'first_name': employee.first_name, 'last_name': employee.last_name,
        'department': employee.department.name if employee.department else None, 'position': employee.position.title if employee.position else None,
        'employment_type': employee.employment_type.name if employee.employment_type else None,
        'manager': {'id': str(employee.manager.id), 'name': f'{employee.manager.first_name} {employee.manager.last_name}'} if employee.manager else None,
        'status': employee.status, 'is_active': employee.is_active, 'hire_date': employee.hire_date.isoformat() if employee.hire_date else None,
        'regularization_date': employee.regularization_date.isoformat() if employee.regularization_date else None,
        'separation_date': employee.separation_date.isoformat() if employee.separation_date else None,
    }
    if include_private:
        data.update({'birth_date': employee.birth_date.isoformat() if employee.birth_date else None, 'sex': employee.sex,
                     'personal_email': employee.personal_email, 'work_email': employee.work_email, 'mobile_number': employee.mobile_number,
                     'address': employee.address, 'emergency_contact_name': employee.emergency_contact_name, 'emergency_contact_phone': employee.emergency_contact_phone})
    return data


def _parse_date(value, field):
    if not value:
        return None
    try:
        return timezone.datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        raise ValueError(f'{field} must use YYYY-MM-DD format.')


def employee_directory(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request.user)
    if membership is None or not membership.has_permission('view_employees'):
        return JsonResponse({'detail': 'No active organization membership found.'}, status=403)
    employees = Employee.objects.filter(organization=membership.organization, is_active=True).select_related('department', 'position', 'employment_type', 'manager').prefetch_related('assignments__shift_template', 'assignments__client')
    return JsonResponse({'employees': [{**_employee_payload(employee, False), 'assignments': [{'shift': a.shift_template.name, 'client': a.client.name if a.client else None, 'site': a.client_site.name if a.client_site else None, 'start_date': a.start_date.isoformat(), 'end_date': a.end_date.isoformat() if a.end_date else None, 'is_primary': a.is_primary} for a in employee.assignments.all()]} for employee in employees]})


def employee_directory_page(request):
    if not request.user.is_authenticated:
        return redirect('login')
    from apps.accounts.views import workspace_url_for_user
    return render(request, 'employees/directory.html', {'workspace_url': workspace_url_for_user(request.user)})


def employee_profile(request, employee_id):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request.user)
    if membership is None:
        return JsonResponse({'detail': 'No active organization membership found.'}, status=403)
    employee = Employee.objects.filter(id=employee_id, organization=membership.organization).select_related('department', 'position', 'employment_type', 'manager').first()
    if employee is None:
        return JsonResponse({'detail': 'Employee not found.'}, status=404)
    is_self = employee.user_id == request.user.id
    if not is_self and not membership.has_permission('view_employees'):
        return JsonResponse({'detail': 'You do not have permission to view this employee.'}, status=403)
    return JsonResponse({'employee': _employee_payload(employee, include_private=is_self or membership.has_permission('manage_employees')),
                         'history': [{'action': h.action, 'effective_date': h.effective_date.isoformat(), 'status': h.status, 'reason': h.reason, 'notes': h.notes, 'actor': h.actor.get_username() if h.actor else None} for h in employee.employment_history.select_related('actor').all()],
                         'documents': [{'id': str(d.id), 'document_type': d.document_type, 'name': d.name, 'reference_number': d.reference_number, 'issued_date': d.issued_date.isoformat() if d.issued_date else None, 'expiry_date': d.expiry_date.isoformat() if d.expiry_date else None, 'file_url': d.file_url, 'is_verified': d.is_verified, 'is_expired': d.is_expired, 'expires_soon': d.expires_soon} for d in employee.documents.all()]})


def employee_lifecycle_action(request, employee_id):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed.'}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request.user)
    if membership is None or not membership.has_permission('manage_employees'):
        return JsonResponse({'detail': 'Employee management permission is required.'}, status=403)
    try:
        payload = json.loads(request.body or '{}')
        action = payload['action'].upper()
        effective_date = _parse_date(payload.get('effective_date'), 'effective_date') or timezone.localdate()
        allowed = {choice for choice, _ in EmployeeEmploymentHistory.Action.choices}
        if action not in allowed or action == 'PROFILE_UPDATE':
            raise ValueError('Unsupported lifecycle action.')
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        return JsonResponse({'detail': str(exc)}, status=400)
    with transaction.atomic():
        employee = Employee.objects.select_for_update().filter(id=employee_id, organization=membership.organization).first()
        if employee is None:
            return JsonResponse({'detail': 'Employee not found.'}, status=404)
        old_status = employee.status
        status_map = {'ONBOARD': Employee.Status.ONBOARDING, 'REGULARIZE': Employee.Status.REGULAR, 'SUSPEND': Employee.Status.SUSPENDED, 'REINSTATE': Employee.Status.REGULAR, 'RESIGN': Employee.Status.RESIGNED, 'TERMINATE': Employee.Status.TERMINATED, 'SEPARATE': Employee.Status.SEPARATED}
        if action in status_map:
            employee.status = status_map[action]
        if action == 'PROMOTE' and payload.get('position_id'):
            employee.position = Position.objects.filter(id=payload['position_id'], organization=employee.organization).first()
            if employee.position is None: return JsonResponse({'detail': 'Invalid position for organization.'}, status=400)
        if action == 'TRANSFER':
            for key, model in [('department_id', Department), ('position_id', Position), ('employment_type_id', EmploymentType)]:
                if key in payload:
                    value = model.objects.filter(id=payload[key], organization=employee.organization).first()
                    if value is None: return JsonResponse({'detail': f'Invalid {key[:-3]} for organization.'}, status=400)
                    setattr(employee, key[:-3], value)
        if 'manager_id' in payload:
            manager = Employee.objects.filter(id=payload['manager_id'], organization=employee.organization).first()
            if manager is None or manager.id == employee.id: return JsonResponse({'detail': 'Invalid manager.'}, status=400)
            employee.manager = manager
        if action == 'ONBOARD' and employee.hire_date is None: employee.hire_date = effective_date
        if action == 'REGULARIZE': employee.regularization_date = effective_date
        if action in {'RESIGN', 'TERMINATE', 'SEPARATE'}: employee.separation_date, employee.is_active = effective_date, False
        if action in {'ONBOARD', 'REGULARIZE', 'REINSTATE'}: employee.is_active = True
        employee.save()
        EmployeeEmploymentHistory.objects.create(employee=employee, action=action, effective_date=effective_date, status=employee.status, department=employee.department, position=employee.position, employment_type=employee.employment_type, manager=employee.manager, reason=payload.get('reason', ''), notes=payload.get('notes', ''), actor=request.user)
        AuditEvent.objects.create(organization=employee.organization, actor=request.user, action=f'employee.{action.lower()}', entity_type='Employee', entity_id=str(employee.id), details={'effective_date': effective_date.isoformat(), 'previous_status': old_status, 'new_status': employee.status, 'reason': payload.get('reason', '')})
    return JsonResponse({'employee': _employee_payload(employee), 'action': action}, status=200)


def employee_document_api(request, employee_id):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request.user)
    if membership is None or not membership.has_permission('manage_employees'):
        return JsonResponse({'detail': 'Employee management permission is required.'}, status=403)
    employee = Employee.objects.filter(id=employee_id, organization=membership.organization).first()
    if employee is None: return JsonResponse({'detail': 'Employee not found.'}, status=404)
    if request.method == 'GET':
        return JsonResponse({'documents': [{'id': str(d.id), 'document_type': d.document_type, 'name': d.name, 'reference_number': d.reference_number, 'expiry_date': d.expiry_date.isoformat() if d.expiry_date else None, 'is_expired': d.is_expired, 'expires_soon': d.expires_soon, 'is_verified': d.is_verified} for d in employee.documents.all()]})
    if request.method != 'POST': return JsonResponse({'detail': 'Method not allowed.'}, status=405)
    try: payload = json.loads(request.body or '{}'); expiry = _parse_date(payload.get('expiry_date'), 'expiry_date'); issued = _parse_date(payload.get('issued_date'), 'issued_date')
    except (json.JSONDecodeError, ValueError) as exc: return JsonResponse({'detail': str(exc)}, status=400)
    if not payload.get('name') or not payload.get('document_type'): return JsonResponse({'detail': 'name and document_type are required.'}, status=400)
    document = EmployeeDocument.objects.create(employee=employee, document_type=payload['document_type'], name=payload['name'], reference_number=payload.get('reference_number', ''), issued_date=issued, expiry_date=expiry, file_url=payload.get('file_url', ''), notes=payload.get('notes', ''))
    AuditEvent.objects.create(organization=employee.organization, actor=request.user, action='employee.document_added', entity_type='EmployeeDocument', entity_id=str(document.id), details={'employee_id': str(employee.id), 'name': document.name})
    return JsonResponse({'id': str(document.id), 'name': document.name}, status=201)

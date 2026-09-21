from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from datetime import date
import json

from apps.organization.context import current_membership
from apps.organization.models import OrganizationMembership
from apps.employees.models import Employee, EmployeeAssignment
from apps.workforce.models import ShiftTemplate, Client, ClientSite
from apps.core.services import record_audit

INELIGIBLE_ASSIGNMENT_STATUSES = {
    Employee.Status.SUSPENDED,
    Employee.Status.RESIGNED,
    Employee.Status.TERMINATED,
    Employee.Status.SEPARATED,
}


def _membership_for(request):
    return current_membership(request)


def scheduling_page(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request)
    if membership is None or not membership.has_permission('manage_attendance'):
        return JsonResponse({'detail': 'Access denied. Requires scheduling permissions.'}, status=403)
    from django.shortcuts import render
    from apps.accounts.views import workspace_url_for_user
    return render(request, 'scheduling/schedule.html', {'workspace_url': workspace_url_for_user(request.user)})


def _tenant_shift_queryset(organization):
    return ShiftTemplate.objects.filter(organization=organization) | ShiftTemplate.objects.filter(organization__isnull=True)


@require_http_methods(['GET'])
def get_shifts(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request)
    if membership is None or not membership.has_permission('manage_attendance'):
        return JsonResponse({'detail': 'Access denied.'}, status=403)
    shifts = _tenant_shift_queryset(membership.organization).order_by('name')
    return JsonResponse({'shifts': [{'id': str(shift.id), 'name': shift.name, 'start_time': shift.start_time.strftime('%H:%M'), 'end_time': shift.end_time.strftime('%H:%M')} for shift in shifts]})


@require_http_methods(['GET'])
def get_clients(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request)
    if membership is None:
        return JsonResponse({'detail': 'Access denied.'}, status=403)
    clients = Client.objects.filter(organization=membership.organization, is_active=True).prefetch_related('sites').order_by('name')
    return JsonResponse({'clients': [{'id': str(client.id), 'name': client.name, 'code': client.code, 'sites': [{'id': str(site.id), 'name': site.name} for site in client.sites.filter(is_active=True).order_by('name')]} for client in clients]})


@require_http_methods(['GET'])
def get_assignable_employees(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request)
    if membership is None or not membership.has_permission('manage_attendance'):
        return JsonResponse({'detail': 'Access denied.'}, status=403)
    employees = Employee.objects.filter(organization=membership.organization, is_active=True).exclude(status__in=INELIGIBLE_ASSIGNMENT_STATUSES).select_related('department', 'position', 'employment_type').order_by('last_name', 'first_name')
    return JsonResponse({'employees': [{'id': str(employee.id), 'employee_number': employee.employee_number, 'name': f'{employee.first_name} {employee.last_name}', 'department': employee.department.name if employee.department else None, 'position': employee.position.title if employee.position else None} for employee in employees]})


@require_http_methods(['GET'])
def get_employee_schedule(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request)
    if membership is None or not membership.has_permission('manage_attendance'):
        return JsonResponse({'detail': 'Access denied.'}, status=403)
    employee_id = request.GET.get('employee_id')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if not all([employee_id, start_date, end_date]):
        return JsonResponse({'detail': 'Missing required parameters.'}, status=400)
    try:
        employee = Employee.objects.get(id=employee_id, organization=membership.organization)
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except (Employee.DoesNotExist, ValueError):
        return JsonResponse({'detail': 'Invalid parameters.'}, status=400)
    assignments = EmployeeAssignment.objects.filter(employee=employee, start_date__lte=end).exclude(end_date__lt=start).filter(shift_template__organization__in=[membership.organization.id, None]).select_related('shift_template', 'client', 'client_site')
    return JsonResponse({'assignments': [{'id': str(assignment.id), 'shift': assignment.shift_template.name, 'shift_id': str(assignment.shift_template.id), 'client': assignment.client.name if assignment.client else None, 'client_id': str(assignment.client.id) if assignment.client else None, 'site': assignment.client_site.name if assignment.client_site else None, 'site_id': str(assignment.client_site.id) if assignment.client_site else None, 'start_date': assignment.start_date.isoformat(), 'end_date': assignment.end_date.isoformat() if assignment.end_date else None, 'is_primary': assignment.is_primary} for assignment in assignments]})


@require_http_methods(['POST'])
def assign_shift(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request)
    if membership is None or not membership.has_permission('manage_attendance'):
        return JsonResponse({'detail': 'Access denied.'}, status=403)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'detail': 'Invalid JSON.'}, status=400)
    employee_id = data.get('employee_id')
    shift_id = data.get('shift_id')
    client_id = data.get('client_id')
    site_id = data.get('site_id')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    is_primary = data.get('is_primary', False)
    assignment_id = data.get('assignment_id')
    if not all([employee_id, shift_id, start_date]):
        return JsonResponse({'detail': 'Missing required fields.'}, status=400)
    try:
        employee = Employee.objects.get(id=employee_id, organization=membership.organization)
        if employee.status in INELIGIBLE_ASSIGNMENT_STATUSES or not employee.is_active:
            return JsonResponse({'detail': 'This employee is not eligible for new shift assignments in their current lifecycle status.'}, status=409)
        shift = _tenant_shift_queryset(membership.organization).filter(id=shift_id).first()
        if shift is None:
            return JsonResponse({'detail': 'Shift template not found.'}, status=404)
        start_dt = date.fromisoformat(start_date)
        end_dt = date.fromisoformat(end_date) if end_date else None
        if end_dt and end_dt < start_dt:
            return JsonResponse({'detail': 'Assignment end date cannot be before its start date.'}, status=400)
        if employee.separation_date and start_dt >= employee.separation_date:
            return JsonResponse({'detail': 'A shift cannot start on or after the employee separation date.'}, status=409)
        client = None
        site = None
        if client_id:
            client = Client.objects.get(id=client_id, organization=membership.organization)
        if site_id:
            if not client:
                return JsonResponse({'detail': 'A site requires a client.'}, status=400)
            site = ClientSite.objects.get(id=site_id, client=client)
    except (Employee.DoesNotExist, Client.DoesNotExist, ClientSite.DoesNotExist, ValueError):
        return JsonResponse({'detail': 'Invalid parameters.'}, status=400)
    try:
        if assignment_id:
            try:
                assignment = EmployeeAssignment.objects.get(id=assignment_id, employee__organization=membership.organization, employee=employee)
            except EmployeeAssignment.DoesNotExist:
                return JsonResponse({'detail': 'Assignment not found.'}, status=404)
            assignment.shift_template = shift
            assignment.client = client
            assignment.client_site = site
            assignment.start_date = start_dt
            assignment.end_date = end_dt
            assignment.is_primary = is_primary
            assignment.full_clean()
            assignment.save()
            created = False
        else:
            assignment = EmployeeAssignment(employee=employee, shift_template=shift, start_date=start_dt, client=client, client_site=site, end_date=end_dt, is_primary=is_primary)
            assignment.full_clean()
            assignment.save()
            created = True
    except ValidationError as exc:
        return JsonResponse({'detail': 'Assignment violates a scheduling validation rule.', 'errors': exc.message_dict}, status=400)
    record_audit(organization=employee.organization, actor=request.user, action='scheduling.assign_shift', entity=assignment)
    return JsonResponse({'id': str(assignment.id), 'status': 'created' if created else 'updated', 'message': 'Shift assignment saved successfully.'})


@require_http_methods(['DELETE'])
def delete_assignment(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request)
    if membership is None or not membership.has_permission('manage_attendance'):
        return JsonResponse({'detail': 'Access denied.'}, status=403)
    try:
        data = json.loads(request.body)
        assignment_id = data.get('assignment_id')
    except json.JSONDecodeError:
        return JsonResponse({'detail': 'Invalid JSON.'}, status=400)
    try:
        assignment = EmployeeAssignment.objects.get(id=assignment_id, employee__organization=membership.organization)
        assignment.delete()
        return JsonResponse({'message': 'Assignment deleted successfully.'})
    except EmployeeAssignment.DoesNotExist:
        return JsonResponse({'detail': 'Assignment not found.'}, status=404)

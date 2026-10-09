from datetime import date, datetime
from io import BytesIO
import json

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill

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
    return render(request, 'scheduling/schedule.html', {'workspace_url': workspace_url_for_user(request.user), 'can_bulk_assign_shifts': _can_bulk_assign_shifts(membership)})


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


from apps.workforce.models import CoverShift, ScheduleException, ScheduleRule
from apps.workforce.scheduling import resolve_schedule


@require_http_methods(['GET'])
def get_schedule_calendar(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request)
    if membership is None or not membership.has_permission('manage_attendance'):
        return JsonResponse({'detail': 'Access denied.'}, status=403)
    employee_id, start_raw, end_raw = request.GET.get('employee_id'), request.GET.get('start_date'), request.GET.get('end_date')
    if not all((employee_id, start_raw, end_raw)):
        return JsonResponse({'detail': 'employee_id, start_date and end_date are required.'}, status=400)
    try:
        employee = Employee.objects.get(id=employee_id, organization=membership.organization)
        start, end = date.fromisoformat(start_raw), date.fromisoformat(end_raw)
    except (Employee.DoesNotExist, ValueError):
        return JsonResponse({'detail': 'Invalid employee or date range.'}, status=400)
    if end < start or (end - start).days > 366:
        return JsonResponse({'detail': 'Date range must be valid and no longer than 366 days.'}, status=400)
    rows, current = [], start
    while current <= end:
        resolved = resolve_schedule(employee, current)
        rows.append({
            'date': current.isoformat(),
            'kind': resolved['kind'],
            'shift_id': str(resolved['shift'].id) if resolved['shift'] else None,
            'shift': resolved['shift'].name if resolved['shift'] else None,
            'cover_shift_id': str(resolved['cover_shift'].id) if resolved['cover_shift'] else None,
            'client_id': str(resolved['client'].id) if resolved['client'] else None,
            'site_id': str(resolved['client_site'].id) if resolved['client_site'] else None,
        })
        current = current.fromordinal(current.toordinal() + 1)
    return JsonResponse({'schedule': rows})


@require_http_methods(['POST'])
def schedule_rule_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request)
    if membership is None or not membership.has_permission('manage_attendance'):
        return JsonResponse({'detail': 'Access denied.'}, status=403)
    try:
        data = json.loads(request.body)
        employee = Employee.objects.get(id=data['employee_id'], organization=membership.organization)
        shift = _tenant_shift_queryset(membership.organization).get(id=data['shift_id'])
        rule = ScheduleRule(
            employee=employee,
            shift_template=shift,
            effective_from=date.fromisoformat(data['effective_from']),
            effective_to=date.fromisoformat(data['effective_to']) if data.get('effective_to') else None,
            pattern=data.get('pattern', ScheduleRule.Pattern.WEEKLY),
            weekdays=data.get('weekdays', []),
            cycle_weeks=int(data.get('cycle_weeks', 1)),
            rotation_shifts=data.get('rotation_shifts', []),
            rest_days=data.get('rest_days', []),
            priority=int(data.get('priority', 0)),
        )
        rule.full_clean()
        rule.save()
    except (KeyError, ValueError, Employee.DoesNotExist, ShiftTemplate.DoesNotExist, ValidationError) as exc:
        return JsonResponse({'detail': 'Invalid schedule rule.', 'errors': getattr(exc, 'message_dict', str(exc))}, status=400)
    record_audit(organization=membership.organization, actor=request.user, action='scheduling.rule_created', entity=rule)
    return JsonResponse({'id': str(rule.id), 'status': 'created'})


@require_http_methods(['POST'])
def schedule_exception_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request)
    if membership is None or not membership.has_permission('manage_attendance'):
        return JsonResponse({'detail': 'Access denied.'}, status=403)
    try:
        data = json.loads(request.body)
        employee = Employee.objects.get(id=data['employee_id'], organization=membership.organization)
        shift = _tenant_shift_queryset(membership.organization).filter(id=data.get('shift_id')).first() if data.get('shift_id') else None
        exception = ScheduleException(
            employee=employee,
            work_date=date.fromisoformat(data['work_date']),
            shift_template=shift,
            is_rest_day=bool(data.get('is_rest_day', False)),
            reason=str(data.get('reason', '')).strip(),
            approved=False,
        )
        exception.full_clean()
        exception.save()
    except (KeyError, ValueError, Employee.DoesNotExist, ValidationError) as exc:
        return JsonResponse({'detail': 'Invalid schedule exception.', 'errors': getattr(exc, 'message_dict', str(exc))}, status=400)
    record_audit(organization=membership.organization, actor=request.user, action='scheduling.exception_created', entity=exception)
    return JsonResponse({'id': str(exception.id), 'status': 'PENDING'})


@require_http_methods(['POST'])
def schedule_exception_decision(request, exception_id):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request)
    if membership is None or not membership.has_permission('manage_attendance'):
        return JsonResponse({'detail': 'Access denied.'}, status=403)
    try:
        data = json.loads(request.body)
        exception = ScheduleException.objects.get(id=exception_id, employee__organization=membership.organization)
        approved = bool(data.get('approved'))
        exception.approved = approved
        exception.approved_by = request.user if approved else None
        exception.save(update_fields=('approved', 'approved_by', 'updated_at'))
    except (json.JSONDecodeError, ScheduleException.DoesNotExist):
        return JsonResponse({'detail': 'Schedule exception not found or invalid JSON.'}, status=400)
    record_audit(organization=membership.organization, actor=request.user, action='scheduling.exception_decision', entity=exception, details={'approved': approved})
    return JsonResponse({'status': 'APPROVED' if approved else 'REJECTED'})


@require_http_methods(['POST'])
def cover_shift_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request)
    if membership is None or not membership.has_permission('manage_attendance'):
        return JsonResponse({'detail': 'Access denied.'}, status=403)
    try:
        data = json.loads(request.body)
        employee = Employee.objects.get(id=data['employee_id'], organization=membership.organization)
        shift = _tenant_shift_queryset(membership.organization).get(id=data['shift_id'])
        client = Client.objects.filter(id=data.get('client_id'), organization=membership.organization).first() if data.get('client_id') else None
        site = ClientSite.objects.filter(id=data.get('site_id'), client=client).first() if data.get('site_id') and client else None
        cover = CoverShift(
            employee=employee,
            work_date=date.fromisoformat(data['work_date']),
            shift_template=shift,
            client=client,
            client_site=site,
            reason=str(data.get('reason', '')).strip(),
            requested_by=request.user,
        )
        cover.full_clean()
        cover.save()
    except (KeyError, ValueError, Employee.DoesNotExist, ShiftTemplate.DoesNotExist, ValidationError) as exc:
        return JsonResponse({'detail': 'Invalid cover shift.', 'errors': getattr(exc, 'message_dict', str(exc))}, status=400)
    record_audit(organization=membership.organization, actor=request.user, action='scheduling.cover_shift_requested', entity=cover)
    return JsonResponse({'id': str(cover.id), 'status': cover.status})


@require_http_methods(['POST'])
def cover_shift_decision(request, cover_shift_id):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request)
    if membership is None or not membership.has_permission('manage_attendance'):
        return JsonResponse({'detail': 'Access denied.'}, status=403)
    try:
        data = json.loads(request.body)
        cover = CoverShift.objects.select_for_update().get(id=cover_shift_id, employee__organization=membership.organization)
        if cover.requested_by_id == request.user.id:
            return JsonResponse({'detail': 'The requester cannot approve their own cover shift.'}, status=409)
        approved = bool(data.get('approved'))
        cover.status = CoverShift.Status.APPROVED if approved else CoverShift.Status.REJECTED
        cover.approved_by = request.user if approved else None
        cover.approved_at = timezone.now() if approved else None
        cover.save(update_fields=('status', 'approved_by', 'approved_at', 'updated_at'))
    except (json.JSONDecodeError, CoverShift.DoesNotExist):
        return JsonResponse({'detail': 'Cover shift not found or invalid JSON.'}, status=400)
    record_audit(organization=membership.organization, actor=request.user, action='scheduling.cover_shift_decision', entity=cover, details={'approved': approved})
    return JsonResponse({'status': cover.status})


# Excel-based bulk shift assignment for HR and SME.

SHIFT_ASSIGNMENT_HEADERS = ('Employee Number', 'Shift Name', 'Start Date', 'End Date', 'Client Code', 'Site Name', 'Primary')


def _can_bulk_assign_shifts(membership):
    return membership and membership.has_permission('manage_attendance') and membership.role in (
        OrganizationMembership.Role.HR,
        OrganizationMembership.Role.SME,
        OrganizationMembership.Role.OWNER,
        OrganizationMembership.Role.SUPER_USER,
    )


@require_http_methods(['GET'])
def shift_assignment_template(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request)
    if not _can_bulk_assign_shifts(membership):
        return JsonResponse({'detail': 'HR or SME access is required to download this template.'}, status=403)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Shift Assignments'
    sheet.append(SHIFT_ASSIGNMENT_HEADERS)
    sheet.append(['EMP-000001', 'Day Shift', timezone.localdate(), None, '', '', 'TRUE'])
    for cell in sheet[1]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill('solid', fgColor='1F4E78')
    sheet['C2'].number_format = sheet['D2'].number_format = 'yyyy-mm-dd'
    for column, width in zip('ABCDEFG', (22, 28, 16, 16, 18, 24, 12)):
        sheet.column_dimensions[column].width = width
    sheet.freeze_panes = 'A2'
    buffer = BytesIO()
    workbook.save(buffer)
    response = HttpResponse(buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="bizflow-shift-assignment-template.xlsx"'
    return response


@require_http_methods(['POST'])
def import_shift_assignments(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request)
    if not _can_bulk_assign_shifts(membership):
        return JsonResponse({'detail': 'HR or SME access is required to upload shift assignments.'}, status=403)
    uploaded = request.FILES.get('file')
    if uploaded is None or not uploaded.name.lower().endswith('.xlsx'):
        return JsonResponse({'detail': 'Upload an .xlsx shift assignment workbook.'}, status=400)
    if uploaded.size > 5 * 1024 * 1024:
        return JsonResponse({'detail': 'The workbook must be 5 MB or smaller.'}, status=400)
    try:
        workbook = load_workbook(uploaded, read_only=True, data_only=True)
        sheet = workbook.active
        header_row = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), None)
        headers = tuple(value.strip() if isinstance(value, str) else value for value in (header_row or ()))
        if headers != SHIFT_ASSIGNMENT_HEADERS:
            workbook.close()
            return JsonResponse({'detail': f'Headers must be exactly: {", ".join(SHIFT_ASSIGNMENT_HEADERS)}.'}, status=400)
        raw_rows = []
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if len(raw_rows) >= 1000:
                workbook.close()
                return JsonResponse({'detail': 'A workbook may contain at most 1,000 assignment rows. Split larger uploads into separate files.'}, status=400)
            raw_rows.append(row)
        workbook.close()
    except Exception:
        return JsonResponse({'detail': 'The workbook could not be read. Download and use the supplied template.'}, status=400)

    errors, prepared, seen = [], [], set()
    for row_number, row in enumerate(raw_rows, start=2):
        values = list(row) + [None] * (len(SHIFT_ASSIGNMENT_HEADERS) - len(row))
        if not any(value not in (None, '') for value in values):
            continue
        try:
            employee_number, shift_name, start_value, end_value, client_code, site_name, primary_value = values[:7]
            if not isinstance(employee_number, str) or not employee_number.strip():
                raise ValueError('Employee Number is required.')
            if not isinstance(shift_name, str) or not shift_name.strip():
                raise ValueError('Shift Name is required.')
            def parse_excel_date(value, field, required=False):
                if value in (None, ''):
                    if required:
                        raise ValueError(f'{field} is required.')
                    return None
                if isinstance(value, datetime):
                    return value.date()
                if isinstance(value, date):
                    return value
                if isinstance(value, str):
                    try:
                        return date.fromisoformat(value.strip())
                    except ValueError:
                        raise ValueError(f'{field} must be an Excel date or YYYY-MM-DD.')
                raise ValueError(f'{field} must be an Excel date or YYYY-MM-DD.')
            start_day = parse_excel_date(start_value, 'Start Date', required=True)
            end_day = parse_excel_date(end_value, 'End Date')
            if end_day and end_day < start_day:
                raise ValueError('End Date cannot be before Start Date.')
            if isinstance(primary_value, bool):
                is_primary = primary_value
            elif primary_value in (None, ''):
                is_primary = False
            elif str(primary_value).strip().upper() in ('TRUE', 'YES', 'Y', '1'):
                is_primary = True
            elif str(primary_value).strip().upper() in ('FALSE', 'NO', 'N', '0'):
                is_primary = False
            else:
                raise ValueError('Primary must be TRUE or FALSE.')
            employee_number = employee_number.strip()
            key = (employee_number.casefold(), shift_name.strip().casefold(), start_day.isoformat())
            if key in seen:
                raise ValueError('Duplicate employee/start-date row in this workbook.')
            seen.add(key)
            employee = Employee.objects.filter(employee_number=employee_number, organization=membership.organization, is_active=True).exclude(status__in=INELIGIBLE_ASSIGNMENT_STATUSES).first()
            if employee is None:
                raise ValueError('Active eligible employee was not found in this organization.')
            shift = _tenant_shift_queryset(membership.organization).filter(name__iexact=shift_name.strip()).first()
            if shift is None:
                raise ValueError('Shift Name was not found in this organization.')
            if employee.separation_date and start_day >= employee.separation_date:
                raise ValueError('Shift cannot start on or after the employee separation date.')
            client = None
            site = None
            if client_code not in (None, ''):
                client = Client.objects.filter(organization=membership.organization, code__iexact=str(client_code).strip(), is_active=True).first()
                if client is None:
                    raise ValueError('Client Code was not found in this organization.')
            if site_name not in (None, ''):
                if client is None:
                    raise ValueError('Client Code is required when Site Name is supplied.')
                site = ClientSite.objects.filter(client=client, name__iexact=str(site_name).strip(), is_active=True).first()
                if site is None:
                    raise ValueError('Site Name was not found under the selected client.')
            if EmployeeAssignment.objects.filter(employee=employee, start_date=start_day, shift_template=shift).exists():
                raise ValueError('This employee already has this shift assignment starting on this date.')
            assignment = EmployeeAssignment(employee=employee, shift_template=shift, client=client, client_site=site, start_date=start_day, end_date=end_day, is_primary=is_primary)
            assignment.full_clean()
            prepared.append((row_number, assignment, employee))
        except (TypeError, ValueError, ValidationError) as error:
            detail = '; '.join(error.messages) if isinstance(error, ValidationError) else str(error)
            errors.append({'row': row_number, 'detail': detail})

    if not prepared and not errors:
        return JsonResponse({'detail': 'The workbook contains no assignment rows.'}, status=400)
    if errors:
        return JsonResponse({'detail': 'No assignments were imported. Fix the listed rows and upload the workbook again.', 'errors': errors}, status=400)

    try:
        with transaction.atomic():
            for row_number, assignment, employee in prepared:
                assignment.save()
                record_audit(organization=membership.organization, actor=request.user, action='scheduling.bulk_assign_shift', entity=assignment, details={'source': uploaded.name, 'row': row_number, 'employee_number': employee.employee_number})
    except Exception:
        return JsonResponse({'detail': 'No assignments were imported because saving failed. Check the workbook and try again.'}, status=400)
    return JsonResponse({'imported': len(prepared), 'source': uploaded.name, 'message': f'Successfully imported {len(prepared)} shift assignment(s).'})

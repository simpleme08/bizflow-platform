import json
from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.core.services import record_audit
from apps.organization.models import OrganizationMembership
from .models import ApprovalRequest, Announcement, DocumentAcknowledgement, EmployeeDocument, ExternalConnector, ProfileChangeRequest, Project, TimesheetEntry


def _membership(request):
    return OrganizationMembership.objects.filter(user=request.user, is_active=True, organization__is_active=True).select_related('organization').first()


def _access(request, management=False):
    if not request.user.is_authenticated:
        return None, JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership(request)
    if membership is None or (management and not membership.has_permission('manage_employees')):
        return None, JsonResponse({'detail': 'Access is not available for this account.'}, status=403)
    return membership, None


def _json(request):
    return json.loads(request.body or '{}')


def _can_approve_timesheets(membership):
    return membership.has_permission('manage_employees') or membership.has_permission('manage_attendance')


def operations_page(request):
    membership, error = _access(request, management=True)
    if error:
        return redirect('login') if not request.user.is_authenticated else error
    return render(request, 'operations/operations.html')


def employee_hub_page(request):
    membership, error = _access(request)
    if error:
        return redirect('login')
    return render(request, 'operations/employee_hub.html')


@require_http_methods(['GET', 'POST'])
def employee_hub_api(request):
    membership, error = _access(request)
    if error:
        return error
    try:
        employee = request.user.employee_profile
    except AttributeError:
        return JsonResponse({'detail': 'No employee profile is linked to this account.'}, status=404)
    # A user may have memberships in multiple organizations. The employee profile
    # is the authoritative tenant boundary for self-service data and mutations.
    if employee.organization_id != membership.organization_id or not employee.organization.is_active:
        return JsonResponse({'detail': 'Employee organization access is not available.'}, status=403)
    if request.method == 'GET':
        today = timezone.localdate()
        docs = EmployeeDocument.objects.filter(organization=membership.organization, status=EmployeeDocument.Status.PUBLISHED).filter(Q(expires_on__isnull=True) | Q(expires_on__gte=today)).order_by('title')
        acknowledged = set(DocumentAcknowledgement.objects.filter(employee=employee, document__in=docs).values_list('document_id', flat=True))
        announcements = Announcement.objects.filter(organization=membership.organization, is_published=True).filter(Q(expires_on__isnull=True) | Q(expires_on__gte=today)).order_by('-published_at')
        return JsonResponse({
            'documents': [{'id': str(d.id), 'title': d.title, 'category': d.category, 'body': d.body, 'requires_acknowledgement': d.requires_acknowledgement, 'acknowledged': d.id in acknowledged, 'file_url': d.file_url} for d in docs],
            'announcements': [{'id': str(a.id), 'title': a.title, 'message': a.message, 'published_at': a.published_at.isoformat() if a.published_at else None} for a in announcements],
            'profile': {'first_name': employee.first_name, 'last_name': employee.last_name, 'email': request.user.email},
            'profile_requests': [{'id': str(r.id), 'changes': r.requested_changes, 'status': r.status, 'remarks': r.remarks, 'created_at': r.created_at.isoformat()} for r in employee.profile_change_requests.order_by('-created_at')[:20]],
            'projects': [{'id': str(p.id), 'code': p.code, 'name': p.name} for p in Project.objects.filter(organization=membership.organization, is_active=True).order_by('code')],
            'timesheets': [{'id': str(t.id), 'project': t.project.name, 'date': t.work_date.isoformat(), 'hours': str(t.hours), 'notes': t.notes, 'status': t.status} for t in employee.timesheet_entries.select_related('project').order_by('-work_date')[:30]],
        })
    try:
        payload = _json(request)
        kind = payload['kind']
        if kind == 'profile_change':
            changes = payload['changes']
            allowed = {'first_name', 'last_name', 'email'}
            if not isinstance(changes, dict) or not changes or set(changes) - allowed:
                raise ValueError
            changes = {key: str(value).strip() for key, value in changes.items() if str(value).strip()}
            if not changes:
                raise ValueError
            item = ProfileChangeRequest.objects.create(employee=employee, requested_changes=changes)
        elif kind == 'acknowledge_document':
            document = EmployeeDocument.objects.get(id=payload['document_id'], organization=membership.organization, status=EmployeeDocument.Status.PUBLISHED)
            item, _ = DocumentAcknowledgement.objects.get_or_create(document=document, employee=employee)
        elif kind == 'timesheet':
            project = Project.objects.get(id=payload['project_id'], organization=membership.organization, is_active=True)
            hours = Decimal(str(payload['hours']))
            work_date = date.fromisoformat(payload['work_date'])
            if hours <= 0 or hours > 24 or work_date > timezone.localdate():
                raise ValueError
            item = TimesheetEntry.objects.create(employee=employee, project=project, work_date=work_date, hours=hours, notes=str(payload.get('notes', '')).strip(), status=TimesheetEntry.Status.SUBMITTED)
        else:
            raise ValueError
    except (KeyError, ValueError, TypeError, InvalidOperation, json.JSONDecodeError, EmployeeDocument.DoesNotExist, Project.DoesNotExist):
        return JsonResponse({'detail': 'Provide valid employee-service data.'}, status=400)
    record_audit(organization=membership.organization, actor=request.user, action='employee_hub.submitted', entity=item)
    return JsonResponse({'id': str(item.id)}, status=201)


@require_http_methods(['GET', 'POST'])
def operations_api(request):
    membership, error = _access(request, management=True)
    if error:
        return error
    org = membership.organization
    if request.method == 'GET':
        approvers = OrganizationMembership.objects.filter(organization=org, is_active=True).select_related('user')
        return JsonResponse({
            'approvals': [{'id': str(a.id), 'title': a.title, 'category': a.category, 'status': a.status, 'requester': a.requester.get_username(), 'approver': a.approver.get_username() if a.approver else '', 'decision_note': a.decision_note} for a in ApprovalRequest.objects.filter(organization=org).select_related('requester', 'approver').order_by('-created_at')[:50]],
            'documents': [{'id': str(d.id), 'title': d.title, 'category': d.category, 'status': d.status, 'required': d.requires_acknowledgement} for d in EmployeeDocument.objects.filter(organization=org).order_by('-created_at')],
            'announcements': [{'id': str(a.id), 'title': a.title, 'is_published': a.is_published} for a in Announcement.objects.filter(organization=org).order_by('-created_at')],
            'projects': [{'id': str(p.id), 'code': p.code, 'name': p.name, 'billable': p.is_billable} for p in Project.objects.filter(organization=org).order_by('code')],
            'connectors': [{'id': str(c.id), 'name': c.name, 'kind': c.kind, 'enabled': c.is_enabled} for c in ExternalConnector.objects.filter(organization=org).order_by('name')],
            'profile_requests': [{'id': str(r.id), 'employee': str(r.employee), 'changes': r.requested_changes, 'status': r.status, 'remarks': r.remarks} for r in ProfileChangeRequest.objects.filter(employee__organization=org).select_related('employee').order_by('-created_at')[:50]],
            'timesheets': [{'id': str(t.id), 'employee': str(t.employee), 'project': t.project.name, 'date': t.work_date.isoformat(), 'hours': str(t.hours), 'status': t.status} for t in TimesheetEntry.objects.filter(employee__organization=org).select_related('employee', 'project').order_by('-work_date')[:50]],
            'approvers': [{'id': str(m.user_id), 'name': m.user.get_username(), 'role': m.role} for m in approvers if m.has_permission('manage_employees')],
        })
    try:
        payload = _json(request)
        kind = payload['kind']
        if kind == 'document':
            status = payload.get('status', EmployeeDocument.Status.DRAFT)
            if status not in EmployeeDocument.Status.values:
                raise ValueError
            item = EmployeeDocument.objects.create(organization=org, title=str(payload['title']).strip(), category=str(payload.get('category', 'Policy')).strip(), body=str(payload.get('body', '')).strip(), requires_acknowledgement=bool(payload.get('requires_acknowledgement', False)), status=status)
        elif kind == 'announcement':
            published = bool(payload.get('is_published', True))
            item = Announcement.objects.create(organization=org, title=str(payload['title']).strip(), message=str(payload['message']).strip(), is_published=published, published_at=timezone.now() if published else None)
        elif kind == 'project':
            item = Project.objects.create(organization=org, code=str(payload['code']).strip().upper(), name=str(payload['name']).strip(), is_billable=bool(payload.get('is_billable', False)))
        elif kind == 'connector':
            connector_kind = payload['connector_kind']
            if connector_kind not in ExternalConnector.Kind.values:
                raise ValueError
            item = ExternalConnector.objects.create(organization=org, name=str(payload['name']).strip(), kind=connector_kind, endpoint=str(payload.get('endpoint', '')).strip(), configuration=payload.get('configuration', {}), is_enabled=False)
        elif kind == 'approval':
            approver_id = payload.get('approver_id')
            if approver_id and not OrganizationMembership.objects.filter(organization=org, user_id=approver_id, is_active=True).exists():
                raise ValueError
            item = ApprovalRequest.objects.create(organization=org, requester=request.user, approver_id=approver_id, category=str(payload['category']).strip(), title=str(payload['title']).strip(), payload=payload.get('payload', {}))
        else:
            raise ValueError
        if not getattr(item, 'title', getattr(item, 'name', '')).strip():
            raise ValueError
    except (KeyError, ValueError, TypeError, IntegrityError, json.JSONDecodeError):
        return JsonResponse({'detail': 'Provide valid operations data. Project codes must be unique.'}, status=400)
    record_audit(organization=org, actor=request.user, action=f'operations.{kind}.created', entity=item)
    return JsonResponse({'id': str(item.id)}, status=201)


@require_http_methods(['POST'])
def approval_decision(request, approval_id):
    membership, error = _access(request, management=True)
    if error:
        return error
    try:
        approval = ApprovalRequest.objects.get(id=approval_id, organization=membership.organization, status=ApprovalRequest.Status.PENDING)
        if approval.approver_id and approval.approver_id != request.user.id:
            return JsonResponse({'detail': 'This approval is assigned to another approver.'}, status=403)
        payload = _json(request)
        decision = payload['decision']
        if decision not in ('approve', 'reject'):
            raise ValueError
        approval.status = ApprovalRequest.Status.APPROVED if decision == 'approve' else ApprovalRequest.Status.REJECTED
        approval.approver = request.user
        approval.decision_note = str(payload.get('note', '')).strip()
        approval.decided_at = timezone.now()
        approval.save()
    except (ApprovalRequest.DoesNotExist, KeyError, ValueError, json.JSONDecodeError):
        return JsonResponse({'detail': 'A valid pending approval and decision are required.'}, status=400)
    record_audit(organization=membership.organization, actor=request.user, action=f'approval.{decision}d', entity=approval)
    return JsonResponse({'id': str(approval.id), 'status': approval.status})


@require_http_methods(['POST'])
def profile_request_decision(request, request_id):
    membership, error = _access(request, management=True)
    if error:
        return error
    try:
        item = ProfileChangeRequest.objects.select_related('employee__user').get(id=request_id, employee__organization=membership.organization, status=ProfileChangeRequest.Status.PENDING)
        payload = _json(request)
        decision = payload['decision']
        if decision not in ('approve', 'reject'):
            raise ValueError
        item.status = ProfileChangeRequest.Status.APPROVED if decision == 'approve' else ProfileChangeRequest.Status.REJECTED
        item.reviewer = request.user
        item.remarks = str(payload.get('note', '')).strip()
        if decision == 'approve':
            changes = item.requested_changes
            for field in ('first_name', 'last_name'):
                if field in changes:
                    setattr(item.employee, field, str(changes[field]).strip())
                    setattr(item.employee.user, field, str(changes[field]).strip())
            if 'email' in changes:
                item.employee.user.email = str(changes['email']).strip()
            item.employee.save()
            item.employee.user.save()
        item.save()
    except (ProfileChangeRequest.DoesNotExist, KeyError, ValueError, json.JSONDecodeError):
        return JsonResponse({'detail': 'A valid pending profile request and decision are required.'}, status=400)
    record_audit(organization=membership.organization, actor=request.user, action=f'profile_change.{decision}d', entity=item)
    return JsonResponse({'id': str(item.id), 'status': item.status})


@require_http_methods(['POST'])
def timesheet_decision(request, entry_id):
    membership, error = _access(request)
    if error:
        return error
    if not _can_approve_timesheets(membership):
        return JsonResponse({'detail': 'You do not have permission to approve timesheets.'}, status=403)
    try:
        item = TimesheetEntry.objects.get(id=entry_id, employee__organization=membership.organization, status=TimesheetEntry.Status.SUBMITTED)
        payload = _json(request)
        decision = payload['decision']
        if decision not in ('approve', 'reject'):
            raise ValueError
        item.status = TimesheetEntry.Status.APPROVED if decision == 'approve' else TimesheetEntry.Status.REJECTED
        item.approver = request.user
        item.save()
    except (TimesheetEntry.DoesNotExist, KeyError, ValueError, json.JSONDecodeError):
        return JsonResponse({'detail': 'A valid submitted timesheet and decision are required.'}, status=400)
    record_audit(organization=membership.organization, actor=request.user, action=f'timesheet.{decision}d', entity=item)
    return JsonResponse({'id': str(item.id), 'status': item.status})

import json
from datetime import date

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.employees.models import Employee
from apps.core.services import record_audit
from apps.onboarding.models import EmployeeOnboarding, OnboardingTask, OnboardingTaskTemplate, OnboardingWorkflow
from apps.organization.context import current_membership


def _membership_for(request):
    return current_membership(request)


def onboarding_page(request):
    if not request.user.is_authenticated:
        return redirect('login')
    membership = _membership_for(request)
    if membership is None or not membership.has_permission('manage_employees'):
        return JsonResponse({'detail': 'Onboarding access required.'}, status=403)
    return render(request, 'onboarding/onboarding.html')


@require_http_methods(['GET', 'POST'])
def onboarding_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request)
    if membership is None or not membership.has_permission('manage_employees'):
        return JsonResponse({'detail': 'Onboarding access required.'}, status=403)

    if request.method == 'GET':
        workflows = OnboardingWorkflow.objects.filter(organization=membership.organization, is_active=True).order_by('name')
        records = EmployeeOnboarding.objects.filter(employee__organization=membership.organization).select_related('employee', 'workflow')
        return JsonResponse({'workflows': [{'id': str(workflow.id), 'name': workflow.name} for workflow in workflows], 'records': [{'id': str(record.id), 'employee': f'{record.employee.first_name} {record.employee.last_name}', 'employee_number': record.employee.employee_number, 'workflow': record.workflow.name, 'status': record.status, 'start_date': record.start_date.isoformat() if record.start_date else None, 'expected_completion_date': record.expected_completion_date.isoformat() if record.expected_completion_date else None, 'tasks': [{'id': str(task.id), 'title': task.title, 'description': task.description, 'status': task.status, 'due_date': task.due_date.isoformat() if task.due_date else None} for task in record.tasks.all()]} for record in records]})

    try:
        payload = json.loads(request.body or '{}')
        employee = Employee.objects.get(id=payload['employee_id'], organization=membership.organization, is_active=True)
        workflow = OnboardingWorkflow.objects.get(id=payload['workflow_id'], organization=membership.organization, is_active=True)
        start_date = date.fromisoformat(payload['start_date']) if payload.get('start_date') else None
        expected_completion_date = date.fromisoformat(payload['expected_completion_date']) if payload.get('expected_completion_date') else None
    except (KeyError, ValueError, json.JSONDecodeError, Employee.DoesNotExist, OnboardingWorkflow.DoesNotExist):
        return JsonResponse({'detail': 'Provide valid employee_id, workflow_id, start_date, and expected_completion_date.'}, status=400)

    onboarding, _ = EmployeeOnboarding.objects.get_or_create(employee=employee, defaults={'workflow': workflow, 'start_date': start_date, 'expected_completion_date': expected_completion_date, 'status': EmployeeOnboarding.Status.NOT_STARTED})
    if start_date:
        onboarding.start_date = start_date
    if expected_completion_date:
        onboarding.expected_completion_date = expected_completion_date
    onboarding.workflow = workflow
    onboarding.status = onboarding.status or EmployeeOnboarding.Status.NOT_STARTED
    onboarding.save(update_fields=('workflow', 'start_date', 'expected_completion_date', 'status', 'updated_at'))

    for template in workflow.task_templates.all().order_by('order'):
        OnboardingTask.objects.get_or_create(onboarding=onboarding, template=template, defaults={'title': template.title, 'description': template.description, 'due_date': expected_completion_date, 'status': OnboardingTask.Status.PENDING})

    return JsonResponse({'id': str(onboarding.id), 'status': onboarding.status}, status=201)


@require_http_methods(['PATCH'])
def onboarding_status_update(request, onboarding_id):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request)
    if membership is None or not membership.has_permission('manage_employees'):
        return JsonResponse({'detail': 'Onboarding access required.'}, status=403)
    try:
        onboarding = EmployeeOnboarding.objects.select_related('workflow', 'employee').get(
            id=onboarding_id,
            employee__organization=membership.organization,
        )
        payload = json.loads(request.body or '{}')
        new_status = payload.get('status')
    except (EmployeeOnboarding.DoesNotExist, json.JSONDecodeError):
        return JsonResponse({'detail': 'Invalid onboarding record or JSON.'}, status=400)
    if new_status not in {choice.value for choice in EmployeeOnboarding.Status}:
        return JsonResponse({'detail': 'Invalid onboarding status.'}, status=400)
    if new_status == EmployeeOnboarding.Status.COMPLETED:
        required = [str(item).strip() for item in (onboarding.workflow.required_document_types or []) if str(item).strip()]
        missing = []
        for document_type in required:
            if not onboarding.employee.documents.filter(
                document_type__iexact=document_type,
                status='ACTIVE',
            ).filter(
                models_q_expiry_valid()
            ).exists():
                missing.append(document_type)
        incomplete_required_tasks = onboarding.tasks.filter(
            template__is_required=True,
        ).exclude(status=OnboardingTask.Status.COMPLETED).count()
        if missing or incomplete_required_tasks:
            return JsonResponse({
                'detail': 'Onboarding cannot be completed until required documents and tasks are complete.',
                'missing_document_types': missing,
                'incomplete_required_tasks': incomplete_required_tasks,
            }, status=409)
    onboarding.status = new_status
    onboarding.save(update_fields=('status', 'updated_at'))
    record_audit(
        organization=membership.organization,
        actor=request.user,
        action='onboarding.status_changed',
        entity=onboarding,
        details={'status': new_status},
    )
    return JsonResponse({'id': str(onboarding.id), 'status': onboarding.status})


def models_q_expiry_valid():
    from django.db.models import Q
    return Q(expiry_date__isnull=True) | Q(expiry_date__gte=timezone.localdate())


@require_http_methods(['PATCH'])
def onboarding_task_update(request, onboarding_id, task_id):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request)
    if membership is None or not membership.has_permission('manage_employees'):
        return JsonResponse({'detail': 'Onboarding access required.'}, status=403)
    try:
        task = OnboardingTask.objects.get(id=task_id, onboarding_id=onboarding_id, onboarding__employee__organization=membership.organization)
    except OnboardingTask.DoesNotExist:
        return JsonResponse({'detail': 'Task not found.'}, status=404)
    try:
        payload = json.loads(request.body or '{}')
        new_status = payload.get('status')
    except json.JSONDecodeError:
        return JsonResponse({'detail': 'Invalid JSON.'}, status=400)
    if new_status not in {choice.value for choice in OnboardingTask.Status}:
        return JsonResponse({'detail': 'Invalid status value.'}, status=400)
    task.status = new_status
    task.completed_at = timezone.now() if new_status == OnboardingTask.Status.COMPLETED else None
    task.save(update_fields=('status', 'completed_at', 'updated_at'))
    return JsonResponse({'id': str(task.id), 'status': task.status})

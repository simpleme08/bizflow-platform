import json
from datetime import date

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.employees.models import Employee
from apps.onboarding.models import EmployeeOnboarding, OnboardingTask, OnboardingTaskTemplate, OnboardingWorkflow
from apps.organization.models import OrganizationMembership


def _membership_for(user):
    return OrganizationMembership.objects.filter(
        user=user,
        is_active=True,
        organization__is_active=True,
    ).select_related('organization').first()


def onboarding_page(request):
    if not request.user.is_authenticated:
        return redirect('login')
    membership = _membership_for(request.user)
    if membership is None or not membership.has_permission('manage_employees'):
        return JsonResponse({'detail': 'Onboarding access required.'}, status=403)
    return render(request, 'onboarding/onboarding.html')


@require_http_methods(['GET', 'POST'])
def onboarding_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request.user)
    if membership is None or not membership.has_permission('manage_employees'):
        return JsonResponse({'detail': 'Onboarding access required.'}, status=403)

    if request.method == 'GET':
        workflows = OnboardingWorkflow.objects.filter(organization=membership.organization, is_active=True).order_by('name')
        records = EmployeeOnboarding.objects.filter(employee__organization=membership.organization).select_related('employee', 'workflow')
        return JsonResponse({
            'workflows': [{
                'id': str(workflow.id),
                'name': workflow.name,
            } for workflow in workflows],
            'records': [{
                'id': str(record.id),
                'employee': f'{record.employee.first_name} {record.employee.last_name}',
                'employee_number': record.employee.employee_number,
                'workflow': record.workflow.name,
                'status': record.status,
                'start_date': record.start_date.isoformat() if record.start_date else None,
                'expected_completion_date': record.expected_completion_date.isoformat() if record.expected_completion_date else None,
                'tasks': [{
                    'id': str(task.id),
                    'title': task.title,
                    'description': task.description,
                    'status': task.status,
                    'due_date': task.due_date.isoformat() if task.due_date else None,
                } for task in record.tasks.all()],
            } for record in records]
        })

    payload = json.loads(request.body or '{}')
    try:
        employee = Employee.objects.get(id=payload['employee_id'], organization=membership.organization, is_active=True)
        workflow = OnboardingWorkflow.objects.get(id=payload['workflow_id'], organization=membership.organization, is_active=True)
        start_date = date.fromisoformat(payload['start_date']) if payload.get('start_date') else None
        expected_completion_date = date.fromisoformat(payload['expected_completion_date']) if payload.get('expected_completion_date') else None
    except (KeyError, ValueError, json.JSONDecodeError, Employee.DoesNotExist, OnboardingWorkflow.DoesNotExist):
        return JsonResponse({'detail': 'Provide valid employee_id, workflow_id, start_date, and expected_completion_date.'}, status=400)

    onboarding, _ = EmployeeOnboarding.objects.get_or_create(
        employee=employee,
        defaults={
            'workflow': workflow,
            'start_date': start_date,
            'expected_completion_date': expected_completion_date,
            'status': EmployeeOnboarding.Status.NOT_STARTED,
        },
    )
    if start_date:
        onboarding.start_date = start_date
    if expected_completion_date:
        onboarding.expected_completion_date = expected_completion_date
    onboarding.workflow = workflow
    onboarding.status = onboarding.status or EmployeeOnboarding.Status.NOT_STARTED
    onboarding.save(update_fields=('workflow', 'start_date', 'expected_completion_date', 'status', 'updated_at'))

    for template in workflow.task_templates.all().order_by('order'):
        OnboardingTask.objects.get_or_create(
            onboarding=onboarding,
            template=template,
            defaults={
                'title': template.title,
                'description': template.description,
                'due_date': expected_completion_date,
                'status': OnboardingTask.Status.PENDING,
            },
        )

    return JsonResponse({'id': str(onboarding.id), 'status': onboarding.status}, status=201)


@require_http_methods(['PATCH'])
def onboarding_task_update(request, onboarding_id, task_id):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership_for(request.user)
    if membership is None or not membership.has_permission('manage_employees'):
        return JsonResponse({'detail': 'Onboarding access required.'}, status=403)

    try:
        task = OnboardingTask.objects.get(id=task_id, onboarding_id=onboarding_id, onboarding__employee__organization=membership.organization)
    except OnboardingTask.DoesNotExist:
        return JsonResponse({'detail': 'Task not found.'}, status=404)

    payload = json.loads(request.body or '{}')
    new_status = payload.get('status')
    if new_status not in {choice.value for choice in OnboardingTask.Status}:
        return JsonResponse({'detail': 'Invalid status value.'}, status=400)

    task.status = new_status
    if new_status == OnboardingTask.Status.COMPLETED:
        task.completed_at = __import__('django.utils.timezone').utils.timezone.now()
    else:
        task.completed_at = None
    task.save(update_fields=('status', 'completed_at', 'updated_at'))

    return JsonResponse({'id': str(task.id), 'status': task.status})

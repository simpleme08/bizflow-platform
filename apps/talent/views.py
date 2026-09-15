import json
from datetime import date

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.core.services import record_audit
from apps.employees.models import Employee
from apps.organization.context import current_membership
from apps.organization.models import OrganizationMembership

from .models import BenefitEnrollment, BenefitPlan, Candidate, EmployeeGoal, JobApplication, JobOpening, OffboardingRecord, PerformanceCycle, PerformanceReview


def _membership(request):
    return current_membership(request)


def _require(request, permission):
    if not request.user.is_authenticated:
        return None, JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership(request)
    if membership is None or not membership.has_permission(permission):
        return None, JsonResponse({'detail': 'You do not have access to this feature.'}, status=403)
    return membership, None


def talent_page(request):
    if not request.user.is_authenticated:
        return redirect('login')
    membership = _membership(request)
    if membership is None or not membership.has_permission('manage_employees'):
        return JsonResponse({'detail': 'Talent access required.'}, status=403)
    return render(request, 'talent/talent.html')


@require_http_methods(['GET', 'POST'])
def recruiting_api(request):
    membership, error = _require(request, 'manage_recruiting')
    if error:
        return error
    if request.method == 'GET':
        jobs = JobOpening.objects.filter(organization=membership.organization).select_related('department', 'employment_type')
        candidates = Candidate.objects.filter(organization=membership.organization)
        applications = JobApplication.objects.filter(job__organization=membership.organization).select_related('job', 'candidate')
        return JsonResponse({'jobs': [{'id': str(j.id), 'title': j.title, 'status': j.status, 'department': j.department.name if j.department else None, 'applications': j.applications.count()} for j in jobs], 'candidates': [{'id': str(c.id), 'name': str(c), 'email': c.email, 'source': c.source} for c in candidates], 'applications': [{'id': str(a.id), 'job': a.job.title, 'candidate': str(a.candidate), 'stage': a.stage, 'rating': a.rating} for a in applications]})
    try:
        payload = json.loads(request.body or '{}')
        kind = payload['kind']
        if kind == 'job':
            item = JobOpening.objects.create(organization=membership.organization, title=payload['title'], description=payload.get('description', ''), location=payload.get('location', ''), status=payload.get('status', JobOpening.Status.DRAFT))
        elif kind == 'candidate':
            item = Candidate.objects.create(organization=membership.organization, first_name=payload['first_name'], last_name=payload['last_name'], email=payload['email'], phone=payload.get('phone', ''), source=payload.get('source', ''))
        elif kind == 'application':
            job = JobOpening.objects.get(id=payload['job_id'], organization=membership.organization)
            candidate = Candidate.objects.get(id=payload['candidate_id'], organization=membership.organization)
            item = JobApplication.objects.create(job=job, candidate=candidate, stage=payload.get('stage', JobApplication.Stage.APPLIED))
        else:
            raise ValueError
    except (KeyError, ValueError, json.JSONDecodeError, JobOpening.DoesNotExist, Candidate.DoesNotExist):
        return JsonResponse({'detail': 'Provide valid recruiting data.'}, status=400)
    record_audit(organization=membership.organization, actor=request.user, action=f'recruiting.{kind}.created', entity=item)
    return JsonResponse({'id': str(item.id)}, status=201)


@require_http_methods(['GET', 'POST'])
def performance_api(request):
    membership, error = _require(request, 'manage_performance')
    if error:
        return error
    if request.method == 'GET':
        cycles = PerformanceCycle.objects.filter(organization=membership.organization)
        goals = EmployeeGoal.objects.filter(employee__organization=membership.organization).select_related('employee', 'cycle')
        reviews = PerformanceReview.objects.filter(employee__organization=membership.organization).select_related('employee', 'cycle')
        return JsonResponse({'cycles': [{'id': str(c.id), 'name': c.name, 'start_date': c.start_date.isoformat(), 'end_date': c.end_date.isoformat(), 'status': c.status} for c in cycles], 'goals': [{'id': str(g.id), 'employee': str(g.employee), 'title': g.title, 'progress': g.progress, 'status': g.status} for g in goals], 'reviews': [{'id': str(r.id), 'employee': str(r.employee), 'cycle': r.cycle.name, 'rating': r.rating, 'status': r.status} for r in reviews]})
    try:
        payload = json.loads(request.body or '{}')
        kind = payload['kind']
        if kind == 'cycle':
            item = PerformanceCycle.objects.create(organization=membership.organization, name=payload['name'], start_date=date.fromisoformat(payload['start_date']), end_date=date.fromisoformat(payload['end_date']), status=payload.get('status', PerformanceCycle.Status.DRAFT))
        elif kind == 'goal':
            employee = Employee.objects.get(id=payload['employee_id'], organization=membership.organization)
            cycle = PerformanceCycle.objects.get(id=payload['cycle_id'], organization=membership.organization) if payload.get('cycle_id') else None
            item = EmployeeGoal.objects.create(employee=employee, cycle=cycle, title=payload['title'], description=payload.get('description', ''), progress=int(payload.get('progress', 0)), status=payload.get('status', EmployeeGoal.Status.NOT_STARTED))
        elif kind == 'review':
            employee = Employee.objects.get(id=payload['employee_id'], organization=membership.organization)
            cycle = PerformanceCycle.objects.get(id=payload['cycle_id'], organization=membership.organization)
            item = PerformanceReview.objects.create(cycle=cycle, employee=employee, reviewer=request.user, rating=payload.get('rating'), comments=payload.get('comments', ''), status=payload.get('status', PerformanceReview.Status.DRAFT))
        else:
            raise ValueError
    except (KeyError, ValueError, TypeError, json.JSONDecodeError, Employee.DoesNotExist, PerformanceCycle.DoesNotExist):
        return JsonResponse({'detail': 'Provide valid performance data.'}, status=400)
    record_audit(organization=membership.organization, actor=request.user, action=f'performance.{kind}.created', entity=item)
    return JsonResponse({'id': str(item.id)}, status=201)


@require_http_methods(['GET', 'POST'])
def benefits_api(request):
    membership, error = _require(request, 'manage_benefits')
    if error:
        return error
    if request.method == 'GET':
        plans = BenefitPlan.objects.filter(organization=membership.organization)
        enrollments = BenefitEnrollment.objects.filter(employee__organization=membership.organization).select_related('employee', 'plan')
        return JsonResponse({'plans': [{'id': str(p.id), 'name': p.name, 'provider': p.provider, 'employee_cost': str(p.employee_cost), 'employer_cost': str(p.employer_cost), 'is_active': p.is_active} for p in plans], 'enrollments': [{'id': str(e.id), 'employee': str(e.employee), 'plan': e.plan.name, 'effective_date': e.effective_date.isoformat(), 'status': e.status} for e in enrollments]})
    try:
        payload = json.loads(request.body or '{}')
        if payload['kind'] == 'plan':
            item = BenefitPlan.objects.create(organization=membership.organization, name=payload['name'], provider=payload.get('provider', ''), description=payload.get('description', ''), employee_cost=payload.get('employee_cost', 0), employer_cost=payload.get('employer_cost', 0))
        elif payload['kind'] == 'enrollment':
            employee = Employee.objects.get(id=payload['employee_id'], organization=membership.organization)
            plan = BenefitPlan.objects.get(id=payload['plan_id'], organization=membership.organization, is_active=True)
            item = BenefitEnrollment.objects.create(employee=employee, plan=plan, effective_date=date.fromisoformat(payload['effective_date']))
        else:
            raise ValueError
    except (KeyError, ValueError, json.JSONDecodeError, Employee.DoesNotExist, BenefitPlan.DoesNotExist):
        return JsonResponse({'detail': 'Provide valid benefit data.'}, status=400)
    record_audit(organization=membership.organization, actor=request.user, action='benefits.created', entity=item)
    return JsonResponse({'id': str(item.id)}, status=201)


@require_http_methods(['GET', 'POST'])
def offboarding_api(request):
    membership, error = _require(request, 'manage_offboarding')
    if error:
        return error
    if request.method == 'GET':
        records = OffboardingRecord.objects.filter(employee__organization=membership.organization).select_related('employee')
        return JsonResponse({'records': [{'id': str(r.id), 'employee': str(r.employee), 'last_working_day': r.last_working_day.isoformat(), 'reason': r.reason, 'status': r.status} for r in records]})
    try:
        payload = json.loads(request.body or '{}')
        employee = Employee.objects.get(id=payload['employee_id'], organization=membership.organization)
        item = OffboardingRecord.objects.create(employee=employee, last_working_day=date.fromisoformat(payload['last_working_day']), reason=payload.get('reason', ''), notes=payload.get('notes', ''))
    except (KeyError, ValueError, json.JSONDecodeError, Employee.DoesNotExist):
        return JsonResponse({'detail': 'Provide a valid employee and last working day.'}, status=400)
    record_audit(organization=membership.organization, actor=request.user, action='offboarding.created', entity=item)
    return JsonResponse({'id': str(item.id)}, status=201)

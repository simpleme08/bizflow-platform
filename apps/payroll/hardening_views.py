from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.core.services import record_audit
from apps.organization.models import OrganizationMembership

from .completion import settle_loans_for_record
from .hardening import PayrollConfidence
from .models import PayrollPeriod, PayrollRecord
from .views import _membership


APPROVER_ROLES = {OrganizationMembership.Role.OWNER, OrganizationMembership.Role.SUPER_USER, OrganizationMembership.Role.CEO}
PAYMENT_ROLES = {OrganizationMembership.Role.OWNER, OrganizationMembership.Role.SUPER_USER}


def _payroll_membership(request, action):
    membership = _membership(request, 'manage_payroll' if action == 'process' else 'view_payroll')
    if membership is None:
        return None
    if action == 'approve' and membership.role not in APPROVER_ROLES:
        return None
    if action == 'pay' and membership.role not in PAYMENT_ROLES:
        return None
    return membership


@require_http_methods(['POST'])
def payroll_preflight(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership(request, 'manage_payroll')
    if membership is None:
        return JsonResponse({'detail': 'Payroll management permission is required.'}, status=403)
    try:
        period = PayrollPeriod.objects.get(id=request.POST.get('period_id'), organization=membership.organization)
    except PayrollPeriod.DoesNotExist:
        return JsonResponse({'detail': 'Payroll period was not found.'}, status=404)
    return JsonResponse(PayrollConfidence.preflight(period, membership.organization))


@require_http_methods(['POST'])
def process_payroll(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _payroll_membership(request, 'process')
    if membership is None:
        return JsonResponse({'detail': 'Payroll processing permission is required.'}, status=403)
    with transaction.atomic():
        try:
            period = PayrollPeriod.objects.select_for_update().get(id=request.POST.get('period_id'), organization=membership.organization)
        except PayrollPeriod.DoesNotExist:
            return JsonResponse({'detail': 'Payroll period was not found.'}, status=404)
        if period.status != PayrollPeriod.Status.DRAFT:
            return JsonResponse({'detail': 'Only draft payroll periods can be processed.'}, status=409)
        if PayrollRecord.objects.filter(payroll_period=period).exclude(status=PayrollRecord.Status.DRAFT).exists():
            return JsonResponse({'detail': 'Payroll contains approved or paid records and cannot be recalculated.'}, status=409)
        try:
            processed = PayrollConfidence.process_period(period, membership.organization, actor=request.user)
        except ValueError as exc:
            return JsonResponse({'detail': str(exc)}, status=409)
    record_audit(organization=membership.organization, actor=request.user, action='payroll.processed', entity=period, details={'processed': processed, 'confidence': period.confidence_status, 'rule_set': period.rule_set.version if period.rule_set else None})
    return JsonResponse({'period': period.name, 'processed': processed, 'status': period.status, 'confidence': period.confidence_status})


@require_http_methods(['POST'])
def approve_payroll(request, record_id):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _payroll_membership(request, 'approve')
    if membership is None:
        return JsonResponse({'detail': 'Payroll approval authority is required.'}, status=403)
    with transaction.atomic():
        try:
            record = PayrollRecord.objects.select_for_update().select_related('payroll_period').get(id=record_id, employee__organization=membership.organization, payroll_period__organization=membership.organization)
        except PayrollRecord.DoesNotExist:
            return JsonResponse({'detail': 'Payroll record was not found.'}, status=404)
        period = PayrollPeriod.objects.select_for_update().get(pk=record.payroll_period_id)
        if period.status != PayrollPeriod.Status.CALCULATED:
            return JsonResponse({'detail': 'Payroll must be calculated before records can be approved.'}, status=409)
        if period.processed_by_id == request.user.id:
            return JsonResponse({'detail': 'Maker/checker separation: the payroll processor cannot approve the same payroll.'}, status=409)
        if record.status != PayrollRecord.Status.DRAFT:
            return JsonResponse({'detail': 'Only draft payroll records can be approved.'}, status=409)
        record.status = PayrollRecord.Status.APPROVED
        record.save(update_fields=('status', 'updated_at'))
        if not PayrollRecord.objects.filter(payroll_period=period).exclude(status=PayrollRecord.Status.APPROVED).exists():
            period.approved_by = request.user
            period.status = PayrollPeriod.Status.APPROVED
            period.save(update_fields=('approved_by', 'status', 'updated_at'))
    record_audit(organization=membership.organization, actor=request.user, action='payroll.approved', entity=record, details={'period_id': str(period.id), 'period_approved': period.status == PayrollPeriod.Status.APPROVED})
    return JsonResponse({'id': str(record.id), 'status': record.status, 'period_status': period.status, 'approved_by': request.user.get_username() if period.approved_by_id else None})


@require_http_methods(['POST'])
def mark_payroll_paid(request, record_id):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials are required.'}, status=401)
    membership = _payroll_membership(request, 'pay')
    if membership is None:
        return JsonResponse({'detail': 'Payroll payment authority is required.'}, status=403)
    with transaction.atomic():
        try:
            record = PayrollRecord.objects.select_for_update().select_related('payroll_period').get(id=record_id, employee__organization=membership.organization, payroll_period__organization=membership.organization)
        except PayrollRecord.DoesNotExist:
            return JsonResponse({'detail': 'Payroll record was not found.'}, status=404)
        period = PayrollPeriod.objects.select_for_update().get(pk=record.payroll_period_id)
        if period.approved_by_id == request.user.id or period.processed_by_id == request.user.id:
            return JsonResponse({'detail': 'Payment must be performed by a different authority from payroll processing and approval.'}, status=409)
        if record.status != PayrollRecord.Status.APPROVED:
            return JsonResponse({'detail': 'Only approved payroll records can be marked paid.'}, status=409)
        if record.loan_deductions:
            settle_loans_for_record(record)
        record.status = PayrollRecord.Status.PAID
        record.save(update_fields=('status', 'updated_at'))
        if not PayrollRecord.objects.filter(payroll_period=period).exclude(status=PayrollRecord.Status.PAID).exists():
            period.status = PayrollPeriod.Status.PAID
            period.paid_by = request.user
            period.save(update_fields=('status', 'paid_by', 'updated_at'))
    record_audit(organization=membership.organization, actor=request.user, action='payroll.paid', entity=record, details={'period_id': str(period.id), 'paid_by': request.user.get_username()})
    return JsonResponse({'id': str(record.id), 'status': record.status, 'period_status': period.status, 'paid_by': request.user.get_username() if period.paid_by_id else None})

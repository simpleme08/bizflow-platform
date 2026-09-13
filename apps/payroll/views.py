from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from apps.organization.context import current_membership
from apps.core.services import record_audit

from .completion import apply_record_adjustments, settle_loans_for_record
from .models import PayrollAdjustment, PayrollPeriod, PayrollRecord
from .services import PayrollCalculator


def _membership(request, permission=None):
    membership = current_membership(request)
    if membership is None or (permission and not membership.has_permission(permission)):
        return None
    return membership


def payroll_page(request):
    if not request.user.is_authenticated:
        return redirect('login')
    from apps.accounts.views import workspace_url_for_user
    return render(request, 'payroll/payroll.html', {'workspace_url': workspace_url_for_user(request.user)})


def payroll_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership(request, 'view_payroll')
    if membership is None:
        return JsonResponse({'detail': 'No active organization membership found.'}, status=403)
    records = PayrollRecord.objects.filter(employee__organization=membership.organization, payroll_period__organization=membership.organization).select_related('employee', 'payroll_period')
    return JsonResponse({'records': [{
        'id': str(record.id), 'employee': f'{record.employee.first_name} {record.employee.last_name}', 'employee_number': record.employee.employee_number,
        'period': record.payroll_period.name, 'basic_pay': str(record.basic_pay), 'overtime_pay': str(record.overtime_pay),
        'gross_pay': str(record.gross_pay), 'total_deductions': str(record.total_deductions), 'employer_contributions': str(record.employer_contributions), 'net_pay': str(record.net_pay), 'status': record.status,
    } for record in records]})


def my_payroll_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    try:
        employee = request.user.employee_profile
    except AttributeError:
        return JsonResponse({'detail': 'No employee profile is linked to this account.'}, status=404)
    records = employee.payroll_records.select_related('payroll_period').filter(status__in=(PayrollRecord.Status.APPROVED, PayrollRecord.Status.PAID), payroll_period__organization=employee.organization).order_by('-payroll_period__end_date', '-created_at')
    return JsonResponse({'records': [{
        'id': str(record.id), 'period': record.payroll_period.name, 'period_start': record.payroll_period.start_date.isoformat(), 'period_end': record.payroll_period.end_date.isoformat(),
        'basic_pay': str(record.basic_pay), 'overtime_pay': str(record.overtime_pay), 'gross_pay': str(record.gross_pay), 'total_deductions': str(record.total_deductions), 'net_pay': str(record.net_pay), 'status': record.status,
    } for record in records]})


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
    return JsonResponse(PayrollCalculator.preflight(period, membership.organization))


@require_http_methods(['POST'])
def process_payroll(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership(request, 'manage_payroll')
    if membership is None:
        return JsonResponse({'detail': 'Payroll management permission is required.'}, status=403)
    try:
        period = PayrollPeriod.objects.get(id=request.POST.get('period_id'), organization=membership.organization)
    except PayrollPeriod.DoesNotExist:
        return JsonResponse({'detail': 'Payroll period was not found.'}, status=404)
    if PayrollRecord.objects.filter(payroll_period=period).exclude(status=PayrollRecord.Status.DRAFT).exists():
        return JsonResponse({'detail': 'Payroll contains approved or paid records and cannot be recalculated.'}, status=409)
    try:
        processed = PayrollCalculator.process_period(period, membership.organization)
    except ValueError as exc:
        return JsonResponse({'detail': str(exc)}, status=409)
    record_audit(organization=membership.organization, actor=request.user, action='payroll.processed', entity=period, details={'processed': processed})
    return JsonResponse({'period': period.name, 'processed': processed, 'status': period.status})


@require_http_methods(['POST'])
def create_payroll_adjustment(request, record_id):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership(request, 'manage_payroll')
    if membership is None:
        return JsonResponse({'detail': 'Payroll management permission is required.'}, status=403)
    try:
        record = PayrollRecord.objects.select_related('employee', 'payroll_period').get(id=record_id, employee__organization=membership.organization, payroll_period__organization=membership.organization)
    except PayrollRecord.DoesNotExist:
        return JsonResponse({'detail': 'Payroll record was not found.'}, status=404)
    if record.status != PayrollRecord.Status.DRAFT:
        return JsonResponse({'detail': 'Only draft payroll records can receive adjustments.'}, status=409)
    try:
        adjustment = PayrollAdjustment.objects.create(
            payroll_record=record,
            kind=request.POST.get('kind', PayrollAdjustment.Kind.EARNING),
            description=request.POST.get('description', '').strip(),
            amount=Decimal(request.POST.get('amount', '0')),
            taxable=request.POST.get('taxable', 'true').lower() == 'true',
            approved=request.POST.get('approved', 'false').lower() == 'true',
        )
    except Exception as exc:
        return JsonResponse({'detail': str(exc)}, status=400)
    return JsonResponse({'id': str(adjustment.id), 'kind': adjustment.kind, 'description': adjustment.description, 'amount': str(adjustment.amount), 'approved': adjustment.approved}, status=201)


@require_http_methods(['POST'])
def apply_payroll_adjustments(request, record_id):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership(request, 'manage_payroll')
    if membership is None:
        return JsonResponse({'detail': 'Payroll management permission is required.'}, status=403)
    try:
        record = PayrollRecord.objects.select_related('employee', 'payroll_period').get(id=record_id, employee__organization=membership.organization, payroll_period__organization=membership.organization)
    except PayrollRecord.DoesNotExist:
        return JsonResponse({'detail': 'Payroll record was not found.'}, status=404)
    try:
        record = apply_record_adjustments(record)
    except (ValueError, TypeError, InvalidOperation) as exc:
        return JsonResponse({'detail': str(exc)}, status=409)
    record_audit(organization=membership.organization, actor=request.user, action='payroll.adjustments.applied', entity=record)
    return JsonResponse({'id': str(record.id), 'gross_pay': str(record.gross_pay), 'loan_deductions': str(record.loan_deductions), 'withholding_tax': str(record.withholding_tax), 'net_pay': str(record.net_pay)})


def payslip(request, record_id):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    try:
        employee = request.user.employee_profile
        record = PayrollRecord.objects.select_related('employee', 'payroll_period').get(id=record_id, employee=employee, payroll_period__organization=employee.organization, status__in=(PayrollRecord.Status.APPROVED, PayrollRecord.Status.PAID))
    except (AttributeError, PayrollRecord.DoesNotExist):
        return JsonResponse({'detail': 'Approved payslip was not found.'}, status=404)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Payslip-{record.employee.employee_number}-{record.payroll_period.name}.pdf"'
    pdf = canvas.Canvas(response, pagesize=letter)
    pdf.setTitle(f'Payslip {record.employee.employee_number}')
    pdf.drawString(72, 740, 'BizFlow HRIS Payslip')
    pdf.drawString(72, 720, f'Employee: {record.employee.first_name} {record.employee.last_name} ({record.employee.employee_number})')
    pdf.drawString(72, 700, f'Payroll period: {record.payroll_period.name}')
    lines = [
        ('Basic Pay', record.basic_pay), ('Overtime Pay', record.overtime_pay), ('Holiday Pay', record.holiday_pay), ('Night Differential', record.night_differential),
        ('Allowances', record.allowances), ('Commissions', record.commissions), ('Bonuses', record.bonuses), ('Gross Pay', record.gross_pay),
        ('SSS', record.sss_employee), ('PhilHealth', record.philhealth_employee), ('Pag-IBIG', record.pagibig_employee), ('Withholding Tax', record.withholding_tax),
        ('Late/Undertime', record.late_deduction + record.undertime_deduction), ('Leave Without Pay', record.leave_without_pay), ('Loans', record.loan_deductions), ('Other Deductions', record.other_deductions),
        ('Total Deductions', record.total_deductions), ('Net Pay', record.net_pay),
    ]
    for index, (label, amount) in enumerate(lines):
        pdf.drawString(90, 660 - index * 22, label)
        pdf.drawRightString(420, 660 - index * 22, f'PHP {amount:,.2f}')
    pdf.drawString(72, 230, f'Generated: {timezone.localtime().strftime("%B %d, %Y %I:%M %p")} PHT')
    pdf.save()
    record_audit(organization=employee.organization, actor=request.user, action='payslip.generated', entity=record)
    return response

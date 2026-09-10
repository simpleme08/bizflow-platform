from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.http import JsonResponse

from apps.organization.models import OrganizationMembership

from .models import PayrollPeriod, PayrollRecord

ZERO = Decimal('0.00')
CENT = Decimal('0.01')


def _money(value):
    return str(Decimal(value or ZERO).quantize(CENT, rounding=ROUND_HALF_UP))


def payroll_summary_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = OrganizationMembership.objects.filter(user=request.user, is_active=True, organization__is_active=True).first()
    if membership is None or not membership.has_permission('view_payroll'):
        return JsonResponse({'detail': 'Payroll viewing permission is required.'}, status=403)
    periods = PayrollPeriod.objects.filter(organization=membership.organization)
    period_id = request.GET.get('period_id')
    try:
        period = periods.get(id=period_id) if period_id else periods.order_by('-end_date', '-start_date').first()
    except PayrollPeriod.DoesNotExist:
        return JsonResponse({'detail': 'Payroll period was not found.'}, status=404)
    if period is None:
        return JsonResponse({
            'period': None, 'headcount': 0, 'gross_pay': '0.00',
            'employee_deductions': '0.00', 'net_pay': '0.00',
            'employer_contributions': '0.00', 'withholding_tax': '0.00',
            'status_counts': {},
        })

    records = PayrollRecord.objects.filter(
        payroll_period=period,
        employee__organization=membership.organization,
        payroll_period__organization=membership.organization,
    )
    aggregates = records.aggregate(
        headcount=Count('id'),
        gross_pay=Coalesce(Sum('gross_pay'), ZERO),
        net_pay=Coalesce(Sum('net_pay'), ZERO),
        withholding_tax=Coalesce(Sum('withholding_tax'), ZERO),
        sss_employee=Coalesce(Sum('sss_employee'), ZERO),
        philhealth_employee=Coalesce(Sum('philhealth_employee'), ZERO),
        pagibig_employee=Coalesce(Sum('pagibig_employee'), ZERO),
        sss_employer=Coalesce(Sum('sss_employer'), ZERO),
        philhealth_employer=Coalesce(Sum('philhealth_employer'), ZERO),
        pagibig_employer=Coalesce(Sum('pagibig_employer'), ZERO),
        late_deduction=Coalesce(Sum('late_deduction'), ZERO),
        undertime_deduction=Coalesce(Sum('undertime_deduction'), ZERO),
        leave_without_pay=Coalesce(Sum('leave_without_pay'), ZERO),
        loan_deductions=Coalesce(Sum('loan_deductions'), ZERO),
        other_deductions=Coalesce(Sum('other_deductions'), ZERO),
    )
    employee_deductions = sum(
        (aggregates[field] for field in (
            'late_deduction', 'undertime_deduction', 'leave_without_pay',
            'loan_deductions', 'sss_employee', 'philhealth_employee',
            'pagibig_employee', 'withholding_tax', 'other_deductions',
        )),
        ZERO,
    )
    employer_contributions = sum(
        (aggregates[field] for field in ('sss_employer', 'philhealth_employer', 'pagibig_employer')),
        ZERO,
    )
    status_counts = {
        status: records.filter(status=status).count()
        for status in PayrollRecord.Status.values
    }
    return JsonResponse({
        'period': {
            'id': str(period.id), 'name': period.name,
            'start_date': period.start_date.isoformat(),
            'end_date': period.end_date.isoformat(),
            'frequency': period.frequency, 'status': period.status,
        },
        'headcount': aggregates['headcount'],
        'gross_pay': _money(aggregates['gross_pay']),
        'employee_deductions': _money(employee_deductions),
        'net_pay': _money(aggregates['net_pay']),
        'employer_contributions': _money(employer_contributions),
        'withholding_tax': _money(aggregates['withholding_tax']),
        'sss_employee': _money(aggregates['sss_employee']),
        'philhealth_employee': _money(aggregates['philhealth_employee']),
        'pagibig_employee': _money(aggregates['pagibig_employee']),
        'sss_employer': _money(aggregates['sss_employer']),
        'philhealth_employer': _money(aggregates['philhealth_employer']),
        'pagibig_employer': _money(aggregates['pagibig_employer']),
        'status_counts': status_counts,
    })

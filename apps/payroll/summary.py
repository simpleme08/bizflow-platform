from decimal import Decimal

from django.http import JsonResponse

from apps.organization.models import OrganizationMembership

from .models import PayrollPeriod, PayrollRecord

ZERO = Decimal('0.00')


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
        return JsonResponse({'period': None, 'headcount': 0, 'gross_pay': '0.00', 'employee_deductions': '0.00', 'net_pay': '0.00', 'employer_contributions': '0.00', 'withholding_tax': '0.00', 'status_counts': {}})
    records = PayrollRecord.objects.filter(payroll_period=period, employee__organization=membership.organization, payroll_period__organization=membership.organization)
    def total(field):
        return sum((getattr(record, field) for record in records), ZERO)
    status_counts = {status: records.filter(status=status).count() for status in PayrollRecord.Status.values}
    return JsonResponse({
        'period': {'id': str(period.id), 'name': period.name, 'start_date': period.start_date.isoformat(), 'end_date': period.end_date.isoformat(), 'frequency': period.frequency, 'status': period.status},
        'headcount': records.count(),
        'gross_pay': str(total('gross_pay')),
        'employee_deductions': str(sum((record.total_deductions for record in records), ZERO)),
        'net_pay': str(total('net_pay')),
        'employer_contributions': str(sum((record.employer_contributions for record in records), ZERO)),
        'withholding_tax': str(total('withholding_tax')),
        'sss_employee': str(total('sss_employee')), 'philhealth_employee': str(total('philhealth_employee')), 'pagibig_employee': str(total('pagibig_employee')),
        'sss_employer': str(total('sss_employer')), 'philhealth_employer': str(total('philhealth_employer')), 'pagibig_employer': str(total('pagibig_employer')),
        'status_counts': status_counts,
    })

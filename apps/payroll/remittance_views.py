import csv
from calendar import monthrange
from datetime import date
from io import StringIO

from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET

from .models import PayrollPeriod, PayrollRecord
from .services import PayrollCalculator, PhilippinePayrollRules
from .views import _membership


EXPORT_TYPES = {'sss', 'philhealth', 'pagibig', 'bir-1601c'}


def _csv_response(filename, headers, rows):
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(rows)
    response = HttpResponse(buffer.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _period_records(period):
    return PayrollRecord.objects.filter(
        payroll_period=period,
        employee__organization=period.organization,
    ).select_related('employee', 'employee__payroll_profile')


def _employee_name(employee):
    return f'{employee.last_name}, {employee.first_name}'.strip(', ')


@require_GET
def payroll_remittance_export(request, period_id, export_type):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership(request, 'manage_payroll')
    if membership is None:
        return JsonResponse({'detail': 'Payroll management permission is required.'}, status=403)
    if export_type not in EXPORT_TYPES:
        return JsonResponse({'detail': 'Unsupported remittance export type.'}, status=404)
    try:
        period = PayrollPeriod.objects.get(id=period_id, organization=membership.organization)
    except PayrollPeriod.DoesNotExist:
        return JsonResponse({'detail': 'Payroll period not found.'}, status=404)

    records = list(_period_records(period))
    if export_type == 'sss':
        rows = []
        for record in records:
            profile = getattr(record.employee, 'payroll_profile', None)
            rows.append([
                getattr(profile, 'sss_number', '') if profile else '',
                record.employee.employee_number,
                _employee_name(record.employee),
                period.start_date.isoformat(),
                period.end_date.isoformat(),
                f'{record.sss_employee:.2f}',
                f'{record.sss_employer:.2f}',
                f'{(record.sss_employee + record.sss_employer):.2f}',
            ])
        return _csv_response(
            f'sss-remittance-{period.end_date:%Y-%m}.csv',
            ['SSS Number', 'Employee Number', 'Employee Name', 'Period Start', 'Period End', 'EE Share', 'ER Share', 'Total'],
            rows,
        )

    if export_type == 'philhealth':
        rows = []
        for record in records:
            profile = getattr(record.employee, 'payroll_profile', None)
            rows.append([
                getattr(profile, 'philhealth_number', '') if profile else '',
                record.employee.employee_number,
                _employee_name(record.employee),
                period.start_date.strftime('%Y%m'),
                f'{record.philhealth_employee:.2f}',
                f'{record.philhealth_employer:.2f}',
                f'{(record.philhealth_employee + record.philhealth_employer):.2f}',
            ])
        return _csv_response(
            f'philhealth-remittance-{period.end_date:%Y-%m}.csv',
            ['PhilHealth Number', 'Employee Number', 'Employee Name', 'Period Covered', 'EE Share', 'ER Share', 'Total'],
            rows,
        )

    if export_type == 'pagibig':
        rows = []
        for record in records:
            profile = getattr(record.employee, 'payroll_profile', None)
            rows.append([
                getattr(profile, 'pagibig_number', '') if profile else '',
                record.employee.employee_number,
                _employee_name(record.employee),
                period.end_date.strftime('%Y%m'),
                f'{record.pagibig_employee:.2f}',
                f'{record.pagibig_employer:.2f}',
                '',
            ])
        return _csv_response(
            f'pagibig-remittance-{period.end_date:%Y-%m}.csv',
            ['Pag-IBIG ID/RTN', 'Employee Number', 'Employee Name', 'Percov', 'EE Share', 'ER Share', 'Remarks'],
            rows,
        )

    # BIR 1601-C is an aggregate calculation sheet, not a claimed eFPS upload layout.
    period_month_start = period.start_date.replace(day=1)
    period_month_end = period.end_date
    if period_month_end.month != period_month_start.month or period_month_end.year != period_month_start.year:
        period_month_end = date(period_month_start.year, period_month_start.month, monthrange(period_month_start.year, period_month_start.month)[1])

    total_compensation = sum((r.gross_pay for r in records), 0)
    total_statutory = sum((r.statutory_deductions for r in records), 0)
    total_tax = sum((r.withholding_tax for r in records), 0)
    total_thirteenth = sum((r.thirteenth_month for r in records), 0)
    exempt_thirteenth = min(total_thirteenth, PhilippinePayrollRules.THIRTEENTH_MONTH_EXEMPTION)

    mwe_basic = 0
    mwe_ot_holiday_nd = 0
    for record in records:
        profile = getattr(record.employee, 'payroll_profile', None)
        if not profile or not profile.minimum_wage_earner:
            continue
        wage_rate = PayrollCalculator._wage_rate_for_employee(record.employee, period)
        salary = PayrollCalculator._salary_for_period(record.employee, period)
        if wage_rate is None or salary is None:
            continue
        daily_rate = salary.basic_salary / PayrollCalculator.WORKING_DAYS
        if daily_rate <= wage_rate.daily_rate:
            periods = PayrollCalculator.periods_per_month(period)
            qualifying_regular = min(record.basic_pay, PhilippinePayrollRules.money(wage_rate.daily_rate * PayrollCalculator.WORKING_DAYS / periods))
            mwe_basic += qualifying_regular
            mwe_ot_holiday_nd += record.overtime_pay + record.holiday_pay + record.night_differential

    # taxable_supplementary is taxable by definition, so it must never be reported
    # as "other non-taxable compensation".
    other_non_taxable = 0
    total_non_taxable = mwe_basic + mwe_ot_holiday_nd + exempt_thirteenth + total_statutory + other_non_taxable
    taxable_compensation = max(0, total_compensation - total_non_taxable)
    rows = [[
        period_month_start.strftime('%m/%Y'),
        f'{total_compensation:.2f}',
        f'{mwe_basic:.2f}',
        f'{mwe_ot_holiday_nd:.2f}',
        f'{total_thirteenth:.2f}',
        '0.00',
        f'{total_statutory:.2f}',
        f'{other_non_taxable:.2f}',
        f'{total_non_taxable:.2f}',
        f'{taxable_compensation:.2f}',
        f'{total_tax:.2f}',
        '0.00',
        f'{total_tax:.2f}',
        '',
    ]]
    return _csv_response(
        f'bir-1601c-{period_month_start:%Y-%m}.csv',
        ['For the Month', 'Total Compensation', 'MWE Statutory Minimum Wage', 'MWE Holiday/OT/NSD', '13th Month and Other Benefits', 'De Minimis Benefits', 'Employee Statutory Contributions', 'Other Non-Taxable Compensation', 'Total Non-Taxable Compensation', 'Net/Taxable Compensation Basis', 'Total Taxes Withheld', 'Prior-Period Adjustment', 'Tax Required for Remittance', 'Notes'],
        rows,
    )

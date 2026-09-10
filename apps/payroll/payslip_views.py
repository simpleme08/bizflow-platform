from datetime import timedelta
from decimal import Decimal

from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from apps.attendance.models import AttendanceRecord
from apps.core.services import record_audit
from .models import PayrollAdjustment, PayrollRecord


def _money(value):
    return f'PHP {Decimal(value or 0):,.2f}'


def _section(pdf, x, y, width, title):
    pdf.setFont('Helvetica-Bold', 9)
    pdf.drawString(x, y, title)
    pdf.line(x, y - 3, x + width, y - 3)


def _label_value(pdf, x, y, label, value, value_x):
    pdf.setFont('Helvetica-Bold', 8.5)
    pdf.drawString(x, y, label)
    pdf.setFont('Helvetica', 8.5)
    pdf.drawString(value_x, y, str(value))


def _amount_column(pdf, x, y, width, title, rows):
    pdf.setFont('Helvetica-Bold', 8.5)
    pdf.drawString(x, y, title.upper())
    y -= 16
    for label, amount in rows:
        pdf.setFont('Helvetica', 8.5)
        pdf.drawString(x, y, label)
        pdf.drawRightString(x + width, y, _money(amount))
        y -= 15
    return y


def payslip(request, record_id):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    try:
        employee = request.user.employee_profile
        record = PayrollRecord.objects.select_related(
            'employee', 'employee__position', 'employee__employment_type', 'employee__department',
            'payroll_period', 'payroll_period__organization',
        ).get(
            id=record_id,
            employee=employee,
            payroll_period__organization=employee.organization,
            status__in=(PayrollRecord.Status.APPROVED, PayrollRecord.Status.PAID),
        )
    except (AttributeError, PayrollRecord.DoesNotExist):
        return JsonResponse({'detail': 'Approved payslip was not found.'}, status=404)

    attendance = AttendanceRecord.objects.filter(
        employee=employee,
        attendance_date__range=(record.payroll_period.start_date, record.payroll_period.end_date),
    )
    total_hours = Decimal('0.00')
    overtime_hours = Decimal('0.00')
    night_hours = Decimal('0.00')
    days_worked = 0
    for item in attendance:
        if not (item.time_in and item.time_out):
            continue
        hours = Decimal(str((item.time_out - item.time_in).total_seconds() / 3600)).quantize(Decimal('0.01'))
        total_hours += max(hours, Decimal('0'))
        days_worked += 1
        overtime_hours += Decimal(item.overtime_minutes) / Decimal('60')
        cursor = timezone.localtime(item.time_in)
        end = timezone.localtime(item.time_out)
        while cursor < end:
            if cursor.hour >= 22 or cursor.hour < 6:
                night_hours += Decimal('1') / Decimal('60')
            cursor += timedelta(minutes=1)
    total_hours = total_hours.quantize(Decimal('0.01'))
    overtime_hours = overtime_hours.quantize(Decimal('0.01'))
    night_hours = night_hours.quantize(Decimal('0.01'))
    regular_hours = max(total_hours - overtime_hours, Decimal('0')).quantize(Decimal('0.01'))

    adjustments = list(record.adjustments.filter(approved=True))
    adjustment_earnings = sum((a.amount for a in adjustments if a.kind == PayrollAdjustment.Kind.EARNING), Decimal('0'))
    adjustment_deductions = sum((a.amount for a in adjustments if a.kind == PayrollAdjustment.Kind.DEDUCTION), Decimal('0'))

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Payslip-{employee.employee_number}-{record.payroll_period.name}.pdf"'
    pdf = canvas.Canvas(response, pagesize=A4)
    pdf.setTitle(f'Payslip {employee.employee_number}')
    page_width, page_height = A4
    left, right = 42, page_width - 42
    width = right - left
    y = page_height - 42

    pdf.setFont('Helvetica-Bold', 14)
    pdf.drawCentredString(page_width / 2, y, employee.organization.name.upper())
    y -= 16
    pdf.setFont('Helvetica', 8)
    pdf.drawCentredString(page_width / 2, y, 'PAYSLIP')
    y -= 12
    pdf.line(left, y, right, y)
    y -= 18

    mid = left + width / 2 + 10
    _label_value(pdf, left, y, 'EMPLOYEE NAME:', f'{employee.last_name}, {employee.first_name}', left + 80)
    _label_value(pdf, mid, y, 'PAY PERIOD:', record.payroll_period.name, mid + 62)
    y -= 15
    _label_value(pdf, left, y, 'EMPLOYEE CODE:', employee.employee_number, left + 80)
    _label_value(pdf, mid, y, 'POSITION:', getattr(employee.position, 'title', '') or '—', mid + 62)
    y -= 15
    salary = getattr(getattr(employee, 'salary', None), 'basic_salary', Decimal('0'))
    _label_value(pdf, left, y, 'MONTHLY SALARY:', _money(salary), left + 80)
    pay_date = record.updated_at.astimezone(timezone.get_current_timezone()).strftime('%B %d, %Y') if record.updated_at else '—'
    _label_value(pdf, mid, y, 'PAY DATE:', pay_date, mid + 62)
    y -= 15
    _label_value(pdf, left, y, 'STATUS:', getattr(employee.employment_type, 'name', '') or '—', left + 80)
    _label_value(pdf, mid, y, 'DEPARTMENT:', getattr(employee.department, 'name', '') or '—', mid + 62)
    y -= 22

    column_gap = 22
    column_width = (width - column_gap) / 2
    earnings = [
        ('Basic Salary', record.basic_pay),
        ('Overtime Pay', record.overtime_pay),
        ('Holiday Pay', record.holiday_pay),
        ('Night Shift Differential', record.night_differential),
        ('De Minimis Benefits', Decimal('0')),
        ('Non-taxable Allowances', record.allowances),
        ('Reimbursements', Decimal('0')),
        ('Adjustments (+)', adjustment_earnings),
    ]
    deductions = [
        ('SSS', record.sss_employee),
        ('HDMF / Pag-IBIG', record.pagibig_employee),
        ('PhilHealth', record.philhealth_employee),
        ('Withholding Tax', record.withholding_tax),
        ('Government Loans', Decimal('0')),
        ('HMO', Decimal('0')),
        ('Company Loans', record.loan_deductions),
        ('Other Deductions', record.other_deductions + record.late_deduction + record.undertime_deduction + record.leave_without_pay + adjustment_deductions),
    ]
    left_end = _amount_column(pdf, left, y, column_width, 'Earnings', earnings)
    right_end = _amount_column(pdf, left + column_width + column_gap, y, column_width, 'Deductions', deductions)
    y = min(left_end, right_end) - 5
    pdf.setFont('Helvetica-Bold', 8.5)
    pdf.drawString(left, y, 'TOTAL EARNINGS:')
    pdf.drawRightString(left + column_width, y, _money(record.gross_pay + adjustment_earnings))
    pdf.drawString(left + column_width + column_gap, y, 'TOTAL DEDUCTIONS:')
    pdf.drawRightString(right, y, _money(record.total_deductions + adjustment_deductions))
    y -= 24
    pdf.setFont('Helvetica-Bold', 12)
    pdf.drawString(left, y, 'NET PAY:')
    pdf.drawRightString(right, y, _money(record.net_pay))
    y -= 25

    _section(pdf, left, y, width, 'WORK DETAILS')
    y -= 18
    _label_value(pdf, left, y, 'TOTAL DAYS WORKED:', days_worked, left + 105)
    _label_value(pdf, left + 225, y, 'DAY SHIFT:', total_hours, left + 285)
    y -= 15
    _label_value(pdf, left, y, 'TOTAL HOURS WORKED:', f'{total_hours:.2f}', left + 105)
    _label_value(pdf, left + 225, y, 'NIGHT SHIFT:', f'{night_hours:.2f}', left + 285)
    y -= 15
    _label_value(pdf, left, y, 'TOTAL REGULAR HOURS:', f'{regular_hours:.2f}', left + 105)
    _label_value(pdf, left + 225, y, 'REST DAY & OVERTIME:', f'{overtime_hours:.2f}', left + 330)
    y -= 25

    _section(pdf, left, y, width, 'PAYMENT DETAILS')
    y -= 18
    _label_value(pdf, left, y, 'MODE OF PAYMENT:', 'Configured payroll method', left + 105)
    y -= 15
    _label_value(pdf, left, y, 'BANK ACCOUNT:', 'Not configured', left + 105)
    y -= 25

    _section(pdf, left, y, width, 'DISCLAIMER')
    y -= 16
    disclaimer = ('Please review your earnings and deductions promptly after receipt. If you identify an error, '
                  'contact Payroll immediately so corrections can be reviewed and processed. This payslip contains '
                  'confidential payroll information intended solely for the employee and authorized company personnel.')
    pdf.setFont('Helvetica', 7.5)
    current = ''
    for word in disclaimer.split():
        candidate = f'{current} {word}'.strip()
        if stringWidth(candidate, 'Helvetica', 7.5) > width:
            pdf.drawString(left, y, current)
            y -= 10
            current = word
        else:
            current = candidate
    if current:
        pdf.drawString(left, y, current)
        y -= 10
    y -= 8

    _section(pdf, left, y, width, "EMPLOYER'S CERTIFICATION")
    y -= 18
    pdf.setFont('Helvetica', 7.5)
    certification = 'I certify that the above payment has been processed correctly in accordance with company policies and applicable labor regulations.'
    pdf.drawString(left, y, certification)
    y -= 28
    pdf.setFont('Helvetica-Bold', 8)
    pdf.drawString(left, y, 'APPROVED BY:')
    pdf.drawString(left + 260, y, 'EMPLOYEE SIGNATURE:')
    y -= 18
    pdf.line(left, y, left + 180, y)
    pdf.line(left + 260, y, right, y)
    y -= 12
    pdf.setFont('Helvetica', 7)
    pdf.drawString(left, y, 'Authorized Payroll / HR')
    pdf.drawString(left + 260, y, f'{employee.last_name}, {employee.first_name}')

    pdf.setFont('Helvetica', 6.5)
    pdf.drawCentredString(page_width / 2, 20, f'Generated {timezone.localtime().strftime("%B %d, %Y %I:%M %p")} PHT')
    pdf.save()
    record_audit(organization=employee.organization, actor=request.user, action='payslip.generated', entity=record)
    return response

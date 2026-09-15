from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from apps.core.services import record_audit

from .completion import loan_deduction_for_record
from .loan_models import EmployeeLoan
from .models import PayrollRecord
from .views import _membership


@require_http_methods(['GET', 'POST'])
def loans_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership(request, 'manage_payroll')
    if membership is None:
        return JsonResponse({'detail': 'Payroll management permission is required.'}, status=403)
    if request.method == 'GET':
        loans = EmployeeLoan.objects.filter(employee__organization=membership.organization).select_related('employee')
        return JsonResponse({'loans': [{
            'id': str(loan.id), 'employee_id': str(loan.employee_id), 'employee': f'{loan.employee.first_name} {loan.employee.last_name}',
            'lender': loan.lender, 'loan_type': loan.loan_type, 'reference_number': loan.reference_number,
            'principal': str(loan.principal), 'interest': str(loan.interest), 'installment_amount': str(loan.installment_amount),
            'start_date': loan.start_date.isoformat(), 'end_date': loan.end_date.isoformat(), 'balance': str(loan.balance), 'status': loan.status,
        } for loan in loans]})

    try:
        from apps.employees.models import Employee

        employee = Employee.objects.get(
            id=request.POST.get('employee_id'),
            organization=membership.organization,
        )
        principal = Decimal(request.POST.get('principal', '0'))
        interest = Decimal(request.POST.get('interest', '0'))
        installment = Decimal(request.POST.get('installment_amount', '0'))
        loan = EmployeeLoan(
            employee=employee,
            lender=request.POST.get('lender', '').strip(),
            loan_type=request.POST.get('loan_type', '').strip(),
            reference_number=request.POST.get('reference_number', '').strip(),
            principal=principal,
            interest=interest,
            installment_amount=installment,
            start_date=request.POST.get('start_date'),
            end_date=request.POST.get('end_date'),
            balance=principal + interest,
        )
        loan.full_clean()
        loan.save(force_insert=True)
    except Employee.DoesNotExist:
        return JsonResponse({'detail': 'Employee was not found.'}, status=404)
    except (ValidationError, InvalidOperation, TypeError, ValueError):
        return JsonResponse({'detail': 'Invalid loan data.'}, status=400)

    record_audit(organization=membership.organization, actor=request.user, action='payroll.loan.created', entity=loan)
    return JsonResponse({'id': str(loan.id), 'balance': str(loan.balance), 'status': loan.status}, status=201)


@require_http_methods(['GET'])
def payroll_loan_preview(request, record_id):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership(request, 'view_payroll')
    if membership is None:
        return JsonResponse({'detail': 'Payroll access is required.'}, status=403)
    try:
        record = PayrollRecord.objects.get(id=record_id, employee__organization=membership.organization, payroll_period__organization=membership.organization)
    except PayrollRecord.DoesNotExist:
        return JsonResponse({'detail': 'Payroll record was not found.'}, status=404)
    return JsonResponse({'scheduled_loan_deduction': str(loan_deduction_for_record(record))})

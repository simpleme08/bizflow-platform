from datetime import date
from decimal import Decimal, InvalidOperation

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .completion import final_pay_preview
from .loan_models import EmployeeLoan
from .views import _membership


@require_http_methods(['POST'])
def final_pay_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership(request, 'manage_payroll')
    if membership is None:
        return JsonResponse({'detail': 'Payroll management permission is required.'}, status=403)
    from apps.employees.models import Employee
    try:
        employee = Employee.objects.get(id=request.POST.get('employee_id'), organization=membership.organization)
        salary = employee.salary.basic_salary
        separation_date = date.fromisoformat(request.POST.get('separation_date', ''))
        worked_days = Decimal(request.POST.get('worked_days', ''))
        if worked_days != worked_days.to_integral_value():
            raise ValueError('Worked days must be a whole number.')
        loan_balance = sum((loan.balance for loan in EmployeeLoan.objects.filter(employee=employee, status=EmployeeLoan.Status.ACTIVE)), Decimal('0.00'))
        result = final_pay_preview(
            employee,
            separation_date,
            salary,
            worked_days=worked_days,
            thirteenth_month=Decimal(request.POST.get('thirteenth_month', '0')),
            accrued_leave_pay=Decimal(request.POST.get('accrued_leave_pay', '0')),
            other_earnings=Decimal(request.POST.get('other_earnings', '0')),
            other_deductions=Decimal(request.POST.get('other_deductions', '0')),
            loan_balance=loan_balance,
        )
    except (Employee.DoesNotExist, ValueError, InvalidOperation, TypeError) as exc:
        return JsonResponse({'detail': str(exc)}, status=400)
    return JsonResponse({key: str(value) if isinstance(value, Decimal) else value for key, value in result.items()})

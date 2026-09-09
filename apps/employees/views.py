from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.organization.models import OrganizationMembership

from .models import Employee


def _membership_for(user):
	return OrganizationMembership.objects.filter(
		user=user,
		is_active=True,
		organization__is_active=True,
	).select_related('organization').first()


def employee_directory(request):
	if not request.user.is_authenticated:
		return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)

	membership = _membership_for(request.user)
	if membership is None or not membership.has_permission('view_employees'):
		return JsonResponse({'detail': 'No active organization membership found.'}, status=403)

	employees = Employee.objects.filter(
		organization=membership.organization,
		is_active=True,
	).select_related('department', 'position', 'employment_type').prefetch_related('assignments__shift_template', 'assignments__client')
	return JsonResponse({
		'employees': [
			{
				'id': str(employee.id),
				'employee_number': employee.employee_number,
				'name': f'{employee.first_name} {employee.last_name}',
				'department': employee.department.name if employee.department else None,
				'position': employee.position.title if employee.position else None,
				'employment_type': employee.employment_type.name if employee.employment_type else None,
				'assignments': [
					{
						'shift': assignment.shift_template.name,
						'client': assignment.client.name if assignment.client else None,
						'site': assignment.client_site.name if assignment.client_site else None,
						'start_date': assignment.start_date.isoformat(),
						'end_date': assignment.end_date.isoformat() if assignment.end_date else None,
						'is_primary': assignment.is_primary,
					}
					for assignment in employee.assignments.all()
				],
			}
			for employee in employees
		],
	})


def employee_directory_page(request):
	if not request.user.is_authenticated:
		return redirect('login')
	from apps.accounts.views import workspace_url_for_user
	return render(request, 'employees/directory.html', {'workspace_url': workspace_url_for_user(request.user)})

from django.http import JsonResponse

from .models import OrganizationMembership


def current_user(request):
	if not request.user.is_authenticated:
		return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)

	membership = OrganizationMembership.objects.filter(
		user=request.user,
		is_active=True,
		organization__is_active=True,
	).select_related('organization').first()
	if membership is None:
		return JsonResponse({'detail': 'No active organization membership found.'}, status=403)

	return JsonResponse({
		'username': request.user.get_username(),
		'is_superuser': request.user.is_superuser,
		'is_maintenance_user': request.user.is_superuser or membership.role == OrganizationMembership.Role.SUPER_USER,
		'organization': {
			'id': str(membership.organization_id),
			'name': membership.organization.name,
			'slug': membership.organization.slug,
		},
		'role': membership.role,
		'role_label': membership.get_role_display(),
		'permissions': sorted(membership.ROLE_PERMISSIONS.get(membership.role, set())),
	})

# Create your views here.

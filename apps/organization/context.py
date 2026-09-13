from .models import OrganizationMembership


ACTIVE_ORGANIZATION_SESSION_KEY = 'active_organization_id'
ACTIVE_ORGANIZATION_HEADER = 'HTTP_X_ORGANIZATION_ID'


def current_membership(request):
    """Return the explicitly selected organization membership, or a sole membership.

    Multi-organization users must explicitly select a tenant through the session or
    X-Organization-ID header. Never silently choose an arbitrary membership.
    """
    if not request.user.is_authenticated:
        return None

    memberships = OrganizationMembership.objects.filter(
        user=request.user,
        is_active=True,
        organization__is_active=True,
    ).select_related('organization')

    selected_id = request.session.get(ACTIVE_ORGANIZATION_SESSION_KEY)
    if not selected_id:
        selected_id = request.META.get(ACTIVE_ORGANIZATION_HEADER)
    if selected_id:
        return memberships.filter(organization_id=selected_id).first()

    if memberships.count() == 1:
        return memberships.first()
    return None

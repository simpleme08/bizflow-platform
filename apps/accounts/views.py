from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from apps.organization.context import ACTIVE_ORGANIZATION_SESSION_KEY, current_membership


def login_page(request):
    if request.user.is_authenticated:
        return redirect_for_user(request)
    next_url = request.GET.get('next') or request.POST.get('next')
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('username', ''), password=request.POST.get('password', ''))
        if user is not None and user.is_active:
            memberships = user.organization_memberships.filter(is_active=True, organization__is_active=True).select_related('organization').order_by('organization__name')
            selected_id = request.POST.get('organization_id', '').strip()
            if not memberships.exists():
                return render(request, 'registration/login.html', {'error': 'No active organization membership found.', 'next': next_url}, status=401)
            if memberships.count() > 1 and not selected_id:
                login(request, user)
                request.session.pop(ACTIVE_ORGANIZATION_SESSION_KEY, None)
                return render(request, 'registration/login.html', {'error': 'Select the organization you want to access.', 'next': next_url, 'organizations': memberships, 'organization_selection': True, 'username': request.POST.get('username', '').strip()}, status=200)
            membership = memberships.filter(organization_id=selected_id).first() if selected_id else memberships.first()
            if membership is not None:
                login(request, user)
                request.session[ACTIVE_ORGANIZATION_SESSION_KEY] = str(membership.organization_id)
                if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                    return redirect(next_url)
                return redirect_for_user(request)
        return render(request, 'registration/login.html', {'error': 'Invalid username or password.', 'next': next_url}, status=401)
    return render(request, 'registration/login.html', {'next': next_url})


def _user_from_request_or_user(request_or_user):
    return request_or_user.user if hasattr(request_or_user, 'user') else request_or_user


def workspace_url_for_user(request_or_user):
    """Return a workspace URL without ever guessing a tenant for multi-org users."""
    user = _user_from_request_or_user(request_or_user)
    if user.is_anonymous:
        return '/login/'
    if user.is_superuser:
        return '/workspace/'
    if hasattr(request_or_user, 'user'):
        membership = current_membership(request_or_user)
    else:
        memberships = user.organization_memberships.filter(is_active=True, organization__is_active=True)
        membership = memberships.first() if memberships.count() == 1 else None
    if membership is None:
        return '/login/'
    if membership.role == membership.Role.EMPLOYEE:
        return '/ess/'
    return '/workspace/'


def redirect_for_user(request):
    return redirect(workspace_url_for_user(request))


def employee_login(request):
    return redirect('login')
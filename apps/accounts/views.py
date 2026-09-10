from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme


def login_page(request):
    if request.user.is_authenticated:
        return redirect_for_user(request.user)
    next_url = request.GET.get('next') or request.POST.get('next')
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('username', '').strip(), password=request.POST.get('password', ''))
        if user is not None and user.is_active:
            membership = user.organization_memberships.filter(is_active=True, organization__is_active=True).first()
            if membership is not None:
                login(request, user)
                if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}, require_https=request.is_secure()):
                    return redirect(next_url)
                return redirect_for_user(user)
        return render(request, 'registration/login.html', {'error': 'Your account is inactive or has no active organization access.', 'next': next_url}, status=401)
    return render(request, 'registration/login.html', {'next': next_url})


def workspace_url_for_user(user):
    if user.is_anonymous:
        return '/login/'
    if user.is_superuser:
        return '/workspace/'
    membership = user.organization_memberships.filter(is_active=True, organization__is_active=True).first()
    if membership is None:
        return '/login/'
    if membership.role == membership.Role.EMPLOYEE:
        return '/ess/'
    return '/workspace/'


def redirect_for_user(user):
    return redirect(workspace_url_for_user(user))


def employee_login(request):
    return redirect('login')

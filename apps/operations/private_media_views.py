import mimetypes

from django.http import FileResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.organization.models import OrganizationMembership

from .models import EmployeeDocument


@require_GET
def employee_document_file(request, document_id):
    """Serve an employee document only after tenant and publication checks."""
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)

    membership = (
        OrganizationMembership.objects
        .filter(user=request.user, is_active=True, organization__is_active=True)
        .select_related('organization')
        .first()
    )
    if membership is None:
        return JsonResponse({'detail': 'No active organization membership found.'}, status=403)

    document = (
        EmployeeDocument.objects
        .filter(id=document_id, organization=membership.organization, status=EmployeeDocument.Status.PUBLISHED)
        .first()
    )
    if document is None:
        return JsonResponse({'detail': 'Document was not found in your organization.'}, status=404)

    if document.expires_on and document.expires_on < timezone.localdate():
        return JsonResponse({'detail': 'This document is no longer available.'}, status=404)

    if not document.file:
        return JsonResponse({'detail': 'This document has no attached file.'}, status=404)

    try:
        file_handle = document.file.open('rb')
    except (FileNotFoundError, OSError):
        return JsonResponse({'detail': 'Document file is unavailable.'}, status=404)

    content_type, _ = mimetypes.guess_type(document.file.name)
    response = FileResponse(file_handle, content_type=content_type or 'application/octet-stream')
    response['Content-Disposition'] = 'inline'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    return response

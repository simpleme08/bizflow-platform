import mimetypes

from django.http import FileResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.core.services import record_audit
from apps.organization.context import current_membership

from .models import EmployeeDocument


@require_GET
def employee_document_file(request, document_id):
    """Serve a published organization policy file to an active employee.

    Legacy file_url values are intentionally not redirected or returned. They
    must be re-uploaded into the private storage backend before employees can
    download them through this endpoint.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)

    membership = current_membership(request)
    if membership is None:
        return JsonResponse({'detail': 'No active organization membership found.'}, status=403)

    try:
        employee = request.user.employee_profile
    except AttributeError:
        return JsonResponse({'detail': 'An employee profile is required to access policy documents.'}, status=403)

    if employee.organization_id != membership.organization_id or not employee.organization.is_active:
        return JsonResponse({'detail': 'Employee organization access is not available.'}, status=403)

    document = EmployeeDocument.objects.filter(
        id=document_id,
        organization=membership.organization,
        status=EmployeeDocument.Status.PUBLISHED,
    ).first()
    if document is None:
        return JsonResponse({'detail': 'Document was not found in your organization.'}, status=404)
    if document.expires_on and document.expires_on < timezone.localdate():
        return JsonResponse({'detail': 'This document is no longer available.'}, status=404)
    if not document.file:
        return JsonResponse({'detail': 'This attachment must be re-uploaded by HR before it can be downloaded.'}, status=404)

    try:
        file_handle = document.file.open('rb')
    except (FileNotFoundError, OSError):
        return JsonResponse({'detail': 'Document file is unavailable.'}, status=404)

    content_type, _ = mimetypes.guess_type(document.file.name)
    response = FileResponse(
        file_handle,
        as_attachment=True,
        filename=document.file.name.rsplit('/', 1)[-1],
        content_type=content_type or 'application/octet-stream',
    )
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    record_audit(
        organization=membership.organization,
        actor=request.user,
        action='policy_document.downloaded',
        entity=document,
        details={'category': document.category},
    )
    return response

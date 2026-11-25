from django.http import FileResponse, JsonResponse
from django.views.decorators.http import require_GET

from apps.core.services import record_audit
from apps.organization.context import current_membership

from .models import EmployeeDocument


@require_GET
def employee_document_file(request, employee_id, document_id):
    """Stream an employee's private document after tenant and role authorization.

    Do not return FileField.url: private object-storage URLs are short-lived
    bearer credentials and should only be issued after checking access.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)

    membership = current_membership(request)
    if membership is None:
        return JsonResponse({'detail': 'No active organization membership found.'}, status=403)

    document = (
        EmployeeDocument.objects
        .select_related('employee__organization', 'employee__user')
        .filter(
            id=document_id,
            employee_id=employee_id,
            employee__organization=membership.organization,
            status='ACTIVE',
        )
        .first()
    )
    if document is None:
        return JsonResponse({'detail': 'Employee document was not found.'}, status=404)

    is_owner = document.employee.user_id == request.user.id
    if not (is_owner or membership.has_permission('manage_employees')):
        return JsonResponse({'detail': 'You do not have permission to access this employee document.'}, status=403)

    if not document.file:
        return JsonResponse({'detail': 'Document file is unavailable.'}, status=404)

    try:
        file_handle = document.file.open('rb')
    except (FileNotFoundError, OSError):
        return JsonResponse({'detail': 'Document file is unavailable.'}, status=404)

    record_audit(
        organization=membership.organization,
        actor=request.user,
        action='employee_document.downloaded',
        entity=document,
        details={'employee_id': str(document.employee_id), 'document_type': document.document_type},
    )
    response = FileResponse(
        file_handle,
        as_attachment=True,
        filename=document.file.name.rsplit('/', 1)[-1],
        content_type='application/octet-stream',
    )
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    return response

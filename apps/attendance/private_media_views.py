import mimetypes

from django.http import FileResponse, JsonResponse
from django.views.decorators.http import require_GET

from apps.organization.context import current_membership

from .models import AttendanceRecord


@require_GET
def attendance_proof(request, record_id, proof_type):
    """Serve attendance proof only to the employee or an authorized org member.

    Attendance photos are sensitive employment records. Do not expose their
    FileField URL directly to clients; this endpoint enforces tenant and role
    checks before opening the stored object.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)

    membership = current_membership(request)
    if membership is None:
        return JsonResponse({'detail': 'No active organization membership found.'}, status=403)

    record = (
        AttendanceRecord.objects
        .select_related('employee__organization')
        .filter(id=record_id, employee__organization=membership.organization)
        .first()
    )
    if record is None:
        return JsonResponse({'detail': 'Attendance record was not found in your organization.'}, status=404)

    is_owner = record.employee.user_id == request.user.id
    can_manage = request.user.is_superuser or membership.has_permission('view_attendance')
    if not (is_owner or can_manage):
        return JsonResponse({'detail': 'You do not have access to this attendance proof.'}, status=403)

    field_name = {'clock_in': 'clock_in_photo', 'clock_out': 'clock_out_photo'}.get(proof_type)
    if field_name is None:
        return JsonResponse({'detail': 'Proof type must be clock_in or clock_out.'}, status=400)

    proof = getattr(record, field_name)
    if not proof:
        return JsonResponse({'detail': 'Attendance proof is not available.'}, status=404)

    try:
        file_handle = proof.open('rb')
    except (FileNotFoundError, OSError):
        return JsonResponse({'detail': 'Attendance proof is unavailable.'}, status=404)

    content_type, _ = mimetypes.guess_type(proof.name)
    response = FileResponse(file_handle, content_type=content_type or 'application/octet-stream')
    response['Content-Disposition'] = 'inline'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    return response

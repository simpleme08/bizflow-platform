from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Q

from apps.core.services import record_audit
from apps.employees.models import Employee
from apps.organization.models import OrganizationMembership
from apps.workforce.models import ShiftTemplate

from .models import AttendanceRecord
from .views import _clock_state, _validate_clock_photo


@require_http_methods(['GET', 'POST'])
def clock_cover_action(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Sign in before selecting a cover shift.'}, status=401)
    try:
        employee = request.user.employee_profile
    except Employee.DoesNotExist:
        return JsonResponse({'detail': 'This account is not linked to an employee profile.'}, status=403)
    membership = OrganizationMembership.objects.filter(
        user=request.user, is_active=True, organization=employee.organization, organization__is_active=True
    ).first()
    if membership is None:
        return JsonResponse({'detail': 'This employee does not have active organization access.'}, status=403)
    if not employee.is_active:
        return JsonResponse({'detail': 'This employee profile is inactive.'}, status=403)

    today = timezone.localdate()
    shifts = ShiftTemplate.objects.all().order_by('name')
    payload = _clock_state(employee)
    payload['cover_shifts'] = [
        {'id': str(shift.id), 'name': shift.name, 'start_time': shift.start_time.strftime('%H:%M'), 'end_time': shift.end_time.strftime('%H:%M')}
        for shift in shifts
    ]
    if request.method == 'GET':
        return JsonResponse(payload)

    shift_id = request.POST.get('shift_id')
    if not shift_id:
        return JsonResponse({'detail': 'Select the shift you are covering.'}, status=400)
    try:
        shift = ShiftTemplate.objects.get(id=shift_id)
    except ShiftTemplate.DoesNotExist:
        return JsonResponse({'detail': 'The selected cover shift does not exist.'}, status=400)

    try:
        photo = _validate_clock_photo(request.FILES.get('photo'))
    except ValueError as error:
        return JsonResponse({'detail': str(error)}, status=400)

    with transaction.atomic():
        existing = employee.attendance_records.select_for_update().filter(attendance_date=today).first()
        if existing is not None:
            if existing.time_in and existing.time_out:
                return JsonResponse({'detail': 'An attendance record already exists for today. Multiple shift segments are not enabled yet; ask HR to reconcile the record.'}, status=409)
            return JsonResponse({'detail': 'You are already clocked in.'}, status=409)

        assignment = employee.assignments.filter(start_date__lte=today).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=today)
        ).order_by('-is_primary', '-start_date').first()
        record = AttendanceRecord.objects.create(
            employee=employee,
            assignment=assignment,
            clock_shift=shift,
            clock_in_mode=AttendanceRecord.ClockInMode.COVER,
            attendance_date=today,
            time_in=timezone.now(),
            clock_in_photo=photo,
            status=AttendanceRecord.Status.PRESENT,
            remarks='Cover shift clock-in; permanent assignment preserved. Payroll reconciliation required.'
        )
        record_audit(
            organization=employee.organization,
            actor=request.user,
            action='attendance.cover_clocked_in',
            entity=record,
            details={'covered_shift_id': str(shift.id), 'covered_shift': shift.name, 'photo_required': True},
        )

    return JsonResponse(_clock_state(employee))

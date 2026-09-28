import json

from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST

from apps.core.services import record_audit
from .disbursement import prepare_bank_disbursement
from .models import PayrollPeriod
from .views import _membership


@require_POST
def payroll_disbursement_export(request, period_id):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
    membership = _membership(request, 'manage_payroll')
    if membership is None:
        return JsonResponse({'detail': 'Payroll management permission is required.'}, status=403)
    try:
        period = PayrollPeriod.objects.get(id=period_id, organization=membership.organization)
        result = prepare_bank_disbursement(period, request.user)
    except PayrollPeriod.DoesNotExist:
        return JsonResponse({'detail': 'Payroll period not found.'}, status=404)
    except ValueError as exc:
        return JsonResponse({'detail': str(exc)}, status=409)
    record_audit(organization=membership.organization, actor=request.user, action='payroll.disbursement.exported', entity=period, details={k:v for k,v in result.items() if k != 'content'})
    response = HttpResponse(result['content'], content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{result["filename"]}"'
    response['X-Disbursement-SHA256'] = result['sha256']
    return response

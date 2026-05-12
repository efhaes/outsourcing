from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction

from outsourcing.decorators import supervisor_required
from outsourcing.models import (
    IzinStaff, StatusIzinChoices,
    Absensi, StatusHarianChoices,
    StaffSupervisor,
)


def _staff_ids(user):
    return StaffSupervisor.objects.filter(
        supervisor=user, is_active=True
    ).values_list('staff_id', flat=True)


@supervisor_required
def izin_list(request):
    """List semua izin staff di bawah supervisor ini."""
    ids = _staff_ids(request.user)

    status_filter = request.GET.get('status', '').strip()

    izin_qs = (
        IzinStaff.objects
        .filter(staff_id__in=ids)
        .select_related('staff', 'direview_oleh')
        .order_by('-dibuat_pada')
    )

    if status_filter:
        izin_qs = izin_qs.filter(status=status_filter)

    total_pending  = izin_qs.filter(status=StatusIzinChoices.PENDING).count()
    total_approved = izin_qs.filter(status=StatusIzinChoices.APPROVED).count()
    total_rejected = izin_qs.filter(status=StatusIzinChoices.REJECTED).count()

    return render(request, 'supervisor/izin/list.html', {
        'izin_qs'       : izin_qs,
        'status_filter' : status_filter,
        'total_pending' : total_pending,
        'total_approved': total_approved,
        'total_rejected': total_rejected,
        'status_choices': StatusIzinChoices.choices,
    })


@supervisor_required
def izin_detail(request, pk):
    """Detail satu izin — supervisor bisa approve/reject dari sini."""
    ids  = _staff_ids(request.user)
    izin = get_object_or_404(IzinStaff, pk=pk, staff_id__in=ids)
    return render(request, 'supervisor/izin/detail.html', {'izin': izin})


@supervisor_required
@require_POST
def izin_approve(request, pk):
    """Approve izin → loop tanggal → update/create Absensi.status_harian."""
    ids  = _staff_ids(request.user)
    izin = get_object_or_404(IzinStaff, pk=pk, staff_id__in=ids)

    if izin.status != StatusIzinChoices.PENDING:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': 'Izin sudah diproses sebelumnya.'})
        return redirect('supervisor_izin_detail', pk=pk)

    # Map tipe izin → status harian
    TIPE_TO_STATUS = {
        'sakit'   : StatusHarianChoices.DOKTER,
        'cuti'    : StatusHarianChoices.CUTI,
        'keluarga': StatusHarianChoices.IZIN,
        'lainnya' : StatusHarianChoices.IZIN,
    }
    status_harian = TIPE_TO_STATUS.get(izin.tipe, StatusHarianChoices.IZIN)

    with transaction.atomic():
        izin.status        = StatusIzinChoices.APPROVED
        izin.direview_oleh = request.user
        izin.direview_pada = timezone.now()
        izin.save(update_fields=['status', 'direview_oleh', 'direview_pada'])

        # Loop setiap tanggal dalam rentang izin
        from datetime import timedelta
        tanggal = izin.tanggal_mulai
        while tanggal <= izin.tanggal_selesai:
            Absensi.objects.update_or_create(
                staff   = izin.staff,
                tanggal = tanggal,
                defaults={'status_harian': status_harian},
            )
            tanggal += timedelta(days=1)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'ok'          : True,
            'message'     : f'Izin {izin.get_tipe_display()} disetujui.',
            'new_status'  : 'approved',
            'jumlah_hari' : izin.jumlah_hari,
        })
    return redirect('supervisor_izin_list')


@supervisor_required
@require_POST
def izin_reject(request, pk):
    """Reject izin dengan catatan."""
    ids  = _staff_ids(request.user)
    izin = get_object_or_404(IzinStaff, pk=pk, staff_id__in=ids)

    if izin.status != StatusIzinChoices.PENDING:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': 'Izin sudah diproses sebelumnya.'})
        return redirect('supervisor_izin_detail', pk=pk)

    catatan = request.POST.get('catatan', '').strip()
    if not catatan:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': 'Catatan penolakan wajib diisi.'})
        return redirect('supervisor_izin_detail', pk=pk)

    with transaction.atomic():
        izin.status             = StatusIzinChoices.REJECTED
        izin.catatan_supervisor = catatan
        izin.direview_oleh      = request.user
        izin.direview_pada      = timezone.now()
        izin.save(update_fields=[
            'status', 'catatan_supervisor', 'direview_oleh', 'direview_pada'
        ])

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'ok'        : True,
            'message'   : 'Izin ditolak.',
            'new_status': 'rejected',
            'catatan'   : catatan,
        })
    return redirect('supervisor_izin_list')
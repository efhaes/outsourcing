from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from outsourcing.decorators import kepala_supervisor_required
from outsourcing.models import User, SupervisorPerusahaan, StaffSupervisor
from outsourcing.forms.user_forms import CreateSupervisorForm, EditUserForm
from outsourcing.utils import get_supervisor_list, get_staff_list


@kepala_supervisor_required
def supervisor_list(request):
    """
    Kepala Supervisor melihat daftar Supervisor di bawahnya.
    """
    q           = request.GET.get('q', '').strip()
    supervisors = get_supervisor_list(request.user)

    if q:
        supervisors = supervisors.filter(
            Q(nama_lengkap__icontains=q) | Q(username__icontains=q)
        )

    # Tambahkan info perusahaan yang dipegang tiap supervisor
    supervisor_data = []
    for spv in supervisors:
        penugasan = SupervisorPerusahaan.objects.filter(
            supervisor=spv,
            kepala_supervisor=request.user,
            is_active=True,
        ).select_related('perusahaan', 'jenis_jasa')
        supervisor_data.append({
            'supervisor': spv,
            'penugasan' : penugasan,
        })

    context = {
        'supervisor_data': supervisor_data,
        'q'              : q,
        'page_title'     : 'Daftar Supervisor Lapangan',
    }
    return render(request, 'kepala_supervisor/akun/supervisor_list.html', context)


@kepala_supervisor_required
def supervisor_create(request):
    """
    Kepala Supervisor membuat akun Supervisor Lapangan baru.
    """
    if request.method == 'POST':
        form = CreateSupervisorForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'supervisor'
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(
                request,
                f'Akun Supervisor "{user.nama_lengkap}" berhasil dibuat. '
                 'Silakan assign ke perusahaan di menu Penugasan.'
            )
            return redirect('kepala_supervisor_list')
    else:
        form = CreateSupervisorForm()

    context = {
        'form'      : form,
        'page_title': 'Tambah Supervisor Lapangan',
        'action'    : 'Buat Akun',
    }
    return render(request, 'kepala_supervisor/akun/form_supervisor.html', context)


@kepala_supervisor_required
def supervisor_edit(request, pk):
    """Edit data supervisor (yang ada di bawah kepala ini)."""
    # Pastikan supervisor ini memang di bawah kepala yang login
    supervisor = get_object_or_404(User, pk=pk, role='supervisor')
    is_bawahan = SupervisorPerusahaan.objects.filter(
        supervisor=supervisor,
        kepala_supervisor=request.user,
    ).exists()

    if not is_bawahan:
        messages.error(request, 'Supervisor ini bukan di bawah tanggung jawab Anda.')
        return redirect('kepala_supervisor_list')

    if request.method == 'POST':
        form = EditUserForm(request.POST, request.FILES, instance=supervisor)
        if form.is_valid():
            form.save()
            messages.success(request, f'Akun "{supervisor.nama_lengkap}" berhasil diperbarui.')
            return redirect('kepala_supervisor_list')
    else:
        form = EditUserForm(instance=supervisor)

    context = {
        'form'      : form,
        'supervisor': supervisor,
        'page_title': f'Edit Supervisor — {supervisor.nama_lengkap}',
        'action'    : 'Simpan Perubahan',
    }
    return render(request, 'kepala_supervisor/akun/form_edit.html', context)


@kepala_supervisor_required
def supervisor_toggle_aktif(request, pk):
    """Aktifkan / nonaktifkan akun supervisor."""
    supervisor = get_object_or_404(User, pk=pk, role='supervisor')

    if request.method == 'POST':
        supervisor.is_active = not supervisor.is_active
        supervisor.save()
        status = 'diaktifkan' if supervisor.is_active else 'dinonaktifkan'
        messages.success(request, f'Akun "{supervisor.nama_lengkap}" berhasil {status}.')
        return redirect('kepala_supervisor_list')

    context = {
        'supervisor': supervisor,
        'page_title': f'Toggle Akun — {supervisor.nama_lengkap}',
    }
    return render(request, 'kepala_supervisor/akun/confirm_toggle.html', context)


@kepala_supervisor_required
def staff_list(request):
    """
    Kepala Supervisor memantau semua staff
    yang ada di bawah supervisor-nya.
    """
    q        = request.GET.get('q', '').strip()
    spv_id   = request.GET.get('supervisor', '').strip()
    staff_qs = get_staff_list(request.user)

    if q:
        staff_qs = staff_qs.filter(
            Q(nama_lengkap__icontains=q) | Q(username__icontains=q)
        )
    if spv_id:
        staff_qs = staff_qs.filter(
            supervisor_saya__supervisor__pk=spv_id,
            supervisor_saya__is_active=True,
        )

    # Tambahkan info supervisor tiap staff
    staff_data = []
    for stf in staff_qs:
        rel = StaffSupervisor.objects.filter(
            staff=stf, is_active=True
        ).select_related('supervisor').first()
        staff_data.append({
            'staff'     : stf,
            'supervisor': rel.supervisor if rel else None,
        })

    # List supervisor untuk filter dropdown
    from outsourcing.utils import get_supervisor_list
    supervisor_list = get_supervisor_list(request.user)

    context = {
        'staff_data'     : staff_data,
        'supervisor_list': supervisor_list,
        'q'              : q,
        'spv_id'         : spv_id,
        'page_title'     : 'Daftar Staff Lapangan',
    }
    return render(request, 'kepala_supervisor/akun/staff_list.html', context)



@kepala_supervisor_required
def pilih_supervisor(request):
    penugasan = SupervisorPerusahaan.objects.filter(
        kepala_supervisor=request.user,
        is_active=True,
    ).select_related('supervisor', 'perusahaan', 'jenis_jasa').order_by('supervisor__nama_lengkap')

    supervisors = {}
    for p in penugasan:
        if p.supervisor_id not in supervisors:
            supervisors[p.supervisor_id] = {
                'supervisor': p.supervisor,
                'penugasan' : [],
            }
        supervisors[p.supervisor_id]['penugasan'].append(p)

    return render(request, 'kepala_supervisor/akun/pilih_supervisor.html', {
        'supervisors'          : supervisors.values(),
        'acting_as_supervisor' : request.session.get('acting_as_supervisor_id'),
        'page_title'           : 'Pilih Supervisor',
    })


@kepala_supervisor_required
def set_acting_supervisor(request, supervisor_id):
    """Simpan pilihan supervisor ke session, lalu redirect ke dashboard supervisor."""
    is_assigned = SupervisorPerusahaan.objects.filter(
        kepala_supervisor=request.user,
        supervisor_id=supervisor_id,
        is_active=True,
    ).exists()

    if not is_assigned:
        messages.error(request, 'Supervisor ini tidak di bawah pengawasan Anda.')
        return redirect('kepala_pilih_supervisor')

    request.session['acting_as_supervisor_id'] = supervisor_id
    messages.success(request, 'Anda sekarang mengakses sebagai supervisor tersebut.')
    return redirect('supervisor_dashboard')


@kepala_supervisor_required  
def clear_acting_supervisor(request):
    """Kembali ke mode kepala supervisor normal."""
    request.session.pop('acting_as_supervisor_id', None)
    return redirect('kepala_dashboard')
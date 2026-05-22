from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from outsourcing.decorators import supervisor_required
from outsourcing.models import User, StaffSupervisor, StaffTask
from outsourcing.forms.user_forms import CreateStaffForm,EditStaffForm


@supervisor_required
def staff_list(request):
    """Daftar staff lapangan di bawah supervisor yang login."""
    q = request.GET.get('q', '').strip()

    staff_qs = User.objects.filter(
        supervisor_saya__supervisor=request.user,
        supervisor_saya__is_active=True,
    ).order_by('nama_lengkap')

    if q:
        staff_qs = staff_qs.filter(
            Q(nama_lengkap__icontains=q) | Q(username__icontains=q)
        )

    context = {
        'staff_list': staff_qs,
        'q'         : q,
        'page_title': 'Staff Lapangan Saya',
    }
    return render(request, 'supervisor/staff/list.html', context)


@supervisor_required
def staff_create(request):
    """
    Supervisor membuat akun Staff baru,
    lalu otomatis di-assign ke dirinya via StaffSupervisor.
    """
    if request.method == 'POST':
        form = CreateStaffForm(request.POST, request.FILES, supervisor=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'staff'
            user.set_password(form.cleaned_data['password'])
            user.save()

            # Assign staff ke supervisor yang login
            StaffSupervisor.objects.create(
                staff=user,
                supervisor=request.user,
                area_kerja=form.cleaned_data.get('area_kerja'),  # ← TAMBAH
                is_active=True,
            )

            # Assign tasks yang dipilih
            tasks = form.cleaned_data.get('tasks', [])
            for task in tasks:
                StaffTask.objects.create(
                    staff=user,
                    task=task,
                    is_active=True,
                )

            messages.success(
                request,
                f'Akun Staff "{user.nama_lengkap}" berhasil dibuat dan '
                f'ditugaskan ke wilayah Anda.'
            )
            return redirect('supervisor_staff_list')
        else:
            # Tampilkan error form
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'Error {field}: {error}')
    else:
        form = CreateStaffForm(supervisor=request.user)

    context = {
        'form'      : form,
        'page_title': 'Tambah Staff Lapangan',
        'action'    : 'Buat Akun',
    }
    return render(request, 'supervisor/staff/form.html', context)


@supervisor_required
def staff_edit(request, pk):
    staff = get_object_or_404(User, pk=pk, role='staff')

    is_bawahan = StaffSupervisor.objects.filter(
        staff=staff,
        supervisor=request.user,
        is_active=True,
    ).exists()

    if not is_bawahan:
        messages.error(request, 'Staff ini bukan di bawah wilayah Anda.')
        return redirect('supervisor_staff_list')

    if request.method == 'POST':
        form = EditStaffForm(
            request.POST,
            request.FILES,
            instance=staff,
            supervisor=request.user,
        )
        if form.is_valid():
            # Save user + handle password dalam satu commit
            user = form.save(commit=False)
            password = form.cleaned_data.get('password')
            if password:
                user.set_password(password)
            user.save()

            # Update StaffTask — hapus lama, isi baru
            tasks = form.cleaned_data.get('tasks', [])
            StaffTask.objects.filter(staff=staff).delete()
            for task in tasks:
                StaffTask.objects.create(staff=staff, task=task, is_active=True)

            # Update area_kerja di StaffSupervisor
            area_kerja = form.cleaned_data.get('area_kerja')
            StaffSupervisor.objects.filter(
                staff=staff,
                supervisor=request.user,
                is_active=True,
            ).update(area_kerja=area_kerja)

            messages.success(request, f'Data staff "{staff.nama_lengkap}" berhasil diperbarui.')
            return redirect('supervisor_staff_list')
    else:
        form = EditStaffForm(instance=staff, supervisor=request.user)

    context = {
        'form'      : form,
        'staff'     : staff,
        'page_title': f'Edit Staff — {staff.nama_lengkap}',
        'action'    : 'Simpan Perubahan',
    }
    return render(request, 'supervisor/staff/form_edit.html', context)


@supervisor_required
def staff_toggle_aktif(request, pk):
    """Aktifkan / nonaktifkan akun staff."""
    staff = get_object_or_404(User, pk=pk, role='staff')

    is_bawahan = StaffSupervisor.objects.filter(
        staff=staff,
        supervisor=request.user,
        is_active=True,
    ).exists()

    if not is_bawahan:
        messages.error(request, 'Staff ini bukan di bawah wilayah Anda.')
        return redirect('supervisor_staff_list')

    if request.method == 'POST':
        staff.is_active = not staff.is_active
        staff.save()
        status = 'diaktifkan' if staff.is_active else 'dinonaktifkan'
        messages.success(request, f'Akun "{staff.nama_lengkap}" berhasil {status}.')
        return redirect('supervisor_staff_list')

    context = {
        'staff'     : staff,
        'page_title': f'Toggle Akun — {staff.nama_lengkap}',
    }
    return render(request, 'supervisor/staff/confirm_toggle.html', context)


@supervisor_required
def staff_delete(request, pk):
    """Hapus staff (modal ajax)."""
    staff = get_object_or_404(User, pk=pk, role='staff')

    # Pastikan staff ini memang bawahan supervisor yang login
    is_bawahan = StaffSupervisor.objects.filter(
        staff=staff,
        supervisor=request.user,
        is_active=True,
    ).exists()

    if not is_bawahan:
        return JsonResponse({'success': False, 'message': 'Staff ini bukan di bawah wilayah Anda.'})

    if request.method == 'POST':
        nama = staff.nama_lengkap
        staff.delete()
        return JsonResponse({'success': True, 'message': f'Staff "{nama}" berhasil dihapus.'})

    context = {'staff': staff}
    return render(request, 'supervisor/staff/delete_modal.html', context)
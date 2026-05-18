from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from outsourcing.decorators import admin_required
from outsourcing.models import User, KepalaSupervisorJasa, RoleChoices, Perusahaan
from outsourcing.forms.user_forms import CreateKepalaSupervisorForm, CreateCustomerForm, EditUserForm


@admin_required
def akun_list(request):
    q                 = request.GET.get('q', '').strip()
    role              = request.GET.get('role', '').strip()
    perusahaan_filter = request.GET.get('perusahaan', '').strip()

    akun = User.objects.exclude(role=RoleChoices.ADMIN).order_by('role', 'nama_lengkap')

    if perusahaan_filter:
        akun = akun.filter(perusahaan_id=perusahaan_filter)
    if q:
        akun = akun.filter(
            Q(nama_lengkap__icontains=q) | Q(username__icontains=q)
        )
    if role:
        akun = akun.filter(role=role)

    # Base queryset tanpa filter role/q untuk stats yang akurat
    base_qs = User.objects.exclude(role=RoleChoices.ADMIN)

    context = {
        'akun_list'      : akun,
        'role_choices'   : RoleChoices.choices,
        'q'              : q,
        'role'           : role,
        'page_title'     : 'Manajemen Akun',
        'perusahaan_list': Perusahaan.objects.all(),
        'perusahaan'     : perusahaan_filter,
        # Stats — total keseluruhan, bukan hasil filter
        'total_akun'     : base_qs.count(),
        'total_supervisor': base_qs.filter(role=RoleChoices.SUPERVISOR).count(),
        'total_staff'    : base_qs.filter(role=RoleChoices.STAFF).count(),
        'total_kepala'   : base_qs.filter(role=RoleChoices.KEPALA_SUPERVISOR).count(),
    }
    return render(request, 'admin/akun/list.html', context)


@admin_required
def akun_create_kepala(request):
    """
    Admin membuat akun Kepala Supervisor baru
    sekaligus assign ke Jenis Jasa yang dia tangani.
    """
    if request.method == 'POST':
        form = CreateKepalaSupervisorForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = RoleChoices.KEPALA_SUPERVISOR 
            user.is_active = True # pakai constant, bukan string
            user.set_password(form.cleaned_data['password'])
            user.save()

            jenis_jasa_list = form.cleaned_data.get('jenis_jasa', [])
            for jasa in jenis_jasa_list:
                KepalaSupervisorJasa.objects.get_or_create(
                    kepala_supervisor=user,
                    jenis_jasa=jasa,
                )

            messages.success(
                request,
                f'Akun Kepala Supervisor "{user.nama_lengkap}" berhasil dibuat.'
            )
            return redirect('admin_akun_list')
    else:
        form = CreateKepalaSupervisorForm()

    context = {
        'form'      : form,
        'page_title': 'Tambah Kepala Supervisor',
        'action'    : 'Buat Akun',
    }
    return render(request, 'admin/akun/form_kepala.html', context)


@admin_required
def akun_create_customer(request):
    """
    Admin membuat akun Customer baru.
    Customer akan di-link ke Perusahaan nanti via halaman Perusahaan.
    """
    if request.method == 'POST':
        form = CreateCustomerForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = RoleChoices.CUSTOMER
            user.is_active = True
            user.set_password(form.cleaned_data['password'])
            user.save()

            messages.success(
                request,
                f'Akun Customer "{user.nama_lengkap}" berhasil dibuat. '
                f'Silakan assign ke Perusahaan di halaman Perusahaan.'
            )
            return redirect('admin_akun_list')
    else:
        form = CreateCustomerForm()

    context = {
        'form'      : form,
        'page_title': 'Tambah Customer',
        'action'    : 'Buat Akun',
    }
    return render(request, 'admin/akun/form_customer.html', context)


@admin_required
def akun_edit(request, pk):
    """Edit data akun (nama, telepon, foto profil, status aktif)."""
    akun = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        form = EditUserForm(request.POST, request.FILES, instance=akun)
        if form.is_valid():
            form.save()
            messages.success(request, f'Akun "{akun.nama_lengkap}" berhasil diperbarui.')
            return redirect('admin_akun_list')
    else:
        form = EditUserForm(instance=akun)

    context = {
        'form'      : form,
        'akun'      : akun,
        'page_title': f'Edit Akun — {akun.nama_lengkap}',
        'action'    : 'Simpan Perubahan',
    }
    return render(request, 'admin/akun/form_edit.html', context)


@admin_required
def akun_edit_kepala(request, pk):
    """Edit data Kepala Supervisor (nama, telepon, foto profil, jenis jasa)."""
    akun = get_object_or_404(User, pk=pk, role=RoleChoices.KEPALA_SUPERVISOR)
    
    if request.method == 'POST':
        form = CreateKepalaSupervisorForm(request.POST, request.FILES, instance=akun)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = RoleChoices.KEPALA_SUPERVISOR
            user.is_active = True
            if form.cleaned_data.get('password'):
                user.set_password(form.cleaned_data['password'])
            user.save()

            # Update jenis jasa
            KepalaSupervisorJasa.objects.filter(kepala_supervisor=user).delete()
            jenis_jasa_list = form.cleaned_data.get('jenis_jasa', [])
            for jasa in jenis_jasa_list:
                KepalaSupervisorJasa.objects.get_or_create(
                    kepala_supervisor=user,
                    jenis_jasa=jasa,
                )

            messages.success(
                request,
                f'Akun Kepala Supervisor "{user.nama_lengkap}" berhasil diperbarui.'
            )
            return redirect('admin_akun_list')
    else:
        # Pre-populate form dengan data existing
        initial_data = {
            'nama_lengkap': akun.nama_lengkap,
            'username': akun.username,
            'email': akun.email,
            'telepon': akun.telepon,
            'jenis_jasa': list(akun.kepala_supervisor_jasa.values_list('jenis_jasa', flat=True)),
        }
        form = CreateKepalaSupervisorForm(initial=initial_data)

    context = {
        'form'      : form,
        'akun'      : akun,
        'page_title': f'Edit Kepala Supervisor — {akun.nama_lengkap}',
        'action'    : 'Simpan Perubahan',
        'is_edit'   : True,
    }
    return render(request, 'admin/akun/form_kepala.html', context)


@admin_required
def akun_toggle_aktif(request, pk):
    """Aktifkan / nonaktifkan akun user. Hanya menerima POST."""
    # Tolak GET — toggle state via GET berbahaya (bisa ditrigger tanpa sengaja)
    if request.method != 'POST':
        return redirect('admin_akun_list')

    akun = get_object_or_404(User, pk=pk)

    # Jangan biarkan admin menonaktifkan dirinya sendiri
    if akun.pk == request.user.pk:
        messages.error(request, 'Tidak bisa menonaktifkan akun sendiri.')
        return redirect('admin_akun_list')

    akun.is_active = not akun.is_active
    akun.save(update_fields=['is_active'])
    status = 'diaktifkan' if akun.is_active else 'dinonaktifkan'
    messages.success(request, f'Akun "{akun.nama_lengkap}" berhasil {status}.')
    return redirect('admin_akun_list')
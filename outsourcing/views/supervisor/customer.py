from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from outsourcing.decorators import supervisor_required
from outsourcing.models import User, SupervisorPerusahaan, Perusahaan, RoleChoices
from outsourcing.forms.user_forms import CreateCustomerSupervisorForm


@supervisor_required
def customer_create(request):
    """
    Supervisor membuat akun Customer untuk perusahaan yang dia tangani.
    Customer langsung di-link ke perusahaan yang dipilih.
    """
    if request.method == 'POST':
        form = CreateCustomerSupervisorForm(
            request.POST,
            request.FILES,
            supervisor=request.user
        )
        if form.is_valid():
            user = form.save(commit=False)
            user.role = RoleChoices.CUSTOMER
            user.set_password(form.cleaned_data['password'])
            user.save()

            # Link customer ke perusahaan yang dipilih
            perusahaan = form.cleaned_data.get('perusahaan')
            if perusahaan:
                perusahaan.customer = user
                perusahaan.save(update_fields=['customer'])

            messages.success(
                request,
                f'Akun Customer "{user.nama_lengkap}" berhasil dibuat '
                f'dan di-link ke perusahaan "{perusahaan.nama_perusahaan}".'
            )
            return redirect('supervisor_dashboard')
    else:
        form = CreateCustomerSupervisorForm(supervisor=request.user)

    context = {
        'form'      : form,
        'page_title': 'Tambah Customer',
        'action'    : 'Buat Akun',
    }
    return render(request, 'supervisor/customer/form.html', context)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from outsourcing.decorators import supervisor_required
from outsourcing.models import Task, JenisJasa, SupervisorPerusahaan
from outsourcing.forms.task_forms import TaskForm


@supervisor_required
def task_list(request):
    q = request.GET.get('q', '').strip()

    task_qs = Task.objects.filter(
        supervisor=request.user,
        is_active=True,
    ).select_related('jenis_jasa').order_by('nama_task')

    if q:
        task_qs = task_qs.filter(nama_task__icontains=q)

    context = {
        'task_list' : task_qs,
        'q'         : q,
        'page_title': 'Task / Pekerjaan',
    }
    return render(request, 'supervisor/task/list.html', context)


@supervisor_required
def task_create(request):
    # Ambil jenis jasa dari penugasan supervisor
    jenis_jasa_id = SupervisorPerusahaan.objects.filter(
        supervisor=request.user, is_active=True,
    ).values_list('jenis_jasa_id', flat=True).first()

    if not jenis_jasa_id:
        messages.error(request, 'Anda belum ditugaskan ke jenis jasa manapun.')
        return redirect('supervisor_task_list')

    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.supervisor  = request.user
            task.jenis_jasa_id = jenis_jasa_id
            task.save()
            messages.success(request, f'Task "{task.nama_task}" berhasil dibuat.')
            return redirect('supervisor_task_list')
    else:
        form = TaskForm()

    return render(request, 'supervisor/task/form.html', {
        'form'      : form,
        'page_title': 'Tambah Task',
        'action'    : 'Buat Task',
    })


@supervisor_required
def task_edit(request, pk):
    task = get_object_or_404(Task, pk=pk, supervisor=request.user)

    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, f'Task "{task.nama_task}" berhasil diperbarui.')
            return redirect('supervisor_task_list')
    else:
        form = TaskForm(instance=task)

    return render(request, 'supervisor/task/form.html', {
        'form'      : form,
        'task'      : task,
        'page_title': f'Edit Task — {task.nama_task}',
        'action'    : 'Simpan Perubahan',
    })


@supervisor_required
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk, supervisor=request.user)

    if request.method == 'POST':
        nama = task.nama_task
        task.delete()
        messages.success(request, f'Task "{nama}" berhasil dihapus.')
        return redirect('supervisor_task_list')

    return render(request, 'supervisor/task/confirm_delete.html', {
        'task'      : task,
        'page_title': f'Hapus Task — {task.nama_task}',
    })

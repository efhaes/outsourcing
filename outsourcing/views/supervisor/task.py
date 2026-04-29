from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from outsourcing.decorators import supervisor_required
from outsourcing.models import Task, JenisJasa, SupervisorPerusahaan
from outsourcing.forms.task_forms import TaskForm


@supervisor_required
def task_list(request):
    """Daftar task yang bisa dikelola supervisor (berdasarkan jenis jasa yang ditugaskan)."""
    q = request.GET.get('q', '').strip()
    
    # Jenis jasa yang ditugaskan ke supervisor ini
    penugasan = SupervisorPerusahaan.objects.filter(
        supervisor=request.user,
        is_active=True
    ).values_list('jenis_jasa_id', flat=True)
    
    task_qs = Task.objects.filter(
        jenis_jasa_id__in=penugasan
    ).select_related('jenis_jasa').order_by('jenis_jasa', 'nama_task')
    
    if q:
        task_qs = task_qs.filter(
            Q(nama_task__icontains=q) | Q(jenis_jasa__nama_jasa__icontains=q)
        )
    
    context = {
        'task_list' : task_qs,
        'q'         : q,
        'page_title': 'Task / Pekerjaan',
    }
    return render(request, 'supervisor/task/list.html', context)


@supervisor_required
def task_create(request):
    """Buat task baru (modal ajax)."""
    if request.method == 'POST':
        form = TaskForm(request.POST, supervisor=request.user)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Task berhasil dibuat.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = TaskForm(supervisor=request.user)
    
    context = {'form': form}
    return render(request, 'supervisor/task/form_modal.html', context)


@supervisor_required
def task_edit(request, pk):
    """Edit task (modal ajax)."""
    task = get_object_or_404(Task, pk=pk)
    
    # Pastikan task ini milik jenis jasa yang ditugaskan ke supervisor
    penugasan = SupervisorPerusahaan.objects.filter(
        supervisor=request.user,
        is_active=True,
        jenis_jasa=task.jenis_jasa
    ).exists()
    
    if not penugasan:
        return JsonResponse({'success': False, 'message': 'Task ini bukan di wilayah Anda.'})
    
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task, supervisor=request.user)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Task berhasil diperbarui.'})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = TaskForm(instance=task, supervisor=request.user)
    
    context = {'form': form, 'task': task}
    return render(request, 'supervisor/task/form_modal.html', context)


@supervisor_required
def task_delete(request, pk):
    """Hapus task (modal ajax)."""
    task = get_object_or_404(Task, pk=pk)
    
    # Pastikan task ini milik jenis jasa yang ditugaskan ke supervisor
    penugasan = SupervisorPerusahaan.objects.filter(
        supervisor=request.user,
        is_active=True,
        jenis_jasa=task.jenis_jasa
    ).exists()
    
    if not penugasan:
        return JsonResponse({'success': False, 'message': 'Task ini bukan di wilayah Anda.'})
    
    if request.method == 'POST':
        nama = task.nama_task
        task.delete()
        return JsonResponse({'success': True, 'message': f'Task "{nama}" berhasil dihapus.'})
    
    context = {'task': task}
    return render(request, 'supervisor/task/delete_modal.html', context)

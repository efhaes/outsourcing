from django import forms
from outsourcing.models import Task, JenisJasa, SupervisorPerusahaan


class TaskForm(forms.ModelForm):
    """
    Form untuk CRUD Task oleh Supervisor Lapangan.
    Jenis jasa di-filter berdasarkan penugasan supervisor.
    """
    def __init__(self, *args, supervisor=None, **kwargs):
        super().__init__(*args, **kwargs)
        if supervisor:
            # Filter jenis jasa berdasarkan penugasan supervisor
            penugasan = SupervisorPerusahaan.objects.filter(
                supervisor=supervisor,
                is_active=True
            ).values_list('jenis_jasa_id', flat=True)
            self.fields['jenis_jasa'].queryset = JenisJasa.objects.filter(
                pk__in=penugasan,
                is_active=True
            )
    
    def clean(self):
        cleaned_data = super().clean()
        jenis_jasa = cleaned_data.get('jenis_jasa')
        nama_task = cleaned_data.get('nama_task')
        
        # Cek duplikasi (unique_together)
        if jenis_jasa and nama_task:
            qs = Task.objects.filter(jenis_jasa=jenis_jasa, nama_task=nama_task)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f'Task "{nama_task}" dengan jenis jasa "{jenis_jasa.nama_jasa}" sudah ada.'
                )
        return cleaned_data

    class Meta:
        model  = Task
        fields = ['jenis_jasa', 'nama_task', 'deskripsi', 'is_active']
        widgets = {
            'jenis_jasa': forms.Select(attrs={'class': 'form-select'}),  # ← tambah ini
            'nama_task' : forms.TextInput(attrs={'class': 'form-control'}),
            'deskripsi' : forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active'  : forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'jenis_jasa': 'Jenis Jasa',
            'nama_task' : 'Nama Task',
            'deskripsi' : 'Deskripsi',
            'is_active'  : 'Aktif',
        }

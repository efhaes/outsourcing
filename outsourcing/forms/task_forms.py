from django import forms
from outsourcing.models import Task

class TaskForm(forms.ModelForm):
    def __init__(self, *args, supervisor=None, **kwargs):
        super().__init__(*args, **kwargs)
        # jenis_jasa tidak perlu ditampilkan, di-set otomatis di view

    def clean(self):
        cleaned_data = super().clean()
        jenis_jasa   = cleaned_data.get('jenis_jasa')
        nama_task    = cleaned_data.get('nama_task')

        if jenis_jasa and nama_task:
            qs = Task.objects.filter(jenis_jasa=jenis_jasa, nama_task=nama_task)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f'Task "{nama_task}" sudah ada.'
                )
        return cleaned_data

    class Meta:
        model  = Task
        fields = ['nama_task', 'deskripsi', 'is_active']  # ← hapus jenis_jasa
        widgets = {
            'nama_task': forms.TextInput(attrs={'class': 'form-control'}),
            'deskripsi': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'nama_task': 'Nama Task',
            'deskripsi': 'Deskripsi',
            'is_active': 'Aktif',
        }
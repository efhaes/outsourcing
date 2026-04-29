from django import forms
from outsourcing.models import (
    LaporanKegiatan, ItemKegiatan,
    Perusahaan, JenisJasa, AreaKerja, SubArea, Task,
    User, RoleChoices, SupervisorPerusahaan, StaffSupervisor, StaffTask
)


class LaporanKegiatanForm(forms.ModelForm):
    """
    Form buat/edit laporan oleh Supervisor.
    Pilihan perusahaan, jenis_jasa, dan area di-filter
    sesuai penugasan supervisor yang login.
    """
    def __init__(self, *args, supervisor=None, **kwargs):
        super().__init__(*args, **kwargs)
        if supervisor:
            # Perusahaan yang ditugaskan ke supervisor ini
            penugasan = SupervisorPerusahaan.objects.filter(
                supervisor=supervisor, is_active=True
            ).select_related('perusahaan', 'jenis_jasa')

            perusahaan_ids = penugasan.values_list('perusahaan_id', flat=True)
            jenis_jasa_ids = penugasan.values_list('jenis_jasa_id', flat=True)

            perusahaan_qs = Perusahaan.objects.filter(
                pk__in=perusahaan_ids, is_active=True
            )
            self.fields['perusahaan'].queryset = perusahaan_qs
            
            # Tambahkan data attribute untuk mapping perusahaan ke jenis jasa
            perusahaan_jasa_mapping = {}
            for p in perusahaan_qs:
                perusahaan_jasa_mapping[str(p.pk)] = list(
                    p.jenis_jasa.filter(is_active=True).values_list('pk', flat=True)
                )
            self.fields['perusahaan'].widget.attrs['data-jasa-mapping'] = str(perusahaan_jasa_mapping)
            
            self.fields['jenis_jasa'].queryset = JenisJasa.objects.filter(
                pk__in=jenis_jasa_ids, is_active=True
            )
            self.fields['area'].queryset = AreaKerja.objects.filter(
                perusahaan__in=perusahaan_ids, is_active=True
            )

    perusahaan = forms.ModelChoiceField(
        queryset=Perusahaan.objects.none(),
        label='Perusahaan',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    jenis_jasa = forms.ModelChoiceField(
        queryset=JenisJasa.objects.none(),
        label='Jenis Jasa',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    area = forms.ModelChoiceField(
        queryset=AreaKerja.objects.none(),
        label='Area Kerja',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model  = LaporanKegiatan
        fields = ['nama_laporan', 'tanggal_laporan', 'perusahaan', 'jenis_jasa', 'area', 'catatan']
        widgets = {
            'nama_laporan'   : forms.TextInput(attrs={'class': 'form-control'}),
            'tanggal_laporan': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'catatan'        : forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'nama_laporan'   : 'Nama Laporan',
            'tanggal_laporan': 'Tanggal Laporan',
            'catatan'        : 'Catatan',
        }


class ItemKegiatanForm(forms.ModelForm):
    """
    Form buat/edit item kegiatan oleh Supervisor.
    Staff dan sub_area di-filter sesuai laporan yang dipilih.
    Task di-filter sesuai jenis jasa di laporan.
    Staff di-filter berdasarkan task yang dipilih (staff harus punya skill task tersebut).
    Tanggal bisa dipilih bebas oleh supervisor untuk penjadwalan sebulan ke depan.
    """
    def __init__(self, *args, laporan=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.laporan = laporan
        if laporan:
            # Task sesuai jenis jasa di laporan
            self.fields['task'].queryset = Task.objects.filter(
                jenis_jasa=laporan.jenis_jasa,
                is_active=True
            )
 
            # Staff yang ada di bawah supervisor pembuat laporan
            self.fields['staff'].queryset = User.objects.filter(
                role=RoleChoices.STAFF,
                supervisor_saya__supervisor=laporan.supervisor,
                supervisor_saya__is_active=True,
                is_active=True,
            )
 
            # Sub area sesuai area laporan
            self.fields['sub_area'].queryset = SubArea.objects.filter(
                area=laporan.area, is_active=True
            )
 
    def clean(self):
        cleaned_data = super().clean()
 
        # Set laporan pada instance sebelum model clean() dipanggil
        if self.laporan:
            self.instance.laporan = self.laporan
 
        staff         = cleaned_data.get('staff')
        task          = cleaned_data.get('task')
        is_insidental = cleaned_data.get('is_insidental')
 
        if staff and self.laporan and not is_insidental:
            supervisor = self.laporan.supervisor
 
            # Staff harus terdaftar di bawah supervisor pembuat laporan
            for staff_member in staff:
                is_staff_valid = StaffSupervisor.objects.filter(
                    staff=staff_member,
                    supervisor=supervisor,
                    is_active=True,
                ).exists()
                if not is_staff_valid:
                    raise forms.ValidationError(
                        f"Staff '{staff_member}' tidak terdaftar di bawah supervisor '{supervisor}'."
                    )
 
            # Staff harus memiliki skill untuk task yang dipilih
            if task:
                for staff_member in staff:
                    has_skill = StaffTask.objects.filter(
                        staff=staff_member,
                        task=task,
                        is_active=True,
                    ).exists()
                    if not has_skill:
                        raise forms.ValidationError(
                            f"Staff '{staff_member}' tidak memiliki skill untuk task '{task.nama_task}'."
                        )
 
        return cleaned_data
 
    task = forms.ModelChoiceField(
        queryset=Task.objects.none(),
        required=False,
        label='Task / Pekerjaan',
        widget=forms.Select(attrs={
            'class'   : 'form-select',
            'id'      : 'id_task',
            'onchange': 'filterStaffByTask()',
        }),
    )
    staff = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        label='Staff',
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True,
    )
    sub_area = forms.ModelChoiceField(
        queryset=SubArea.objects.none(),
        required=False,
        label='Sub Area',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
 
    class Meta:
        model  = ItemKegiatan
        fields = ['task', 'nama_item', 'deskripsi', 'staff', 'sub_area', 'tanggal', 'is_insidental']
        widgets = {
            'nama_item': forms.TextInput(attrs={'class': 'form-control'}),
            'deskripsi': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'tanggal'  : forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        labels = {
            'task'         : 'Task / Pekerjaan',
            'nama_item'    : 'Nama Pekerjaan',
            'deskripsi'    : 'Deskripsi',
            'tanggal'      : 'Tanggal Pekerjaan',
            'is_insidental': 'Pekerjaan Insidental',
        }
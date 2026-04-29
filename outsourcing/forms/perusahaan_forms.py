from django import forms
from outsourcing.models import (
    Perusahaan, AreaKerja, SubArea, JenisJasa, User, RoleChoices, SupervisorPerusahaan
)
   # tambah di bagian import atas



class JenisJasaForm(forms.ModelForm):
    class Meta:
        model  = JenisJasa
        fields = ['nama_jasa', 'deskripsi', 'is_active']
        widgets = {
            'nama_jasa' : forms.TextInput(attrs={'class': 'form-control'}),
            'deskripsi' : forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'nama_jasa' : 'Nama Jasa',
            'deskripsi' : 'Deskripsi',
            'is_active'  : 'Aktif',
        }


class PerusahaanForm(forms.ModelForm):
    jenis_jasa = forms.ModelMultipleChoiceField(
        queryset=JenisJasa.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Jenis Jasa',
    )
    customer = forms.ModelChoiceField(
        queryset=User.objects.filter(role=RoleChoices.CUSTOMER,is_active=True),
        required=False,
        empty_label='— Pilih Customer —',
        label='Akun Customer',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model  = Perusahaan
        fields = ['nama_perusahaan', 'alamat', 'telepon', 'email', 'jenis_jasa', 'customer', 'is_active']
        widgets = {
            'nama_perusahaan': forms.TextInput(attrs={'class': 'form-control'}),
            'alamat'         : forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'telepon'        : forms.TextInput(attrs={'class': 'form-control'}),
            'email'          : forms.EmailInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'nama_perusahaan': 'Nama Perusahaan',
            'alamat'         : 'Alamat',
            'telepon'        : 'Telepon',
            'email'          : 'Email',
            'is_active'       : 'Aktif',
        }


class AreaKerjaForm(forms.ModelForm):
    def __init__(self, *args, perusahaan_qs=None, **kwargs):
        super().__init__(*args, **kwargs)
        if perusahaan_qs:
            self.fields['perusahaan'] = forms.ModelChoiceField(
                queryset=perusahaan_qs,
                label='Perusahaan',
                widget=forms.Select(attrs={'class': 'form-select'}),
            )

    class Meta:
        model = AreaKerja
        fields = ['perusahaan', 'nama_area', 'keterangan']
        widgets = {
            'nama_area': forms.TextInput(attrs={'class': 'form-control'}),
            'keterangan': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class SubAreaForm(forms.ModelForm):
    def __init__(self, *args, area_qs=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._area_qs = area_qs

        self.fields['area'] = forms.ModelChoiceField(
            queryset=area_qs if area_qs is not None else SubArea.objects.none(),
            label='Area',
            widget=forms.Select(attrs={'class': 'form-select'}),
        )

    def clean_area(self):
        area = self.cleaned_data.get('area')

        if not area:
            raise forms.ValidationError("Area wajib dipilih.")

        if self._area_qs is not None and area not in self._area_qs:
            raise forms.ValidationError("Area tidak termasuk dalam akses Anda.")

        return area

    def clean(self):
        cleaned_data = super().clean()
        area = cleaned_data.get('area')
        nama_sub_area = cleaned_data.get('nama_sub_area')

        if area and nama_sub_area:
            qs = SubArea.objects.filter(area=area, nama_sub_area=nama_sub_area)

            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError(
                    f'Sub Area "{nama_sub_area}" di area "{area}" sudah ada.'
                )

        return cleaned_data

    class Meta:
        model = SubArea
        fields = ['area', 'nama_sub_area', 'keterangan']
        widgets = {
            'nama_sub_area': forms.TextInput(attrs={'class': 'form-control'}),
            'keterangan': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class SupervisorPerusahaanForm(forms.ModelForm):
    """
    Dipakai Kepala Supervisor untuk assign Supervisor ke Perusahaan & Jenis Jasa.
    Queryset supervisor, jenis_jasa, perusahaan di-inject dari view
    agar hanya tampil pilihan yang relevan dengan kepala yang login.
    """
    def __init__(self, *args, supervisor_qs=None, jenis_jasa_qs=None, perusahaan_qs=None, **kwargs):
        super().__init__(*args, **kwargs)
        if supervisor_qs is not None:
            self.fields['supervisor'].queryset = supervisor_qs
        if jenis_jasa_qs is not None:
            self.fields['jenis_jasa'].queryset = jenis_jasa_qs
        if perusahaan_qs is not None:
            self.fields['perusahaan'].queryset = perusahaan_qs

    supervisor = forms.ModelChoiceField(
        queryset=User.objects.filter(role=RoleChoices.SUPERVISOR,is_active=True),
        label='Supervisor Lapangan',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    perusahaan = forms.ModelChoiceField(
        queryset=Perusahaan.objects.filter(is_active=True),
        label='Perusahaan',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    jenis_jasa = forms.ModelChoiceField(
        queryset=JenisJasa.objects.filter(is_active=True),
        label='Jenis Jasa',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model  = SupervisorPerusahaan
        fields = ['supervisor', 'perusahaan', 'jenis_jasa', 'is_active']
        labels = {'is_active': 'Aktif'}

    def clean(self):
        cleaned_data = super().clean()
        perusahaan   = cleaned_data.get('perusahaan')
        jenis_jasa   = cleaned_data.get('jenis_jasa')
        if perusahaan and jenis_jasa:
            if not perusahaan.jenis_jasa.filter(pk=jenis_jasa.pk).exists():
                raise forms.ValidationError(
                    f"Perusahaan '{perusahaan}' tidak menggunakan jasa '{jenis_jasa}'."
                )
        return cleaned_data
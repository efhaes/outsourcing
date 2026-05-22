from django import forms
from outsourcing.models import (
    SupervisorPerusahaan, StaffSupervisor,
    Perusahaan, JenisJasa, User, RoleChoices
)


class AssignSupervisorForm(forms.ModelForm):
    """
    Dipakai Kepala Supervisor untuk assign Supervisor ke Perusahaan + Jenis Jasa.
    kepala_supervisor di-set otomatis di view dari request.user.
    """
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
        fields = ['supervisor', 'perusahaan', 'jenis_jasa'] 

    def clean(self):
        cleaned_data = super().clean()
        perusahaan   = cleaned_data.get('perusahaan')
        jenis_jasa   = cleaned_data.get('jenis_jasa')
        # Validasi: jenis jasa harus digunakan oleh perusahaan tersebut
        if perusahaan and jenis_jasa:
            if not perusahaan.jenis_jasa.filter(pk=jenis_jasa.pk).exists():
                raise forms.ValidationError(
                    f"Perusahaan '{perusahaan}' tidak menggunakan jasa '{jenis_jasa}'."
                )
        return cleaned_data


class AssignStaffForm(forms.ModelForm):
    """
    Dipakai Supervisor Lapangan untuk assign Staff ke dirinya sendiri.
    supervisor di-set otomatis di view dari request.user.
    """
    staff = forms.ModelChoiceField(
        queryset=User.objects.filter(role=RoleChoices.STAFF,is_active=True),
        label='Staff Lapangan',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model  = StaffSupervisor
        fields = ['staff', 'is_active']
        labels = {'is_active': 'Aktif'}
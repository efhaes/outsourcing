from django import forms
from outsourcing.models import QRAbsensi, Absensi,IzinStaff, TipeIzinChoices


class QRAbsensiForm(forms.ModelForm):
    class Meta:
        model  = QRAbsensi
        fields = ['tanggal', 'berlaku_hingga']  # hapus 'laporan'
        widgets = {
            'tanggal'        : forms.DateInput(attrs={'type': 'date'}),
            'berlaku_hingga' : forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class AbsenMasukForm(forms.ModelForm):
    """
    Form untuk Staff absen masuk setelah scan QR.
    Field qr_absensi, staff, laporan, tanggal diisi otomatis dari view.
    """
    lat_masuk = forms.DecimalField(
        widget=forms.HiddenInput(), required=False
    )
    lon_masuk = forms.DecimalField(
        widget=forms.HiddenInput(), required=False
    )

    class Meta:
        model  = Absensi
        fields = ['lat_masuk', 'lon_masuk']


class AbsenPulangForm(forms.ModelForm):
    """
    Form untuk Staff absen pulang.
    """
    lat_pulang = forms.DecimalField(
        widget=forms.HiddenInput(), required=False
    )
    lon_pulang = forms.DecimalField(
        widget=forms.HiddenInput(), required=False
    )

    class Meta:
        model  = Absensi
        fields = [ 'lat_pulang', 'lon_pulang']
        


class IzinStaffForm(forms.ModelForm):
    class Meta:
        model  = IzinStaff
        fields = ['tipe', 'tanggal_mulai', 'tanggal_selesai', 'keterangan', 'lampiran']
        widgets = {
            'tipe'            : forms.Select(),
            'tanggal_mulai'   : forms.DateInput(attrs={'type': 'date'}),
            'tanggal_selesai' : forms.DateInput(attrs={'type': 'date'}),
            'keterangan'      : forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned = super().clean()
        tipe             = cleaned.get('tipe')
        tanggal_mulai    = cleaned.get('tanggal_mulai')
        tanggal_selesai  = cleaned.get('tanggal_selesai')
        lampiran         = cleaned.get('lampiran')

        if tanggal_mulai and tanggal_selesai:
            if tanggal_selesai < tanggal_mulai:
                raise forms.ValidationError('Tanggal selesai tidak boleh sebelum tanggal mulai.')

        if tipe == TipeIzinChoices.SAKIT and not lampiran:
            raise forms.ValidationError('Surat dokter wajib dilampirkan untuk izin sakit.')

        return cleaned
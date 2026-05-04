from django import forms
from outsourcing.models import QRAbsensi, Absensi


class QRAbsensiForm(forms.ModelForm):
    """
    Form untuk Supervisor generate QR per laporan per hari.
    """
    class Meta:
        model  = QRAbsensi
        fields = ['laporan', 'tanggal', 'berlaku_hingga']
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
        fields = ['foto_masuk', 'lat_masuk', 'lon_masuk']
        widgets = {
            'foto_masuk': forms.FileInput(attrs={
                'accept'  : 'image/*',
                'capture' : 'user',   # langsung buka kamera depan di mobile
            }),
        }


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
        fields = ['foto_pulang', 'lat_pulang', 'lon_pulang']
        widgets = {
            'foto_pulang': forms.FileInput(attrs={
                'accept'  : 'image/*',
                'capture' : 'user',
            }),
        }
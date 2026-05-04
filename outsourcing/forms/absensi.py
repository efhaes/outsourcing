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
        
from django import forms
from outsourcing.models import ItemKegiatan


class ItemKegiatanStaffForm(forms.ModelForm):
    """
    Form khusus Staff untuk mengisi progress pekerjaan.
    Jam mulai & jam selesai diisi via modal AJAX di halaman list.
    Form ini hanya untuk: foto on progress, foto after, catatan.
    """
    class Meta:
        model  = ItemKegiatan
        fields = [
            # 'jam_mulai' dan 'jam_selesai' DIHAPUS
            # karena sudah diisi via modal AJAX di list.html
            'foto_on_progress',
            'foto_after',
            'catatan_staff',
        ]
        widgets = {
            # widget jam_mulai & jam_selesai DIHAPUS
            'catatan_staff': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            # label jam_mulai & jam_selesai DIHAPUS
            'foto_on_progress': 'Foto On Progress',
            'foto_after'      : 'Foto Setelah Selesai',
            'catatan_staff'   : 'Catatan',
        }

    def clean(self):
        cleaned_data     = super().clean()
        foto_on_progress = cleaned_data.get('foto_on_progress')
        foto_after       = cleaned_data.get('foto_after')

        # Validasi jam dihapus karena jam diisi di step sebelumnya (modal AJAX)
        # Validasi foto_after vs jam_selesai ditangani di views.py
        # karena form tidak punya akses ke instance.jam_selesai secara langsung

        return cleaned_data
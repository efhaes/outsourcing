from .dashboard import dashboard_view
from .perusahaan import (
    perusahaan_list, perusahaan_create, perusahaan_detail,
    perusahaan_edit, perusahaan_delete
)
from .jenis_jasa import (
    jenis_jasa_list, jenis_jasa_create,
    jenis_jasa_edit, jenis_jasa_delete
)
from .akun import (
    akun_list, akun_create_kepala, akun_create_customer,
    akun_edit, akun_toggle_aktif
)
from .area import (
    area_list, area_create, area_edit, area_delete,
    subarea_create, subarea_edit, subarea_delete
)
from .laporan import laporan_list, laporan_detail
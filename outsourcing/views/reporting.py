from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.conf import settings

from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

from xhtml2pdf import pisa

import io
import os
import calendar

from outsourcing.models import (
    LaporanKegiatan, ItemKegiatan, Absensi,
    StaffSupervisor, SupervisorPerusahaan,
    Perusahaan, JenisJasa
)


def build_jadwal_kalender(item_list, bulan, tahun):
    _, days_in_month = calendar.monthrange(int(tahun), int(bulan))
    jadwal = {}

    for item in item_list:
        area_name = item.laporan.area.nama_area if item.laporan.area else 'Tanpa Area'
        if area_name not in jadwal:
            jadwal[area_name] = {}
        key = item.pk
        if key not in jadwal[area_name]:
            jadwal[area_name][key] = {
                'nama_item'    : item.nama_item,
                'task'         : item.task.nama_task if item.task else '-',
                'sub_area'     : item.sub_area.nama_sub_area if item.sub_area else '-',
                'tanggal_aktif': set(),
            }
        if item.tanggal:
            jadwal[area_name][key]['tanggal_aktif'].add(item.tanggal.day)

    jadwal_final = {}
    for area_name, items_dict in jadwal.items():
        jadwal_final[area_name] = list(items_dict.values())

    return jadwal_final, days_in_month


def build_absensi_kalender(absensi_list, bulan, tahun):
    """
    BUG FIX: Sebelumnya status diambil dengan fallback manual
    ('P' if waktu_masuk else 'A') yang mengabaikan field status_harian
    yang sudah ada di model Absensi.

    Sekarang prioritas pengambilan status:
    1. Gunakan status_harian jika terisi (bukan string kosong)
    2. Fallback ke 'P' jika ada waktu_masuk, 'A' jika tidak ada
       (untuk data lama yang belum punya status_harian)
    """
    _, days_in_month = calendar.monthrange(int(tahun), int(bulan))
    absensi_map = {}

    for ab in absensi_list:
        sid = ab.staff_id
        if sid not in absensi_map:
            absensi_map[sid] = {
                'nama'         : ab.staff.nama_lengkap or ab.staff.username,
                'nik'          : ab.staff.username,
                'foto'         : ab.staff.foto_profil.url if ab.staff.foto_profil else None,
                'jumlah_hadir' : 0,
                'jumlah_alpa'  : 0,
                'jumlah_izin'  : 0,
                'jumlah_cuti'  : 0,
                'jumlah_dokter': 0,  # tambahan untuk DC
                'keterangan'   : '',
            }
        if ab.tanggal:
            # ✅ FIX: Prioritaskan status_harian dari model
            status_harian = getattr(ab, 'status_harian', None)
            if status_harian and status_harian.strip():
                status = status_harian.strip()
            else:
                # Fallback untuk data lama yang belum punya status_harian
                status = 'P' if ab.waktu_masuk else 'A'

            absensi_map[sid][f'd_{ab.tanggal.day}'] = status

            # Rekap jumlah per status
            if status == 'P':
                absensi_map[sid]['jumlah_hadir'] += 1
            elif status == 'A':
                absensi_map[sid]['jumlah_alpa'] += 1
            elif status == 'I':
                absensi_map[sid]['jumlah_izin'] += 1
            elif status == 'L':
                absensi_map[sid]['jumlah_cuti'] += 1
            elif status == 'DC':
                absensi_map[sid]['jumlah_dokter'] += 1

    # Build hari_list per staff agar bisa di-loop di template
    for sid, data in absensi_map.items():
        data['hari_list'] = [data.get(f'd_{d}', '') for d in range(1, days_in_month + 1)]

    return absensi_map, days_in_month


def build_laporan_dengan_jadwal(laporan_list, days_in_month):
    """
    Preprocess laporan + item kegiatan jadi format kalender
    agar template tidak perlu akses dict by variable key.
    """
    result = []
    for laporan in laporan_list:
        items_data = []
        for item in laporan.item_kegiatan.select_related('task', 'sub_area').all():
            hari_list = [''] * days_in_month
            if item.tanggal:
                idx = item.tanggal.day - 1
                if 0 <= idx < days_in_month:
                    hari_list[idx] = '✓'
            items_data.append({
                'nama_item': item.nama_item,
                'sub_area' : item.sub_area.nama_sub_area if item.sub_area else '-',
                'task'     : item.task.nama_task if item.task else '-',
                'frek'     : 'H' if item.jam_mulai else 'M',
                'hari_list': hari_list,
            })
        result.append({
            'laporan'   : laporan,
            'area_nama' : laporan.area.nama_area if laporan.area else '-',
            'supervisor': laporan.supervisor.nama_lengkap or laporan.supervisor.username,
            'items'     : items_data,
        })
    return result


def get_data_laporan_bulanan(perusahaan_id, bulan, tahun, jenis_jasa_id):
    laporan_list = LaporanKegiatan.objects.filter(
        perusahaan_id=perusahaan_id,
        jenis_jasa_id=jenis_jasa_id,
        tanggal_laporan__year=tahun,
        tanggal_laporan__month=bulan,
    ).prefetch_related(
        'item_kegiatan__staff',
        'item_kegiatan__task',
        'item_kegiatan__sub_area',
    ).select_related('supervisor', 'area', 'jenis_jasa')

    supervisor_ids = list(
        laporan_list.values_list('supervisor_id', flat=True).distinct()
    )

    staff_list = StaffSupervisor.objects.filter(
        supervisor_id__in=supervisor_ids,
        is_active=True,
    ).select_related('staff', 'supervisor')

    staff_ids = list(staff_list.values_list('staff_id', flat=True).distinct())

    absensi_list = Absensi.objects.filter(
        staff_id__in=staff_ids,
        tanggal__year=tahun,
        tanggal__month=bulan,
    ).select_related('staff').order_by('staff__nama_lengkap', 'tanggal')

    item_list = ItemKegiatan.objects.filter(
        laporan__in=laporan_list,
    ).prefetch_related('staff').select_related(
        'task', 'sub_area', 'laporan__area'
    ).order_by('laporan__area__nama_area', 'tanggal')

    jadwal_kalender, days_in_month = build_jadwal_kalender(item_list, bulan, tahun)
    absensi_kalender, _            = build_absensi_kalender(absensi_list, bulan, tahun)
    laporan_dengan_jadwal          = build_laporan_dengan_jadwal(laporan_list, days_in_month)

    return {
        'laporan_list'         : laporan_list,
        'staff_list'           : staff_list,
        'absensi_list'         : absensi_list,
        'item_list'            : item_list,
        'supervisor_ids'       : supervisor_ids,
        'staff_ids'            : staff_ids,
        'jadwal_kalender'      : jadwal_kalender,
        'absensi_kalender'     : absensi_kalender,
        'laporan_dengan_jadwal': laporan_dengan_jadwal,
        'days_in_month'        : days_in_month,
        'days_range'           : list(range(1, days_in_month + 1)),
    }


@login_required
def generate_laporan_bulanan(request, perusahaan_id, tahun, bulan, jenis_jasa_id, format):
    try:
        user       = request.user
        perusahaan = get_object_or_404(Perusahaan, pk=perusahaan_id)
        jenis_jasa = get_object_or_404(JenisJasa, pk=jenis_jasa_id)

        if not (user.is_admin or user.is_kepala_supervisor):
            is_assigned = SupervisorPerusahaan.objects.filter(
                supervisor=user,
                perusahaan=perusahaan,
                jenis_jasa=jenis_jasa,
                is_active=True,
            ).exists()
            if not is_assigned:
                return HttpResponse("Tidak punya akses.", status=403)

        data = get_data_laporan_bulanan(perusahaan_id, bulan, tahun, jenis_jasa_id)

        nama_bulan_list = [
            '', 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
            'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
        ]
        nama_bulan = nama_bulan_list[int(bulan)]

        nama_perusahaan_safe = "".join(
            c for c in perusahaan.nama_perusahaan if c.isalnum() or c in (' ', '-', '_')
        ).strip().replace(' ', '_')

        context = {
            **data,
            'perusahaan': perusahaan,
            'jenis_jasa': jenis_jasa,
            'bulan'     : bulan,
            'tahun'     : tahun,
            'nama_bulan': nama_bulan,
            'nama_file' : f"Laporan_{nama_perusahaan_safe}_{nama_bulan}_{tahun}",
        }

        if format == 'pdf':
            return _generate_pdf(request, context)
        elif format == 'word':
            return _generate_word(context)
        else:
            return HttpResponse("Format tidak dikenal. Gunakan 'pdf' atau 'word'.", status=400)

    except Exception as e:
        return HttpResponse(f"Gagal generate laporan: {e}", status=500)


def _fetch_resources(uri, rel):
    if uri.startswith(settings.MEDIA_URL):
        return os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, '').lstrip('/'))
    if uri.startswith(settings.STATIC_URL):
        static_root = getattr(settings, 'STATIC_ROOT', None) or ''
        return os.path.join(static_root, uri.replace(settings.STATIC_URL, '').lstrip('/'))
    return uri


def _generate_pdf(request, context):
    try:
        html_string = render_to_string('laporan_bulanan_pdf.html', context)
        buffer      = io.BytesIO()
        pisa_status = pisa.CreatePDF(
            src=html_string,
            dest=buffer,
            encoding='utf-8',
            link_callback=_fetch_resources,
        )
        if pisa_status.err:
            return HttpResponse(f"Gagal generate PDF: {pisa_status.err}", status=500)
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{context["nama_file"]}.pdf"'
        return response
    except Exception as e:
        return HttpResponse(f"Error PDF: {e}", status=500)


def _generate_word(context):
    try:
        from docx.shared import Mm
        doc = Document()
        for section in doc.sections:
            section.top_margin    = Mm(20)
            section.bottom_margin = Mm(20)
            section.left_margin   = Mm(18)
            section.right_margin  = Mm(18)

        _word_cover(doc, context)
        _word_data_karyawan(doc, context)
        _word_struktur_organisasi(doc, context)
        _word_jadwal(doc, context)
        _word_absensi(doc, context)
        _word_program_pelaksanaan(doc, context)
        _word_foto_progres(doc, context)
        _word_penutup(doc, context)

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        response = HttpResponse(
            buffer,
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        response['Content-Disposition'] = f'attachment; filename="{context["nama_file"]}.docx"'
        return response
    except Exception as e:
        return HttpResponse(f"Error Word: {e}", status=500)


# ──────────────────────────────────────────────────
# WORD HELPERS
# ──────────────────────────────────────────────────

def _add_section_heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    h.alignment = WD_ALIGN_PARAGRAPH.LEFT
    return h


def _add_table_header(table, headers):
    from docx.shared import RGBColor, Pt
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = h
        run = hdr_cells[i].paragraphs[0].runs[0]
        run.bold = True
        run.font.size = Pt(7)
        tc   = hdr_cells[i]._tc
        tcPr = tc.get_or_add_tcPr()
        shd  = OxmlElement('w:shd')
        shd.set(qn('w:val'),   'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'),  '1a3a5c')
        tcPr.append(shd)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)


def _word_cover(doc, ctx):
    from docx.shared import Pt
    doc.add_paragraph()
    t = doc.add_paragraph('LAPORAN BULANAN')
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t.runs[0].bold = True
    t.runs[0].font.size = Pt(18)
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(ctx['perusahaan'].nama_perusahaan + '\n')
    r.bold = True
    r.font.size = Pt(14)
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.add_run(f"Jasa: {ctx['jenis_jasa'].nama_jasa}\n")
    p2.add_run(f"Periode: {ctx['nama_bulan']} {ctx['tahun']}\n")
    p2.add_run(f"\n{ctx['perusahaan'].alamat}")
    doc.add_page_break()


def _word_data_karyawan(doc, ctx):
    _add_section_heading(doc, 'I. DATA KARYAWAN')
    table = doc.add_table(rows=1, cols=5)
    table.style = 'Table Grid'
    _add_table_header(table, ['No', 'Nama', 'NIK', 'Area Tugas', 'Ket'])
    for i, rel in enumerate(ctx['staff_list'], 1):
        row = table.add_row().cells
        row[0].text = str(i)
        row[1].text = rel.staff.nama_lengkap or rel.staff.username
        row[2].text = rel.staff.username
        row[3].text = rel.supervisor.nama_lengkap or '-'
        row[4].text = 'Aktif'
    doc.add_page_break()


def _word_struktur_organisasi(doc, ctx):
    _add_section_heading(doc, 'II. STRUKTUR ORGANISASI')
    table = doc.add_table(rows=1, cols=4)
    table.style = 'Table Grid'
    _add_table_header(table, ['Supervisor', 'Jenis Jasa', 'Jumlah Staff', 'Status'])
    for laporan in ctx['laporan_list']:
        row = table.add_row().cells
        row[0].text = laporan.supervisor.nama_lengkap or laporan.supervisor.username
        row[1].text = laporan.jenis_jasa.nama_jasa
        row[2].text = str(laporan.supervisor.staff_dibawahnya.count())
        row[3].text = 'Aktif'
    doc.add_page_break()


def _word_jadwal(doc, ctx):
    _add_section_heading(doc, 'III. JADWAL DAN PLOTING KERJA')
    days_range      = ctx['days_range']
    jadwal_kalender = ctx['jadwal_kalender']

    for area_name, items in jadwal_kalender.items():
        p = doc.add_paragraph(area_name)
        if p.runs: p.runs[0].bold = True

        cols  = 3 + len(days_range)
        table = doc.add_table(rows=1, cols=cols)
        table.style = 'Table Grid'
        _add_table_header(table, ['No', 'Item', 'Task'] + [str(d) for d in days_range])

        for i, item in enumerate(items, 1):
            row = table.add_row().cells
            row[0].text = str(i)
            row[1].text = item['nama_item']
            row[2].text = item['task']
            for j, day in enumerate(days_range):
                row[3 + j].text = 'A' if day in item['tanggal_aktif'] else ''
        doc.add_paragraph()
    doc.add_page_break()


def _word_absensi(doc, ctx):
    """
    ✅ FIX: Kolom JUMLAH sekarang menampilkan E (hadir), A (alpa), I (izin), L (cuti)
    sesuai data status_harian yang sudah difix di build_absensi_kalender.
    Juga menambahkan kolom DC (surat dokter).
    """
    _add_section_heading(doc, 'IV. ABSENSI')
    days_range       = ctx['days_range']
    absensi_kalender = ctx['absensi_kalender']

    # No | Nama | NIK | hari... | E | A | I | L | DC | Ket
    cols  = 3 + len(days_range) + 5
    table = doc.add_table(rows=1, cols=cols)
    table.style = 'Table Grid'
    _add_table_header(
        table,
        ['No', 'Nama', 'NIK'] + [str(d) for d in days_range] + ['E', 'A', 'I', 'L', 'DC'],
    )

    for i, (staff_id, data) in enumerate(absensi_kalender.items(), 1):
        row = table.add_row().cells
        row[0].text = str(i)
        row[1].text = data['nama']
        row[2].text = data['nik']
        for j, day in enumerate(days_range):
            row[3 + j].text = data.get(f'd_{day}', '')
        base = 3 + len(days_range)
        row[base    ].text = str(data.get('jumlah_hadir',  0))
        row[base + 1].text = str(data.get('jumlah_alpa',   0))
        row[base + 2].text = str(data.get('jumlah_izin',   0))
        row[base + 3].text = str(data.get('jumlah_cuti',   0))
        row[base + 4].text = str(data.get('jumlah_dokter', 0))

    doc.add_paragraph()
    ket = doc.add_paragraph()
    ket.add_run('Keterangan: ').bold = True
    ket.add_run('P=Hadir  L=Cuti  I=Izin  A=Alpa  DC=Surat Dokter')
    doc.add_page_break()


def _word_program_pelaksanaan(doc, ctx):
    _add_section_heading(doc, 'V. PROGRAM DAN PELAKSANAAN PEKERJAAN')
    days_range            = ctx['days_range']
    laporan_dengan_jadwal = ctx['laporan_dengan_jadwal']

    for entry in laporan_dengan_jadwal:
        p = doc.add_paragraph(f"{entry['area_nama']} — Supervisor: {entry['supervisor']}")
        if p.runs: p.runs[0].bold = True

        cols  = 4 + len(days_range)
        table = doc.add_table(rows=1, cols=cols)
        table.style = 'Table Grid'
        _add_table_header(table, ['Object', 'Standar', 'Job', 'Frek'] + [str(d) for d in days_range])

        for item in entry['items']:
            row = table.add_row().cells
            row[0].text = item['nama_item']
            row[1].text = item['sub_area']
            row[2].text = item['task']
            row[3].text = item['frek']
            for j, mark in enumerate(item['hari_list']):
                row[4 + j].text = mark
        doc.add_paragraph()
    doc.add_page_break()


def _word_foto_progres(doc, ctx):
    _add_section_heading(doc, 'VI. FOTO PROGRES')
    current_area = None
    for item in ctx['item_list']:
        if not (item.foto_on_progress or item.foto_after):
            continue
        area_name = item.laporan.area.nama_area if item.laporan.area else 'Tanpa Area'
        if area_name != current_area:
            p = doc.add_paragraph(area_name)
            if p.runs: p.runs[0].bold = True
            current_area = area_name
        doc.add_paragraph(
            f"{item.nama_item}"
            + (f" — {item.tanggal.strftime('%d %B %Y')}" if item.tanggal else "")
        )
        if item.foto_on_progress:
            try:
                doc.add_picture(item.foto_on_progress.path, width=Inches(2.8))
                doc.add_paragraph('On Progress')
            except Exception:
                doc.add_paragraph('[Foto On Progress tidak tersedia]')
        if item.foto_after:
            try:
                doc.add_picture(item.foto_after.path, width=Inches(2.8))
                doc.add_paragraph('After')
            except Exception:
                doc.add_paragraph('[Foto After tidak tersedia]')
        doc.add_paragraph()
    doc.add_page_break()


def _word_penutup(doc, ctx):
    from docx.shared import Pt
    _add_section_heading(doc, 'VII. PENUTUP')
    doc.add_paragraph(
        f"Demikian Laporan Bulanan periode bulan {ctx['nama_bulan']} {ctx['tahun']} ini dibuat "
        f"sebagai bentuk pertanggungjawaban pelaksanaan jasa {ctx['jenis_jasa'].nama_jasa} "
        f"di lingkungan {ctx['perusahaan'].nama_perusahaan}. "
        f"Semua kegiatan telah dilaksanakan sesuai dengan jadwal dan standar yang telah ditetapkan."
    )
    doc.add_paragraph()
    p = doc.add_paragraph(f"{ctx['perusahaan'].alamat or ''}, {ctx['nama_bulan']} {ctx['tahun']}")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    table = doc.add_table(rows=3, cols=3)
    table.style = 'Table Grid'
    supervisor_name = ''
    for laporan in ctx['laporan_list']:
        supervisor_name = laporan.supervisor.nama_lengkap or laporan.supervisor.username
        break
    table.cell(0, 0).text = 'Dibuat oleh,'
    table.cell(0, 1).text = 'Diketahui oleh,'
    table.cell(0, 2).text = 'Disetujui oleh,'
    table.cell(1, 0).text = f'( {supervisor_name} )'
    table.cell(1, 1).text = '( ________________________ )'
    table.cell(1, 2).text = '( ________________________ )'
    table.cell(2, 0).text = f'SPV {ctx["jenis_jasa"].nama_jasa}'
    table.cell(2, 1).text = 'Kepala Supervisor'
    table.cell(2, 2).text = ctx['perusahaan'].nama_perusahaan
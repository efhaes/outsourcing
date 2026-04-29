from __future__ import annotations

from datetime import datetime
from functools import wraps
from typing import Callable

from django.contrib import messages
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from outsourcing.decorators import staff_required
from outsourcing.forms.staff_forms import ItemKegiatanStaffForm
from outsourcing.models import ItemKegiatan


# ---------------------------------------------------------------------------
# Constants — no more magic strings scattered everywhere
# ---------------------------------------------------------------------------

class Status:
    TERJADWAL   = "terjadwal"
    ON_PROGRESS = "on_progress"
    SELESAI     = "selesai"


# ---------------------------------------------------------------------------
# Domain helpers — pure functions, zero side effects, fully testable
# ---------------------------------------------------------------------------

def _is_past_jam_selesai(item: ItemKegiatan) -> bool:
    """Return True kalau waktu sekarang sudah melewati jam_selesai item."""
    if not (item.jam_selesai and item.tanggal):
        return False
    deadline = timezone.make_aware(
        datetime.combine(item.tanggal, item.jam_selesai),
        timezone.get_current_timezone(),
    )
    return timezone.now() >= deadline


def _derive_status(item: ItemKegiatan) -> str:
    """
    Hitung status yang seharusnya berdasarkan state item saat ini.
    Tidak melakukan save — hanya mengembalikan string status.
    """
    if item.foto_after and _is_past_jam_selesai(item):
        return Status.SELESAI
    if item.foto_on_progress or item.jam_mulai:
        return Status.ON_PROGRESS
    return item.status  # tidak berubah


# ---------------------------------------------------------------------------
# Guard decorator — DRY untuk cek item sudah selesai
# ---------------------------------------------------------------------------

def item_not_done(view_fn: Callable) -> Callable:
    """
    Decorator untuk view yang menerima kwarg `pk`.
    Redirect ke list jika item sudah selesai.
    """
    @wraps(view_fn)
    def _wrapper(request: HttpRequest, pk: int, *args, **kwargs):
        item = get_object_or_404(ItemKegiatan, pk=pk, staff=request.user)
        if item.status == Status.SELESAI:
            messages.info(request, "Pekerjaan ini sudah selesai.")
            return redirect("staff_item_list")
        return view_fn(request, *args, item=item, **kwargs)
    return _wrapper


# ---------------------------------------------------------------------------
# Save-type handlers — satu fungsi per aksi, mudah di-test & di-extend
# ---------------------------------------------------------------------------

def _handle_foto_progress(request: HttpRequest, item: ItemKegiatan):
    foto = request.FILES.get("foto_on_progress")
    if not foto:
        messages.warning(request, "Pilih foto terlebih dahulu sebelum menyimpan.")
        return redirect("staff_item_update", pk=item.pk)

    item.foto_on_progress = foto
    if item.status == Status.TERJADWAL:
        item.status = Status.ON_PROGRESS

    item.save(update_fields=["foto_on_progress", "status"])
    messages.success(request, "✓ Foto sedang berjalan berhasil disimpan.")
    return redirect("staff_item_update", pk=item.pk)


def _handle_foto_after(request: HttpRequest, item: ItemKegiatan):
    foto = request.FILES.get("foto_after")
    if not foto:
        messages.warning(request, "Pilih foto terlebih dahulu sebelum menyimpan.")
        return redirect("staff_item_update", pk=item.pk)

    if not _is_past_jam_selesai(item):
        messages.error(
            request,
            f"Belum bisa upload foto 'Setelah Selesai' karena jam selesai "
            f"({item.jam_selesai.strftime('%H:%M')}) belum tiba.",
        )
        return redirect("staff_item_update", pk=item.pk)

    item.foto_after = foto
    item.status = Status.SELESAI
    item.save(update_fields=["foto_after", "status"])
    messages.success(request, "✓ Foto selesai disimpan. Pekerjaan ditandai Selesai.")
    return redirect("staff_item_list")


def _handle_save_all(request: HttpRequest, item: ItemKegiatan):
    form = ItemKegiatanStaffForm(request.POST, request.FILES, instance=item)

    if not form.is_valid():
        return None, form  # signal caller untuk re-render

    updated_item = form.save(commit=False)

    # Tolak foto_after kalau jam_selesai belum tiba
    if form.cleaned_data.get("foto_after") and not _is_past_jam_selesai(updated_item):
        messages.error(
            request,
            f"Belum bisa upload foto 'Setelah Selesai' karena jam selesai "
            f"({updated_item.jam_selesai.strftime('%H:%M')}) belum tiba.",
        )
        return None, form

    updated_item.status = _derive_status(updated_item)
    updated_item.save()
    messages.success(request, f"Pekerjaan \"{updated_item.nama_item}\" berhasil diperbarui.")
    return redirect("staff_item_list"), None


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

@staff_required
def item_list(request: HttpRequest):
    """
    Staff melihat item kegiatan miliknya.
    Flow: Pilih Tahun → Pilih Bulan → Lihat daftar item.
    """
    tahun_dipilih = request.GET.get("tahun", "").strip()
    bulan_dipilih = request.GET.get("bulan", "").strip()
    status        = request.GET.get("status", "").strip()

    base_qs = (
        ItemKegiatan.objects
        .filter(staff=request.user)
        .select_related("laporan__perusahaan", "laporan__area", "sub_area")
        .order_by("-tanggal", "jam_mulai")
    )

    # ── Data untuk card Tahun ─────────────────────────────────────── #
    from django.db.models import Count, Q
    tahun_qs = (
        base_qs
        .values_list("tanggal__year", flat=True)
        .distinct()
        .order_by("tanggal__year")
    )
    tahun_list = []
    for tahun in tahun_qs:
        if tahun:
            total      = base_qs.filter(tanggal__year=tahun).count()
            selesai    = base_qs.filter(tanggal__year=tahun, status="selesai").count()
            tahun_list.append({
                "tahun"  : tahun,
                "total"  : total,
                "selesai": selesai,
            })

    # ── Data untuk card Bulan (jika tahun sudah dipilih) ─────────── #
    NAMA_BULAN = [
        "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember"
    ]
    bulan_list = []
    if tahun_dipilih:
        bulan_qs = (
            base_qs
            .filter(tanggal__year=tahun_dipilih)
            .values_list("tanggal__month", flat=True)
            .distinct()
            .order_by("tanggal__month")
        )
        for bulan in bulan_qs:
            if bulan:
                total   = base_qs.filter(tanggal__year=tahun_dipilih, tanggal__month=bulan).count()
                selesai = base_qs.filter(tanggal__year=tahun_dipilih, tanggal__month=bulan, status="selesai").count()
                bulan_list.append({
                    "bulan"      : bulan,
                    "nama_bulan" : NAMA_BULAN[bulan],
                    "total"      : total,
                    "selesai"    : selesai,
                })

    # ── Daftar item (jika tahun + bulan sudah dipilih) ───────────── #
    item_qs = None
    if tahun_dipilih and bulan_dipilih:
        item_qs = base_qs.filter(
            tanggal__year=tahun_dipilih,
            tanggal__month=bulan_dipilih,
        )
        if status:
            item_qs = item_qs.filter(status=status)

    return render(request, "staff/item/list.html", {
        "tahun_list"    : tahun_list,
        "bulan_list"    : bulan_list,
        "item_list"     : item_qs,
        "tahun_dipilih" : tahun_dipilih,
        "bulan_dipilih" : bulan_dipilih,
        "filter_status" : status,
        "nama_bulan"    : NAMA_BULAN[int(bulan_dipilih)] if bulan_dipilih else "",
        "page_title"    : "Jadwal Pekerjaan Saya",
    })


@staff_required
@item_not_done
def item_update(request: HttpRequest, item: ItemKegiatan):
    """
    Staff mengisi jam, upload foto, dan catatan.
    Status otomatis dihitung oleh _derive_status().

    POST save_type:
        'foto_progress' — simpan foto_on_progress saja
        'foto_after'    — simpan foto_after saja
        'all'           — simpan semua field (default)
    """
    # Dispatch table menggantikan if-elif berantai
    SAVE_HANDLERS: dict[str, Callable] = {
        "foto_progress": _handle_foto_progress,
        "foto_after"   : _handle_foto_after,
    }

    if request.method == "POST":
        save_type = request.POST.get("save_type", "all")
        handler   = SAVE_HANDLERS.get(save_type)

        if handler:
            return handler(request, item)

        # save_type == 'all'
        response, form = _handle_save_all(request, item)
        if response:
            return response
        # form invalid atau error foto_after — re-render dengan form yang ada
    else:
        form = ItemKegiatanStaffForm(instance=item)

    return render(request, "staff/item/update.html", {
        "form"        : form,
        "item"        : item,
        "page_title"  : item.nama_item,
        "disable_save": not _is_past_jam_selesai(item),
    })


@staff_required
def item_update_jam(request: HttpRequest):
    """AJAX view untuk menyimpan jam mulai dan jam selesai."""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Method not allowed"}, status=405)

    item_pk     = request.POST.get("item_pk")
    jam_mulai   = request.POST.get("jam_mulai", "").strip()
    jam_selesai = request.POST.get("jam_selesai", "").strip()

    if not item_pk:
        return JsonResponse({"success": False, "error": "Item ID diperlukan"})

    # ── Validasi: kedua jam wajib diisi ──────────────────────────────────── #
    if not jam_mulai or not jam_selesai:
        return JsonResponse({"success": False, "error": "Jam mulai dan jam selesai wajib diisi"})

    item = get_object_or_404(ItemKegiatan, pk=item_pk, staff=request.user)

    if item.status == Status.SELESAI:
        return JsonResponse({"success": False, "error": "Pekerjaan sudah selesai"})

    # ── Parse ─────────────────────────────────────────────────────────────── #
    try:
        parsed_mulai   = datetime.strptime(jam_mulai,   "%H:%M").time()
        parsed_selesai = datetime.strptime(jam_selesai, "%H:%M").time()
    except ValueError:
        return JsonResponse({"success": False, "error": "Format jam tidak valid (HH:MM)"})

    # ── Validasi urutan jam ───────────────────────────────────────────────── #
    if parsed_selesai <= parsed_mulai:
        return JsonResponse({"success": False, "error": "Jam selesai harus setelah jam mulai"})

    # ── Simpan — hanya field yang relevan ────────────────────────────────── #
    item.jam_mulai   = parsed_mulai
    item.jam_selesai = parsed_selesai
    item.status      = Status.ON_PROGRESS
    item.save(update_fields=["jam_mulai", "jam_selesai", "status"])

    return JsonResponse({
        "success"     : True,
        "redirect_url": f"/staff/item/{item.pk}/update/",
    })
"""
holiday_service.py
Taruh di folder app outsourcing yang sama dengan views.py
"""

import logging
from datetime import date, timedelta

import requests
from django.utils import timezone

from outsourcing.models import HariLiburNasional, CacheMetaLibur

logger = logging.getLogger(__name__)

# API Hari Libur
API_URL = "https://api-hari-libur.vercel.app/api"

# Cache fetch 30 hari
CACHE_EXPIRY = 30


def get_hari_libur_set(tahun: int, bulan: int) -> set:
    """
    Return set of string tanggal libur nasional untuk bulan & tahun tertentu.
    Contoh return:
        {
            '2026-01-01',
            '2026-08-17',
            ...
        }
    """

    if _perlu_fetch(tahun, bulan):
        sukses = _fetch_dan_simpan(tahun, bulan)

        if not sukses:
            logger.warning(
                f"[HolidayService] Gagal fetch API {tahun}-{bulan:02d}. "
                f"Menggunakan cache lama."
            )

    qs = HariLiburNasional.objects.filter(
        tahun=tahun,
        bulan=bulan,
    )

    return {str(item.tanggal) for item in qs}


def _perlu_fetch(tahun: int, bulan: int) -> bool:
    """
    Cek apakah perlu fetch ulang dari API.
    - Belum pernah di-fetch → True
    - Fetch sebelumnya gagal → True (retry)
    - Cache sudah expired (> CACHE_EXPIRY hari) → True
    """

    try:
        meta = CacheMetaLibur.objects.get(
            tahun=tahun,
            bulan=bulan,
        )

        # Kalau fetch sebelumnya gagal → retry
        if not meta.fetch_sukses:
            return True

        # Kalau cache sudah expired
        expired = timezone.now() - meta.last_fetched > timedelta(days=CACHE_EXPIRY)

        return expired

    except CacheMetaLibur.DoesNotExist:
        return True


def _fetch_dan_simpan(tahun: int, bulan: int) -> bool:
    """
    Fetch dari API lalu simpan ke database.

    FIX:
    - Response API berbentuk {"status": "success", "code": 200, "data": [...]}
      bukan langsung array, jadi harus unwrap dengan resp.json().get('data', [])
    - Field tanggal di response adalah 'date', bukan 'holiday_date'
    - Field nama di response adalah 'description', bukan 'holiday_name'
    - Gunakan parameter 'month' agar API sudah filter per bulan (lebih efisien)
    """

    try:
        logger.info(f"[HolidayService] Fetch API {tahun}-{bulan:02d}")

        # ✅ FIX: tambah parameter month agar API filter sendiri per bulan
        resp = requests.get(
            API_URL,
            params={'year': tahun, 'month': bulan},
            timeout=10,
        )

        resp.raise_for_status()

        # ✅ FIX: response dibungkus object {"status":..., "data": [...]}
        # harus ambil dari key 'data', bukan langsung iterasi resp.json()
        response_json = resp.json()
        data = response_json.get('data', [])

        logger.info(f"[HolidayService] Response API: {len(data)} data")

        # Hapus data lama bulan ini sebelum insert baru
        HariLiburNasional.objects.filter(
            tahun=tahun,
            bulan=bulan,
        ).delete()

        bulk = []

        for item in data:
            # ✅ FIX: field yang benar adalah 'date' dan 'description'
            # bukan 'holiday_date' dan 'holiday_name'
            tgl_str = item.get('date')
            nama    = item.get('description')

            if not tgl_str:
                continue

            try:
                tgl = date.fromisoformat(tgl_str)
            except ValueError:
                continue

            # Sudah pakai param month, tapi tetap filter untuk keamanan
            if tgl.month != bulan or tgl.year != tahun:
                continue

            bulk.append(
                HariLiburNasional(
                    tanggal=tgl,
                    nama_libur=nama,
                    tahun=tgl.year,
                    bulan=tgl.month,
                )
            )

        # Simpan bulk ke database
        if bulk:
            HariLiburNasional.objects.bulk_create(
                bulk,
                ignore_conflicts=True,
            )

        # Update cache metadata → sukses
        CacheMetaLibur.objects.update_or_create(
            tahun=tahun,
            bulan=bulan,
            defaults={
                'fetch_sukses': True,
                'last_fetched': timezone.now(),
            },
        )

        logger.info(
            f"[HolidayService] Berhasil simpan "
            f"{len(bulk)} hari libur {tahun}-{bulan:02d}"
        )

        return True

    except requests.exceptions.Timeout:
        logger.error(
            f"[HolidayService] Timeout API {tahun}-{bulan:02d}"
        )

    except requests.exceptions.ConnectionError:
        logger.error(
            f"[HolidayService] Connection Error {tahun}-{bulan:02d}"
        )

    except Exception as e:
        logger.error(
            f"[HolidayService] Error tidak terduga: {str(e)}"
        )

    # Tandai fetch gagal di cache metadata
    try:
        CacheMetaLibur.objects.update_or_create(
            tahun=tahun,
            bulan=bulan,
            defaults={
                'fetch_sukses': False,
                'last_fetched': timezone.now(),
            },
        )
    except Exception:
        pass

    return False
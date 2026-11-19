"""Groq-backed explanations for AirSense charts.

The model receives structured chart data only. It does not run predictions,
change metrics, or determine the AirSense category.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

logger = logging.getLogger(__name__)
BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env", override=False)

DEFAULT_MODEL = "openai/gpt-oss-20b"


class GroqNotConfiguredError(Exception):
    """Raised when GROQ_API_KEY is not configured."""


class GroqExplanationError(Exception):
    """Raised when Groq cannot generate an explanation."""


SYSTEM_PROMPT = """Anda adalah asisten analisis data untuk aplikasi edukasi AirSense.
Tugas Anda hanya menjelaskan grafik berdasarkan data terstruktur yang diberikan.

ATURAN WAJIB:
- Tulis dalam Bahasa Indonesia yang jelas, alami, dan mudah dipahami mahasiswa/pengguna umum.
- Buat 2 sampai 4 kalimat ringkas. Jangan mengulang seluruh tabel.
- Gunakan hanya angka, label, satuan, dan konteks yang terdapat pada data masukan.
- Jangan mengarang angka, penyebab, hubungan sebab-akibat, atau informasi sensor yang tidak diberikan.
- Jangan mengubah, menghitung ulang, atau mengoreksi hasil prediksi maupun metrik.
- Jelaskan bahwa kategori Baik/Sedang/Buruk AirSense bersifat relatif terhadap kuantil data latih, bukan ISPU resmi.
- MAE dan RMSE memiliki satuan target masing-masing; jangan membandingkan besarnya error antarp polutan secara langsung.
- R² menjelaskan proporsi variasi target yang dapat dijelaskan model pada data uji; hindari menyebutnya sebagai persentase akurasi.
- Jangan memberikan diagnosis kesehatan atau menyatakan kondisi udara aman/tidak aman secara medis.
- Jangan menyebut diri Anda sebagai alat ukur. AirSense menghasilkan estimasi model, bukan pembacaan sensor langsung.
- Keluarkan hanya penjelasan, tanpa markdown heading, tanpa daftar, dan tanpa blok JSON.
"""

CHART_TITLES = {
    "prediction_distribution": "Distribusi kategori hasil prediksi empat polutan",
    "r2_comparison": "Perbandingan nilai R-squared empat model regresi",
    "data_split": "Jumlah data latih dan data uji untuk setiap target",
    "feature_usage": "Jumlah fitur masukan yang digunakan setiap model",
}


def generate_chart_explanation(chart_key: str, chart_data: dict) -> tuple[str, str]:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise GroqNotConfiguredError(
            "GROQ_API_KEY belum diatur. Tambahkan kunci Groq ke backend/.env."
        )

    model = os.getenv("GROQ_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    client = Groq(api_key=api_key, timeout=35.0, max_retries=1)
    user_content = {
        "judul_grafik": CHART_TITLES[chart_key],
        "data_grafik": chart_data,
        "instruksi_tambahan": (
            "Jelaskan pola utama yang benar-benar terlihat pada data. "
            "Sebutkan angka penting hanya jika membantu pemahaman."
        ),
    }

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(user_content, ensure_ascii=False),
                },
            ],
            reasoning_effort="low",
            max_completion_tokens=450,
        )
        explanation = (completion.choices[0].message.content or "").strip()
        if not explanation:
            raise GroqExplanationError("Groq mengembalikan penjelasan kosong.")
        return explanation[:4000], model
    except GroqExplanationError:
        raise
    except Exception as exc:  # Provider/network errors are intentionally not exposed to the browser.
        logger.exception("Groq chart explanation failed: %s", type(exc).__name__)
        raise GroqExplanationError(
            "Layanan AI belum dapat menghasilkan penjelasan. Periksa koneksi, model, kuota, dan API key Groq."
        ) from exc

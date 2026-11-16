"""Safe, in-memory extraction for user-provided XFA attachments.

Uploaded content is never saved to the application filesystem and is never executed.
"""
from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import PurePosixPath

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_EXTRACTED_CHARS = 25000
TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".jsx", ".ts", ".tsx", ".css", ".json",
    ".yaml", ".yml", ".toml", ".sql", ".sh", ".java", ".c", ".cpp", ".h",
    ".go", ".rs", ".rb", ".php", ".xml", ".log",
}
IMAGE_TYPES = {
    ".png": ("image/png", b"\x89PNG\r\n\x1a\n"),
    ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
    ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
}
OFFICE_CONTENT = {
    ".docx": "word/document.xml",
    ".pptx": "ppt/presentation.xml",
    ".xlsx": "xl/workbook.xml",
}


def _safe_zip(raw: bytes, expected_member: str) -> zipfile.ZipFile:
    archive = zipfile.ZipFile(io.BytesIO(raw))
    infos = archive.infolist()
    if len(infos) > 300 or sum(item.file_size for item in infos) > 30 * 1024 * 1024:
        archive.close()
        raise ValueError("Office faylının açılmış ölçüsü təhlükəsizlik limitini keçir.")
    for item in infos:
        path = PurePosixPath(item.filename)
        if path.is_absolute() or ".." in path.parts or item.file_size > 8 * 1024 * 1024:
            archive.close()
            raise ValueError("Office faylında təhlükəli və ya həddindən artıq böyük arxiv elementi var.")
    names = {item.filename for item in infos}
    if "[Content_Types].xml" not in names or expected_member not in names:
        archive.close()
        raise ValueError("Fayl düzgün Office sənədi deyil.")
    return archive


def validate_upload(filename: str, raw: bytes) -> tuple[str, str]:
    from werkzeug.utils import secure_filename
    safe_name = secure_filename(str(filename or ""))
    if not safe_name or "." not in safe_name:
        raise ValueError("Fayl adı və formatı müəyyən edilmədi.")
    extension = "." + safe_name.rsplit(".", 1)[-1].lower()
    if not raw:
        raise ValueError("Boş fayl göndərilib.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("Fayl maksimum 8 MB ola bilər.")
    if extension in IMAGE_TYPES:
        mime, signature = IMAGE_TYPES[extension]
        if not raw.startswith(signature):
            raise ValueError("Şəkil faylının məzmunu formatı ilə uyğun gəlmir.")
        return safe_name, mime
    if extension == ".webp":
        if len(raw) < 12 or raw[:4] != b"RIFF" or raw[8:12] != b"WEBP":
            raise ValueError("WebP faylının məzmunu formatı ilə uyğun gəlmir.")
        return safe_name, "image/webp"
    if extension == ".pdf":
        if not raw.startswith(b"%PDF-"):
            raise ValueError("PDF faylının imzası düzgün deyil.")
        return safe_name, "application/pdf"
    if extension in OFFICE_CONTENT:
        with _safe_zip(raw, OFFICE_CONTENT[extension]):
            pass
        return safe_name, "application/vnd.openxmlformats-officedocument"
    if extension == ".csv" or extension in TEXT_EXTENSIONS:
        if b"\x00" in raw[:4096]:
            raise ValueError("Bu fayl mətn formatında deyil.")
        try:
            raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("Mətn faylı UTF-8 formatında olmalıdır.") from exc
        return safe_name, "text/csv" if extension == ".csv" else "text/plain"
    raise ValueError("Dəstəklənməyən format. Şəkil, PDF, DOCX, PPTX, XLSX, CSV, TXT, MD və kod faylları qəbul edilir.")


def extract_text(filename: str, raw: bytes) -> str:
    safe_name, mime = validate_upload(filename, raw)
    extension = "." + safe_name.rsplit(".", 1)[-1].lower()
    if mime.startswith("image/"):
        raise ValueError("Şəkillər mətn çıxarma ilə deyil, görmə modeli ilə analiz olunur.")
    if extension == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("PDF oxuma üçün pypdf paketi quraşdırılmalıdır.") from exc
        reader = PdfReader(io.BytesIO(raw), strict=True)
        if reader.is_encrypted:
            raise ValueError("Şifrəli PDF faylları hələ dəstəklənmir.")
        if len(reader.pages) > 50:
            raise ValueError("PDF maksimum 50 səhifə ola bilər.")
        chunks = [(page.extract_text() or "") for page in reader.pages]
        text = "\n\n".join(chunks)
    elif extension == ".docx":
        try:
            from docx import Document
        except ImportError as exc:
            raise RuntimeError("DOCX oxuma üçün python-docx paketi quraşdırılmalıdır.") from exc
        with _safe_zip(raw, OFFICE_CONTENT[extension]):
            pass
        document = Document(io.BytesIO(raw))
        chunks = [paragraph.text for paragraph in document.paragraphs]
        for table in document.tables[:30]:
            for row in table.rows[:100]:
                chunks.append(" | ".join(cell.text for cell in row.cells[:20]))
        text = "\n".join(chunks)
    elif extension == ".pptx":
        try:
            from pptx import Presentation
        except ImportError as exc:
            raise RuntimeError("PPTX oxuma üçün python-pptx paketi quraşdırılmalıdır.") from exc
        with _safe_zip(raw, OFFICE_CONTENT[extension]):
            pass
        presentation = Presentation(io.BytesIO(raw))
        if len(presentation.slides) > 50:
            raise ValueError("PowerPoint maksimum 50 slayd ola bilər.")
        chunks = []
        for index, slide in enumerate(presentation.slides, start=1):
            slide_text = [shape.text for shape in slide.shapes if getattr(shape, "has_text_frame", False)]
            chunks.append("Slayd " + str(index) + ": " + " | ".join(slide_text))
        text = "\n".join(chunks)
    elif extension == ".xlsx":
        try:
            from openpyxl import load_workbook
        except ImportError as exc:
            raise RuntimeError("XLSX oxuma üçün openpyxl paketi quraşdırılmalıdır.") from exc
        with _safe_zip(raw, OFFICE_CONTENT[extension]):
            pass
        workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        chunks = []
        try:
            for sheet in workbook.worksheets[:10]:
                chunks.append("Vərəq: " + sheet.title)
                for row in sheet.iter_rows(max_row=200, max_col=40, values_only=True):
                    values = ["" if value is None else str(value)[:300] for value in row]
                    chunks.append(" | ".join(values))
        finally:
            workbook.close()
        text = "\n".join(chunks)
    elif extension == ".csv":
        rows = csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
        chunks = []
        for index, row in enumerate(rows):
            if index >= 500:
                chunks.append("[Qalan sətirlər limitə görə kəsildi]")
                break
            chunks.append(" | ".join(str(cell)[:300] for cell in row[:40]))
        text = "\n".join(chunks)
    elif extension == ".json":
        try:
            text = json.dumps(json.loads(raw.decode("utf-8-sig")), ensure_ascii=False, indent=2)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("JSON faylı düzgün formatda deyil.") from exc
    else:
        text = raw.decode("utf-8-sig")
    text = str(text or "").strip()
    if not text:
        raise ValueError("Fayldan oxuna bilən mətn çıxmadı. Skan edilmiş PDF üçün OCR hələ aktiv deyil.")
    return text[:MAX_EXTRACTED_CHARS]

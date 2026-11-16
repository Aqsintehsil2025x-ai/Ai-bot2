import io
import unittest
import zipfile

from xfa_agent.file_inputs import MAX_UPLOAD_BYTES, extract_text, validate_upload


class XFAFileInputTests(unittest.TestCase):
    def test_plain_text_and_json_are_extracted(self):
        name, mime = validate_upload("notes.md", b"# XFA\nHello")
        self.assertEqual(name, "notes.md")
        self.assertEqual(mime, "text/plain")
        self.assertIn("Hello", extract_text("notes.md", b"# XFA\nHello"))
        self.assertIn('"ok": true', extract_text("data.json", b'{"ok":true}'))

    def test_csv_is_bounded_and_readable(self):
        text = extract_text("table.csv", b"name,value\nalpha,1\nbeta,2")
        self.assertIn("alpha | 1", text)

    def test_image_signature_is_checked(self):
        with self.assertRaises(ValueError):
            validate_upload("picture.png", b"not a png")
        self.assertEqual(
            validate_upload("picture.png", b"\x89PNG\r\n\x1a\nimage")[1],
            "image/png",
        )

    def test_audio_signature_is_checked(self):
        self.assertEqual(
            validate_upload("voice.wav", b"RIFF" + b"\x00\x00\x00\x00" + b"WAVEdata")[1],
            "audio/wav",
        )
        with self.assertRaises(ValueError):
            validate_upload("voice.wav", b"not audio")

    def test_unknown_extensions_and_oversized_files_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_upload("payload.exe", b"anything")
        with self.assertRaises(ValueError):
            validate_upload("large.txt", b"a" * (MAX_UPLOAD_BYTES + 1))

    def test_office_archive_requires_expected_document_member(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types/>")
            archive.writestr("word/document.xml", "<document/>")
        self.assertEqual(
            validate_upload("report.docx", stream.getvalue())[1],
            "application/vnd.openxmlformats-officedocument",
        )
        with self.assertRaises(ValueError):
            validate_upload("report.docx", b"not a zip file")


if __name__ == "__main__":
    unittest.main()

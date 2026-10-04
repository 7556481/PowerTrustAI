"""Tiny synthetic_fixture PDFs built only in temporary test directories.

They test extraction mechanics, not visual engineering knowledge or scan quality.
"""
from io import BytesIO


def make_pdf(pages, *, encrypted=False):
    from pypdf import PdfWriter
    from pypdf.generic import (ArrayObject, DictionaryObject, NameObject,
                               NumberObject, DecodedStreamObject)
    writer = PdfWriter()
    writer.add_metadata({"/Title": "synthetic_fixture - program behavior only"})
    for specification in pages:
        page = writer.add_blank_page(width=600, height=800)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"),
                                 NameObject("/BaseFont"): NameObject("/Helvetica")})
        resources = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        if specification == "image":
            image = DecodedStreamObject()
            image.set_data(b"\xff\xff\xff")
            image.update({NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Image"),
                NameObject("/Width"): NumberObject(1), NameObject("/Height"): NumberObject(1),
                NameObject("/ColorSpace"): NameObject("/DeviceRGB"), NameObject("/BitsPerComponent"): NumberObject(8)})
            resources[NameObject("/XObject")] = DictionaryObject({NameObject("/Im1"): writer._add_object(image)})
            content = b"q 200 0 0 200 30 30 cm /Im1 Do Q"
        elif specification == "vector":
            content = b"20 20 100 100 re f"
        elif specification is None:
            content = b""
        else:
            runs = specification if isinstance(specification, list) else [(50, 700 - i * 18, line) for i, line in enumerate(specification.split("\n"))]
            pieces = []
            for x, y, text in runs:
                escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
                pieces.append(f"BT /F1 12 Tf 1 0 0 1 {x} {y} Tm ({escaped}) Tj ET")
            content = "\n".join(pieces).encode("ascii")
        stream = DecodedStreamObject()
        stream.set_data(content)
        page[NameObject("/Resources")] = resources
        page[NameObject("/Contents")] = writer._add_object(stream)
    if encrypted:
        writer.encrypt("synthetic-password")
    stream = BytesIO()
    writer.write(stream)
    return stream.getvalue()

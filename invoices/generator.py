from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET

from django.conf import settings


SPREADSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
ET.register_namespace("", SPREADSHEET_NS)
ET.register_namespace("r", REL_NS)

TEMPLATE_PATH = (
    Path(settings.BASE_DIR)
    / "invoices"
    / "templates"
    / "invoices"
    / "invoice_design.xlsx"
)


def build_invoice_workbook(invoice_data):
    sheet_xml = _render_sheet(invoice_data)
    output = BytesIO()

    with ZipFile(TEMPLATE_PATH, "r") as template, ZipFile(
        output, "w", compression=ZIP_DEFLATED
    ) as generated:
        for item in template.infolist():
            content = (
                sheet_xml
                if item.filename == "xl/worksheets/sheet1.xml"
                else template.read(item.filename)
            )
            generated.writestr(item, content)

    output.seek(0)
    return output


def convert_workbook_to_pdf(workbook, filename):
    converter = shutil.which("soffice") or shutil.which("libreoffice")
    if not converter:
        return None

    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        workbook_path = temp_path / filename
        pdf_path = workbook_path.with_suffix(".pdf")
        workbook.seek(0)
        workbook_path.write_bytes(workbook.read())

        try:
            subprocess.run(
                [
                    converter,
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(temp_path),
                    str(workbook_path),
                ],
                check=True,
                capture_output=True,
                timeout=60,
            )
        except (subprocess.SubprocessError, OSError):
            return None
        if not pdf_path.exists():
            return None
        return BytesIO(pdf_path.read_bytes())


def build_invoice_pdf(invoice_data):
    customer = invoice_data["customer"]
    invoice_date = normalize_invoice_date(invoice_data)
    due_date = invoice_data.get("due_date")
    items = invoice_data["items"]
    subtotal, tax, total = calculate_invoice_totals(invoice_data)
    invoice_number = invoice_data["invoice_number"]

    commands = [
        "BT /F1 18 Tf 50 790 Td (TwinPeaks Investments) Tj ET",
        _pdf_text(50, 765, "Invoice", 16),
        _pdf_text(380, 790, f"No: {invoice_number}", 10),
        _pdf_text(380, 775, f"Date: {invoice_date.isoformat()}", 10),
        _pdf_text(380, 760, f"Due: {due_date.isoformat() if due_date else ''}", 10),
        _pdf_text(50, 725, "Bill To", 12),
        _pdf_text(50, 707, customer["name"], 10),
        _pdf_text(50, 692, customer.get("location", ""), 10),
        _pdf_text(50, 677, customer.get("email", ""), 10),
        _pdf_text(50, 662, customer.get("phone", ""), 10),
        _pdf_text(50, 625, "Qty", 10),
        _pdf_text(105, 625, "Description", 10),
        _pdf_text(360, 625, "Unit Price", 10),
        _pdf_text(470, 625, "Line Total", 10),
        "50 617 m 545 617 l S",
    ]

    y = 595
    for item in items[:15]:
        quantity = Decimal(item["quantity"])
        unit_price = Decimal(item["unit_price"])
        line_total = quantity * unit_price
        commands.extend(
            [
                _pdf_text(50, y, _format_decimal(quantity), 10),
                _pdf_text(105, y, item["description"], 10),
                _pdf_text(360, y, _format_money(unit_price), 10),
                _pdf_text(470, y, _format_money(line_total), 10),
            ]
        )
        y -= 18

    commands.extend(
        [
            "350 170 m 545 170 l S",
            _pdf_text(360, 150, "Subtotal", 10),
            _pdf_text(470, 150, _format_money(subtotal), 10),
            _pdf_text(360, 132, "Tax", 10),
            _pdf_text(470, 132, _format_money(tax), 10),
            _pdf_text(360, 108, "Total", 12),
            _pdf_text(470, 108, _format_money(total), 12),
        ]
    )

    return _build_pdf("\n".join(commands))


def normalize_invoice_date(invoice_data):
    return invoice_data.get("date") or date.today()


def calculate_invoice_totals(invoice_data):
    tax_rate = Decimal(invoice_data.get("tax_rate", Decimal("0.15")))
    subtotal = sum(
        Decimal(item["quantity"]) * Decimal(item["unit_price"])
        for item in invoice_data["items"]
    )
    tax = (subtotal * tax_rate).quantize(Decimal("0.01"))
    total = subtotal + tax
    return subtotal.quantize(Decimal("0.01")), tax, total.quantize(Decimal("0.01"))


def _render_sheet(invoice_data):
    with ZipFile(TEMPLATE_PATH, "r") as template:
        root = ET.fromstring(template.read("xl/worksheets/sheet1.xml"))

    customer = invoice_data["customer"]
    invoice_date = normalize_invoice_date(invoice_data)
    due_date = invoice_data.get("due_date")
    tax_rate = Decimal(invoice_data.get("tax_rate", Decimal("0.15")))
    items = invoice_data["items"]

    subtotal, tax, total = calculate_invoice_totals(invoice_data)

    values = {
        "C7": customer["name"],
        "C8": customer.get("location", ""),
        "C9": customer.get("email", ""),
        "C10": customer.get("phone", ""),
        "E7": invoice_date.isoformat(),
        "E8": invoice_data["invoice_number"],
        "E9": invoice_data.get("customer_id", ""),
        "B14": invoice_data.get("salesperson", ""),
        "C14": invoice_data.get("job", ""),
        "D14": invoice_data.get("payment_terms", ""),
        "E14": due_date.isoformat() if due_date else "",
        "E27": subtotal,
        "E28": tax,
        "E29": total,
    }

    for offset in range(10):
        row = 17 + offset
        if offset < len(items):
            item = items[offset]
            quantity = Decimal(item["quantity"])
            unit_price = Decimal(item["unit_price"])
            values.update(
                {
                    f"B{row}": quantity,
                    f"C{row}": item["description"],
                    f"D{row}": unit_price,
                    f"E{row}": quantity * unit_price,
                }
            )
        else:
            values.update(
                {
                    f"B{row}": "",
                    f"C{row}": "",
                    f"D{row}": "",
                    f"E{row}": "",
                }
            )

    for cell_ref, value in values.items():
        _set_cell_value(root, cell_ref, value)

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _set_cell_value(root, cell_ref, value):
    cell = _find_or_create_cell(root, cell_ref)
    style = cell.attrib.get("s")
    cell.clear()
    cell.attrib["r"] = cell_ref
    if style is not None:
        cell.attrib["s"] = style

    if value == "" or value is None:
        return

    if isinstance(value, Decimal):
        cell.attrib["t"] = "n"
        ET.SubElement(cell, f"{{{SPREADSHEET_NS}}}v").text = _format_decimal(value)
        return

    cell.attrib["t"] = "inlineStr"
    inline_string = ET.SubElement(cell, f"{{{SPREADSHEET_NS}}}is")
    ET.SubElement(inline_string, f"{{{SPREADSHEET_NS}}}t").text = str(value)


def _find_or_create_cell(root, cell_ref):
    sheet_data = root.find(f"{{{SPREADSHEET_NS}}}sheetData")
    row_number = int("".join(character for character in cell_ref if character.isdigit()))
    row_ref = str(row_number)

    row = sheet_data.find(f"{{{SPREADSHEET_NS}}}row[@r='{row_ref}']")
    if row is None:
        row = ET.SubElement(sheet_data, f"{{{SPREADSHEET_NS}}}row", {"r": row_ref})

    cell = row.find(f"{{{SPREADSHEET_NS}}}c[@r='{cell_ref}']")
    if cell is not None:
        return cell

    cell = ET.Element(f"{{{SPREADSHEET_NS}}}c", {"r": cell_ref})
    cells = list(row.findall(f"{{{SPREADSHEET_NS}}}c"))
    insert_at = len(cells)
    target_index = _cell_sort_index(cell_ref)
    for index, existing_cell in enumerate(cells):
        if _cell_sort_index(existing_cell.attrib["r"]) > target_index:
            insert_at = index
            break
    row.insert(insert_at, cell)
    return cell


def _cell_sort_index(cell_ref):
    letters = "".join(character for character in cell_ref if character.isalpha())
    number = int("".join(character for character in cell_ref if character.isdigit()))
    column = 0
    for character in letters:
        column = column * 26 + ord(character.upper()) - ord("A") + 1
    return number, column


def _format_decimal(value):
    normalized = value.quantize(Decimal("0.01"))
    return format(normalized, "f")


def _format_money(value):
    return f"{Decimal(value).quantize(Decimal('0.01')):,.2f}"


def _pdf_text(x, y, text, size=10):
    return f"BT /F1 {size} Tf {x} {y} Td ({_escape_pdf_text(text)}) Tj ET"


def _escape_pdf_text(value):
    text = str(value or "")
    text = text.encode("latin-1", errors="replace").decode("latin-1")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_pdf(content):
    stream = content.encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
    ]

    output = BytesIO()
    output.write(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(output.tell())
        output.write(f"{index} 0 obj\n".encode("ascii"))
        output.write(obj)
        output.write(b"\nendobj\n")

    xref_offset = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.write(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF"
        ).encode("ascii")
    )
    output.seek(0)
    return output

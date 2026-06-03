from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path
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

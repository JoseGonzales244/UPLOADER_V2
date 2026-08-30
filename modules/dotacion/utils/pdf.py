"""
generar_reporte_pdf.py
Genera un reporte PDF formal con los cambios aplicados durante el procesamiento
mensual del equipo de ventas (Fase 3 - Sincronización de dotación).

Secciones:
  1. Cambios de antigüedad
  2. Altas (nuevos ejecutivos)
  3. Bajas / Traslados
  4. Cambios de supervisor
"""

import os
import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)

# ─── Paleta de colores corporativa ────────────────────────────────────────────
INTERBANK_BLUE   = colors.HexColor("#003087")
INTERBANK_TEAL   = colors.HexColor("#00A6A0")
INTERBANK_LIGHT  = colors.HexColor("#E8F4F8")
SECTION_GREEN    = colors.HexColor("#006B54")   # Altas
SECTION_RED      = colors.HexColor("#C0392B")   # Bajas
SECTION_AMBER    = colors.HexColor("#D68910")   # Cambios supervisor
SECTION_BLUE     = colors.HexColor("#1F618D")   # Antigüedad
ROW_ODD          = colors.HexColor("#F5FAFE")
ROW_EVEN         = colors.white
BORDER_GREY      = colors.HexColor("#BDC3C7")
TEXT_DARK        = colors.HexColor("#1A1A2E")

# ─── Nombre del mes en español ────────────────────────────────────────────────
MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}


def _estilos():
    """Devuelve el diccionario de estilos personalizados."""
    base = getSampleStyleSheet()
    estilos = {}

    estilos["titulo"] = ParagraphStyle(
        "titulo",
        parent=base["Title"],
        fontSize=22,
        textColor=INTERBANK_BLUE,
        spaceAfter=4,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
    )
    estilos["subtitulo"] = ParagraphStyle(
        "subtitulo",
        parent=base["Normal"],
        fontSize=11,
        textColor=INTERBANK_TEAL,
        spaceAfter=2,
        fontName="Helvetica",
        alignment=TA_CENTER,
    )
    estilos["meta"] = ParagraphStyle(
        "meta",
        parent=base["Normal"],
        fontSize=9,
        textColor=colors.grey,
        spaceAfter=0,
        fontName="Helvetica",
        alignment=TA_CENTER,
    )
    estilos["seccion"] = ParagraphStyle(
        "seccion",
        parent=base["Heading2"],
        fontSize=12,
        textColor=colors.white,
        fontName="Helvetica-Bold",
        leading=18,
        leftIndent=6,
    )
    estilos["sin_datos"] = ParagraphStyle(
        "sin_datos",
        parent=base["Normal"],
        fontSize=9,
        textColor=colors.grey,
        fontName="Helvetica-Oblique",
        leftIndent=12,
        spaceAfter=8,
    )
    estilos["resumen_num"] = ParagraphStyle(
        "resumen_num",
        parent=base["Normal"],
        fontSize=26,
        textColor=colors.white,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
        leading=28,
    )
    estilos["resumen_label"] = ParagraphStyle(
        "resumen_label",
        parent=base["Normal"],
        fontSize=8,
        textColor=colors.white,
        fontName="Helvetica",
        alignment=TA_CENTER,
        leading=10,
    )
    return estilos


def _tabla_seccion(datos, encabezados, color_header):
    """Construye una Table de reportlab con estilo uniforme."""
    col_widths = _calc_col_widths(encabezados, datos)

    # Estilos de celda para wrapping
    cell_style = ParagraphStyle(
        "cell", fontName="Helvetica", fontSize=8, leading=10, wordWrap="CJK"
    )
    header_style = ParagraphStyle(
        "header", fontName="Helvetica-Bold", fontSize=9, leading=11,
        textColor=colors.white, alignment=TA_CENTER, wordWrap="CJK"
    )

    # Convertir encabezados y datos a Paragraphs para habilitar wrapping
    hdr_row = [Paragraph(str(h), header_style) for h in encabezados]
    body_rows = [
        [Paragraph(str(cell) if cell is not None else "—", cell_style) for cell in row]
        for row in datos
    ]
    all_rows = [hdr_row] + body_rows
    tbl = Table(all_rows, colWidths=col_widths, repeatRows=1)

    style_cmds = [
        # Header
        ("BACKGROUND",    (0, 0), (-1, 0), color_header),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING",    (0, 0), (-1, 0), 6),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        # Body
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("TOPPADDING",    (0, 1), (-1, -1), 4),
        ("ALIGN",         (0, 1), (-1, -1), "LEFT"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        # Grid
        ("GRID",          (0, 0), (-1, -1), 0.4, BORDER_GREY),
        ("LINEBELOW",     (0, 0), (-1, 0), 1, color_header),
    ]
    # Zebra stripes
    for i in range(1, len(all_rows)):
        bg = ROW_ODD if i % 2 == 1 else ROW_EVEN
        style_cmds.append(("BACKGROUND", (0, i), (-1, i), bg))

    tbl.setStyle(TableStyle(style_cmds))
    return tbl


def _calc_col_widths(headers, rows):
    """Distribuye anchos de columna proporcionalmente según el tipo de campo."""
    usable_width = A4[0] - 3 * cm   # márgenes izq + der

    # Proporciones relativas por tipo de encabezado
    WEIGHT_MAP = {
        "hoja":                  1.0,
        "registro":              1.2,
        "colaborador":           3.5,
        "nombre":                3.5,
        "anterior":              1.2,
        "nuevo":                 1.2,
        "supervisor asignado":   3.0,
        "supervisor anterior":   3.0,
        "supervisor nuevo":      3.0,
        "estado anterior":       1.5,
        "estado aplicado":       2.2,
    }
    weights = []
    for h in headers:
        key = str(h).lower().strip()
        weights.append(WEIGHT_MAP.get(key, 2.0))

    total = sum(weights)
    return [usable_width * (w / total) for w in weights]


def _card_resumen(story, seniority_changes, added_advisors, status_changes, supervisor_changes, estilos):
    """Tarjetas de resumen ejecutivo en la parte superior."""
    totales = [
        (len(seniority_changes), "CAMBIOS\nANTIGÜEDAD",  SECTION_BLUE),
        (len(added_advisors),    "ALTAS\nNUEVAS",         SECTION_GREEN),
        (len(status_changes),    "BAJAS /\nTRASLADOS",    SECTION_RED),
        (len(supervisor_changes),"CAMBIOS\nSUPERVISOR",   SECTION_AMBER),
    ]

    celdas = []
    for num, label, color in totales:
        celda = [
            Paragraph(str(num), estilos["resumen_num"]),
            Paragraph(label, estilos["resumen_label"]),
        ]
        celdas.append(celda)

    tbl_data = [celdas]
    col_w = (A4[0] - 3 * cm) / 4

    tbl = Table(tbl_data, colWidths=[col_w] * 4)
    style_cmds = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                  ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                  ("TOPPADDING",    (0, 0), (-1, -1), 14),
                  ("ROUNDEDCORNERS", [6])]
    for idx, (_, _, color) in enumerate(totales):
        style_cmds.append(("BACKGROUND", (idx, 0), (idx, 0), color))
        if idx < 3:
            style_cmds.append(("LINEAFTER", (idx, 0), (idx, 0), 2, colors.white))
    tbl.setStyle(TableStyle(style_cmds))

    story.append(tbl)
    story.append(Spacer(1, 0.5 * cm))


def _seccion_titulo(story, titulo, color, estilos):
    """Barra de título de sección con color de fondo."""
    p = Paragraph(titulo, estilos["seccion"])
    tbl = Table([[p]], colWidths=[A4[0] - 3 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), color),
        ("ROUNDEDCORNERS", [4]),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 0.25 * cm))


def _footer_canvas(canvas_obj, doc):
    """Pie de página con número de página y fecha."""
    canvas_obj.saveState()
    canvas_obj.setFont("Helvetica", 7)
    canvas_obj.setFillColor(colors.grey)
    page_num = canvas_obj.getPageNumber()
    texto = f"Reporte generado el {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')} — Pág. {page_num}"
    canvas_obj.drawRightString(A4[0] - 1.5 * cm, 1 * cm, texto)
    canvas_obj.drawString(1.5 * cm, 1 * cm, "Equipo de Calidad Televentas — Interbank")
    canvas_obj.setStrokeColor(BORDER_GREY)
    canvas_obj.line(1.5 * cm, 1.4 * cm, A4[0] - 1.5 * cm, 1.4 * cm)
    canvas_obj.restoreState()


def generar_pdf(
    output_path: str,
    year: int,
    month: int,
    seniority_changes: list,
    added_advisors: list,
    status_changes: list,
    supervisor_changes: list,
):
    """
    Genera el PDF de cambios mensuales.

    Parámetros
    ----------
    output_path       : ruta de salida del PDF
    year / month      : mes de proceso
    seniority_changes : [(hoja, reg, nombre, old_ant, new_ant), ...]
    added_advisors    : [(hoja, reg, nombre, supervisor), ...]
    status_changes    : [(hoja, reg, nombre, antes, estado), ...]
    supervisor_changes: [(hoja, reg, nombre, old_super, new_super), ...]
    """
    mes_str = f"{MESES_ES.get(month, str(month))} {year}"
    estilos = _estilos()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=2 * cm,
        title=f"Reporte Dotación {mes_str}",
        author="Sistema de Dotación Mensual — Calidad Televentas",
    )

    story = []

    # ── Encabezado ─────────────────────────────────────────────────────────────
    story.append(Paragraph(
        "INTERBANK — CALIDAD TELEVENTAS", estilos["subtitulo"]
    ))
    story.append(Paragraph(
        f"Reporte de Actualización de Dotación", estilos["titulo"]
    ))
    story.append(Paragraph(mes_str, estilos["subtitulo"]))
    story.append(Spacer(1, 0.15 * cm))
    story.append(HRFlowable(width="100%", thickness=2, color=INTERBANK_TEAL, spaceAfter=0.3 * cm))
    story.append(Paragraph(
        f"Generado el {datetime.datetime.now().strftime('%d de %B de %Y a las %H:%M')}",
        estilos["meta"]
    ))
    story.append(Spacer(1, 0.4 * cm))

    # ── Tarjetas resumen ───────────────────────────────────────────────────────
    _card_resumen(story, seniority_changes, added_advisors, status_changes, supervisor_changes, estilos)

    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_GREY, spaceAfter=0.4 * cm))

    # ── 1. Cambios de Antigüedad ───────────────────────────────────────────────
    _seccion_titulo(story, "1.  Cambios de Antigüedad", SECTION_BLUE, estilos)
    if seniority_changes:
        encabezados = ["Hoja", "Registro", "Colaborador", "Anterior", "Nuevo"]
        datos = [
            [sn, reg, nombre or "—", str(old), str(new)]
            for sn, reg, nombre, old, new in seniority_changes
        ]
        story.append(_tabla_seccion(datos, encabezados, SECTION_BLUE))
    else:
        story.append(Paragraph("Sin cambios de antigüedad en este período.", estilos["sin_datos"]))
    story.append(Spacer(1, 0.5 * cm))

    # ── 2. Altas ───────────────────────────────────────────────────────────────
    _seccion_titulo(story, "2.  Altas — Nuevos Ejecutivos", SECTION_GREEN, estilos)
    if added_advisors:
        encabezados = ["Hoja", "Registro", "Colaborador", "Supervisor Asignado"]
        datos = [
            [sn, reg, nombre or "—", sup or "—"]
            for sn, reg, nombre, sup in added_advisors
        ]
        story.append(_tabla_seccion(datos, encabezados, SECTION_GREEN))
    else:
        story.append(Paragraph("Sin nuevas altas en este período.", estilos["sin_datos"]))
    story.append(Spacer(1, 0.5 * cm))

    # ── 3. Bajas / Traslados / Vacaciones ─────────────────────────────────────
    _seccion_titulo(story, "3.  Bajas, Traslados y Ausencias Totales", SECTION_RED, estilos)
    if status_changes:
        encabezados = ["Hoja", "Registro", "Colaborador", "Estado Anterior", "Estado Aplicado"]
        datos = [
            [sn, reg, nombre or "—", str(old), str(nuevo)]
            for sn, reg, nombre, old, nuevo in status_changes
        ]
        story.append(_tabla_seccion(datos, encabezados, SECTION_RED))
    else:
        story.append(Paragraph("Sin bajas, traslados ni ausencias totales en este período.", estilos["sin_datos"]))
    story.append(Spacer(1, 0.5 * cm))

    # ── 4. Cambios de Supervisor ───────────────────────────────────────────────
    _seccion_titulo(story, "4.  Cambios de Supervisor", SECTION_AMBER, estilos)
    if supervisor_changes:
        encabezados = ["Hoja", "Registro", "Colaborador", "Supervisor Anterior", "Supervisor Nuevo"]
        datos = [
            [sn, reg, nombre or "—", str(old) if old else "—", str(new)]
            for sn, reg, nombre, old, new in supervisor_changes
        ]
        story.append(_tabla_seccion(datos, encabezados, SECTION_AMBER))
    else:
        story.append(Paragraph("Sin cambios de supervisor en este período.", estilos["sin_datos"]))

    # ── Build ──────────────────────────────────────────────────────────────────
    doc.build(story, onFirstPage=_footer_canvas, onLaterPages=_footer_canvas)
    print(f"  PDF generado: {output_path}")


# ── Ejecución standalone (para re-generar sin correr el pipeline completo) ────
if __name__ == "__main__":
    import json, sys
    # Uso: python generar_reporte_pdf.py <json_data_file>
    if len(sys.argv) < 2:
        print("Uso: python generar_reporte_pdf.py <archivo_datos.json>")
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    generar_pdf(
        output_path=data.get("output_path", "Reporte_Dotacion.pdf"),
        year=data["year"],
        month=data["month"],
        seniority_changes=[tuple(x) for x in data.get("seniority_changes", [])],
        added_advisors=[tuple(x) for x in data.get("added_advisors", [])],
        status_changes=[tuple(x) for x in data.get("status_changes", [])],
        supervisor_changes=[tuple(x) for x in data.get("supervisor_changes", [])],
    )

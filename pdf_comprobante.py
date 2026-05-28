# -*- coding: utf-8 -*-
"""Comprobante PDF de registro ciudadano (paleta MMQEP + logo opcional)."""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

MMQ_BLUE = colors.HexColor("#003366")
MMQ_BLUE_LIGHT = colors.HexColor("#0a4878")
MUTED = colors.HexColor("#5b6675")
BORDER = colors.HexColor("#cbd5e1")
LOGO_URL = (
    "https://mercadomayorista.quito.gob.ec/wp-content/uploads/2024/08/logo_blanco_smallerc.webp"
)


def _esc_xml(txt):
    if txt is None:
        return ""
    s = str(txt).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return s.replace("\n", "<br/>")


def _fmt_date(d):
    if d is None:
        return "—"
    if hasattr(d, "strftime"):
        return d.strftime("%d/%m/%Y")
    return str(d)


def _fmt_time(t):
    if t is None:
        return "—"
    if hasattr(t, "strftime"):
        return t.strftime("%H:%M")
    return str(t)


def _fmt_dt(dt):
    if dt is None:
        return "—"
    if hasattr(dt, "strftime"):
        return dt.strftime("%d/%m/%Y %H:%M")
    return str(dt)


def _cargar_logo(max_ancho_cm=5.5, max_alto_cm=1.6):
    """Devuelve flowable Image o None si falla la descarga o el formato."""
    try:
        import urllib.request

        from PIL import Image as PILImage
        from reportlab.lib.utils import ImageReader
    except Exception:
        return None

    try:
        req = urllib.request.Request(LOGO_URL, headers={"User-Agent": "MMQEP-PortalDenuncias/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read()
        if not raw:
            return None
        pil = PILImage.open(BytesIO(raw)).convert("RGBA")
        bio = BytesIO()
        pil.save(bio, format="PNG")
        bio.seek(0)
        ir = ImageReader(bio)
        w, h = ir.getSize()
        esc = min((max_ancho_cm * cm) / float(w), (max_alto_cm * cm) / float(h), 1.0)
        nw, nh = w * esc, h * esc
        bio.seek(0)
        return Image(ImageReader(bio), width=nw, height=nh)
    except Exception:
        return None


def _pair_table(rows, col_widths, styles):
    """Tabla etiqueta | valor con borde suave."""
    data = []
    for lab, val in rows:
        data.append(
            [
                Paragraph(_esc_xml(lab), styles["label"]),
                Paragraph(_esc_xml(val if val is not None else "—"), styles["value"]),
            ]
        )
    t = Table(data, colWidths=col_widths)
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, BORDER),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
            ]
        )
    )
    return t


def construir_pdf_comprobante_denuncia(row, nombres_adjuntos=None):
    """
    row: dict con columnas de denuncias (claves como retorna PyMySQL DictCursor).
    nombres_adjuntos: lista de strings (nombre_original de archivos).
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
        title="Comprobante de denuncia",
    )
    styles = getSampleStyleSheet()
    st_title = ParagraphStyle(
        "hdrTitle",
        parent=styles["Heading1"],
        fontSize=14,
        textColor=colors.white,
        spaceAfter=4,
        leading=18,
    )
    st_codigo = ParagraphStyle(
        "codigo",
        parent=styles["Normal"],
        fontSize=18,
        textColor=MMQ_BLUE,
        fontName="Helvetica-Bold",
        spaceBefore=10,
        spaceAfter=6,
    )
    st_h2 = ParagraphStyle(
        "h2",
        parent=styles["Heading2"],
        fontSize=11,
        textColor=MMQ_BLUE_LIGHT,
        spaceBefore=12,
        spaceAfter=6,
    )
    st_label = ParagraphStyle(
        "lab",
        parent=styles["Normal"],
        fontSize=9,
        textColor=MUTED,
        fontName="Helvetica-Bold",
    )
    st_value = ParagraphStyle("val", parent=styles["Normal"], fontSize=10, textColor=colors.black)
    st_small = ParagraphStyle(
        "small",
        parent=styles["Normal"],
        fontSize=8,
        textColor=MUTED,
        leading=11,
    )

    flow = []
    logo = _cargar_logo()

    hdr_cells = []
    if logo:
        hdr_cells.append(logo)
    else:
        hdr_cells.append(Paragraph(_esc_xml("MMQEP"), st_title))
    titulo_txt = (
        "<b>Comprobante de registro</b><br/>"
        "<font size='9' color='#e2e8f0'>Mercado Mayorista Quitumbe — MMQEP</font>"
    )
    hdr_cells.append(Paragraph(titulo_txt, st_title))

    tw = doc.width
    if logo:
        lw = logo.drawWidth + 0.4 * cm
        hdr_tbl = Table([[hdr_cells[0], hdr_cells[1]]], colWidths=[lw, tw - lw])
    else:
        hdr_tbl = Table([[hdr_cells[0], hdr_cells[1]]], colWidths=[3 * cm, tw - 3 * cm])

    hdr_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), MMQ_BLUE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    flow.append(hdr_tbl)
    flow.append(Spacer(1, 0.35 * cm))

    cod = row.get("codigo") or "—"
    flow.append(Paragraph(_esc_xml("Código de seguimiento: {0}".format(cod)), st_codigo))

    es_anon = bool(row.get("es_anonima"))
    tipo_reg = row.get("tipo_registro") or "denuncia"

    den_rows = [
        ("Tipo de registro", str(tipo_reg).capitalize()),
        ("Registro anónimo", "Sí" if es_anon else "No"),
    ]
    if not es_anon:
        den_rows.extend(
            [
                ("Nombres y apellidos", row.get("nombres_denunciante")),
                ("Cédula o RUC", row.get("identificacion_denunciante")),
                ("Teléfono", row.get("telefono_denunciante")),
                ("Correo electrónico", row.get("correo_denunciante")),
            ]
        )

    den_rows.extend(
        [
            ("Categoría", row.get("categoria")),
            ("Subcategoría", row.get("subcategoria")),
            ("Prioridad", row.get("prioridad")),
            ("Estado al registro", row.get("estado")),
            ("Ubicación / lugar", row.get("ubicacion")),
            ("Fecha del hecho", _fmt_date(row.get("fecha_hecho"))),
            ("Hora del hecho (aprox.)", _fmt_time(row.get("hora_hecho"))),
            ("Involucrado (referencia)", row.get("involucrado")),
            ("Fecha y hora de registro en el sistema", _fmt_dt(row.get("fecha_creacion"))),
        ]
    )

    flow.append(Paragraph(_esc_xml("Datos del caso"), st_h2))
    cw = doc.width
    flow.append(
        _pair_table(
            den_rows,
            [5.2 * cm, cw - 5.2 * cm],
            {"label": st_label, "value": st_value},
        )
    )

    flow.append(Spacer(1, 0.25 * cm))
    flow.append(Paragraph(_esc_xml("Descripción detallada"), st_h2))
    desc = row.get("descripcion") or "—"
    flow.append(
        Table(
            [[Paragraph(_esc_xml(desc), st_value)]],
            colWidths=[cw],
            style=TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.75, BORDER),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            ),
        )
    )

    nombres_adjuntos = nombres_adjuntos or []
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(Paragraph(_esc_xml("Evidencias adjuntas al momento del registro"), st_h2))
    if nombres_adjuntos:
        lista_txt = "<br/>".join(_esc_xml(n) for n in nombres_adjuntos)
        flow.append(Paragraph(lista_txt, st_value))
    else:
        flow.append(Paragraph(_esc_xml("No se adjuntaron archivos."), st_value))

    flow.append(Spacer(1, 0.6 * cm))
    flow.append(
        Paragraph(
            _esc_xml(
                "Conserve este documento y su código de seguimiento. "
                "Para consultar el estado del trámite use la opción «Consultar estado» en el portal de denuncias MMQEP."
            ),
            st_small,
        )
    )

    doc.build(flow)
    data = buf.getvalue()
    buf.close()
    return data

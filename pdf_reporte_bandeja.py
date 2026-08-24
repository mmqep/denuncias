# -*- coding: utf-8 -*-
"""Reportes PDF por expediente (interno completo / externo solo gestión ciudadana)."""
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from pdf_comprobante import BORDER, MMQ_BLUE, MMQ_BLUE_LIGHT, MUTED, _cargar_logo, _esc_xml, _fmt_dt


def _truncate(s, max_len=900):
    if s is None:
        return ""
    t = str(s).strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 3] + "..."


def construir_pdf_reporte_bandeja(
    denuncias,
    seguimientos_por_denuncia_id,
    *,
    titulo_principal,
    aviso_confidencialidad,
    generado_por,
    texto_filtros,
    fecha_emision,
    modo_externo=False,
    etiqueta_contexto=None,
):
    """
    denuncias: lista de dicts (id, codigo, estado, prioridad, categoria, subcategoria, area_nombre,
               asignado, fecha_creacion, es_anonima, ubicacion, descripcion opcional).
    seguimientos_por_denuncia_id: dict[int, list[dict]] cada dict con fecha_creacion, usuario_nombre,
               area_nombre, accion, estado_anterior, estado_nuevo, observacion.
    aviso_confidencialidad: texto legal / de uso (interno vs externo).
    modo_externo: si True, tabla de historial solo con columnas aptas para entrega al ciudadano.
    etiqueta_contexto: texto de la etiqueta en metadatos (por defecto «Filtros aplicados en bandeja»).
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.4 * cm,
        rightMargin=1.4 * cm,
        topMargin=1.1 * cm,
        bottomMargin=1.1 * cm,
        title=titulo_principal[:120],
    )
    styles = getSampleStyleSheet()
    st_title = ParagraphStyle(
        "rbTitle",
        parent=styles["Heading1"],
        fontSize=13,
        textColor=colors.white,
        spaceAfter=2,
        leading=16,
    )
    st_h2 = ParagraphStyle(
        "rbH2",
        parent=styles["Heading2"],
        fontSize=11,
        textColor=MMQ_BLUE_LIGHT,
        spaceBefore=10,
        spaceAfter=5,
    )
    st_h3 = ParagraphStyle(
        "rbH3",
        parent=styles["Normal"],
        fontSize=10,
        textColor=MMQ_BLUE,
        fontName="Helvetica-Bold",
        spaceBefore=6,
        spaceAfter=4,
    )
    st_norm = ParagraphStyle("rbN", parent=styles["Normal"], fontSize=9, textColor=colors.black, leading=11)
    st_small = ParagraphStyle("rbS", parent=styles["Normal"], fontSize=8, textColor=MUTED, leading=10)
    st_warn = ParagraphStyle(
        "rbW",
        parent=styles["Normal"],
        fontSize=8.5,
        textColor=colors.HexColor("#92400e"),
        leading=12,
        spaceBefore=4,
        spaceAfter=6,
    )

    flow = []
    logo = _cargar_logo()
    tw = doc.width
    titulo_hdr = (
        "<b>{}</b><br/><font size='8' color='#e2e8f0'>"
        "Mercado Mayorista Quitumbe — MMQEP · Sistema de denuncias y quejas</font>"
    ).format(_esc_xml(titulo_principal))
    if logo:
        lw = logo.drawWidth + 0.35 * cm
        hdr_tbl = Table([[logo, Paragraph(titulo_hdr, st_title)]], colWidths=[lw, tw - lw])
    else:
        hdr_tbl = Table(
            [[Paragraph("<b>MMQEP</b>", st_title), Paragraph(titulo_hdr, st_title)]],
            colWidths=[2.8 * cm, tw - 2.8 * cm],
        )
    hdr_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), MMQ_BLUE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    flow.append(hdr_tbl)
    flow.append(Spacer(1, 0.3 * cm))

    ctx_lab = etiqueta_contexto or "Filtros aplicados en bandeja"
    meta_lines = [
        "<b>Fecha y hora de emisión:</b> {}".format(_esc_xml(fecha_emision)),
        "<b>Generado por:</b> {}".format(_esc_xml(generado_por or "—")),
        "<b>{}:</b> {}".format(
            _esc_xml(ctx_lab),
            _esc_xml(texto_filtros or "—"),
        ),
    ]
    flow.append(Paragraph("<br/>".join(meta_lines), st_small))
    flow.append(Spacer(1, 0.2 * cm))
    flow.append(Paragraph(_esc_xml(aviso_confidencialidad), st_warn))
    flow.append(Spacer(1, 0.25 * cm))
    if len(denuncias) == 1:
        flow.append(Paragraph(_esc_xml("Documento referido a un único expediente."), st_h2))
    else:
        flow.append(
            Paragraph(
                _esc_xml("Expedientes incluidos en este documento: {}".format(len(denuncias))),
                st_h2,
            )
        )

    if not denuncias:
        flow.append(Paragraph(_esc_xml("No hay expedientes que coincidan con los filtros."), st_norm))
        doc.build(flow)
        out = buf.getvalue()
        buf.close()
        return out

    for idx, row in enumerate(denuncias):
        if idx > 0:
            flow.append(PageBreak())

        did = int(row["id"])
        cod = row.get("codigo") or "—"
        flow.append(Paragraph(_esc_xml("Expediente {}".format(cod)), st_h3))

        resumen = [
            ("Estado", row.get("estado")),
            ("Rubro / subcategoría", row.get("subcategoria") or row.get("categoria")),
            ("Área institucional", row.get("area_nombre") or "—"),
            ("Responsable asignado", row.get("asignado") or "—"),
            ("Registro ciudadano", "Anónimo" if row.get("es_anonima") else "Con datos"),
            ("Ingreso al sistema", _fmt_dt(row.get("fecha_creacion"))),
        ]
        if not modo_externo:
            resumen.append(("Ubicación referida", row.get("ubicacion") or "—"))
        if not modo_externo and row.get("descripcion"):
            resumen.append(("Descripción (extracto)", _truncate(row.get("descripcion"), 480)))

        tdata = [[Paragraph(_esc_xml("<b>{}</b>".format(k)), st_small), Paragraph(_esc_xml(str(v or "—")), st_norm)] for k, v in resumen]
        t = Table(tdata, colWidths=[4.2 * cm, tw - 4.2 * cm])
        t.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.35, BORDER),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
                ]
            )
        )
        flow.append(t)
        flow.append(Spacer(1, 0.15 * cm))

        segs = seguimientos_por_denuncia_id.get(did) or []
        if modo_externo:
            hist_tit = "Gestiones comunicadas al ciudadano en este documento ({})".format(len(segs))
        else:
            hist_tit = "Historial completo en este documento ({})".format(len(segs))
        flow.append(Paragraph(_esc_xml(hist_tit), st_h2))

        if not segs:
            msg = (
                "Sin gestiones registradas para el ciudadano en este expediente."
                if modo_externo
                else "Sin movimientos en el alcance de este reporte."
            )
            flow.append(Paragraph(_esc_xml(msg), st_norm))
            flow.append(Spacer(1, 0.35 * cm))
            continue

        # Tabla de historial
        w = tw
        if modo_externo:
            hdr = ["Fecha", "Referencia institucional", "Gestión comunicada al ciudadano"]
            cw = [2.6 * cm, 4.5 * cm, w - 7.1 * cm]
            trows = [[Paragraph(_esc_xml(h), st_small) for h in hdr]]
            for s in segs:
                ref = "MMQEP"
                parts = []
                if s.get("area_nombre"):
                    parts.append(str(s.get("area_nombre")))
                if s.get("usuario_nombre"):
                    parts.append(str(s.get("usuario_nombre")))
                if parts:
                    ref = " · ".join(parts)
                obs = _truncate(s.get("observacion") or "—", 2000)
                trows.append(
                    [
                        Paragraph(_esc_xml(_fmt_dt(s.get("fecha_creacion"))), st_norm),
                        Paragraph(_esc_xml(ref), st_norm),
                        Paragraph(_esc_xml(obs), st_norm),
                    ]
                )
        else:
            hdr = ["Fecha", "Usuario", "Área", "Acción", "Estados", "Detalle"]
            cw = [2.3 * cm, 2.5 * cm, 2.2 * cm, 2.4 * cm, 2.5 * cm, w - 9.9 * cm]
            trows = [[Paragraph(_esc_xml(h), st_small) for h in hdr]]
            for s in segs:
                est = ""
                if s.get("estado_anterior") or s.get("estado_nuevo"):
                    est = "{} → {}".format(s.get("estado_anterior") or "—", s.get("estado_nuevo") or "—")
                obs = _truncate(s.get("observacion") or "—", 1200)
                trows.append(
                    [
                        Paragraph(_esc_xml(_fmt_dt(s.get("fecha_creacion"))), st_norm),
                        Paragraph(_esc_xml(s.get("usuario_nombre") or "—"), st_norm),
                        Paragraph(_esc_xml(s.get("area_nombre") or "—"), st_norm),
                        Paragraph(_esc_xml(s.get("accion") or "—"), st_norm),
                        Paragraph(_esc_xml(est), st_norm),
                        Paragraph(_esc_xml(obs), st_norm),
                    ]
                )
        ht = Table(trows, repeatRows=1, colWidths=cw)
        ht.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), MMQ_BLUE),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.35, BORDER),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        flow.append(ht)
        flow.append(Spacer(1, 0.45 * cm))

    flow.append(Spacer(1, 0.3 * cm))
    flow.append(
        Paragraph(
            _esc_xml(
                "Documento generado electrónicamente desde el sistema MMQEP. "
                "La información debe manejarse conforme a la normativa de protección de datos personales "
                "y a las políticas institucionales."
            ),
            st_small,
        )
    )

    doc.build(flow)
    out = buf.getvalue()
    buf.close()
    return out


_SELLO_URL = (
    "https://mercadomayorista.quito.gob.ec"
    "/wp-content/uploads/2026/06/Recurso-2PC-MAYORISTA-scaled.webp"
)


def _cargar_sello(max_cm=2.2):
    """Descarga el sello institucional MMQEP y lo devuelve como Image de ReportLab."""
    try:
        import urllib.request
        from PIL import Image as PILImage
        from reportlab.lib.utils import ImageReader
        req = urllib.request.Request(_SELLO_URL, headers={"User-Agent": "MMQEP-PortalDenuncias/1.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            raw = resp.read()
        pil = PILImage.open(BytesIO(raw)).convert("RGBA")
        bio = BytesIO()
        pil.save(bio, format="PNG")
        bio.seek(0)
        ir = ImageReader(bio)
        w, h = ir.getSize()
        esc = min((max_cm * cm) / float(w), (max_cm * cm) / float(h), 1.0)
        bio.seek(0)
        return Image(ImageReader(bio), width=w * esc, height=h * esc)
    except Exception:
        return None


_TILE_SERVERS = [
    "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
    "https://b.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
    "https://maps.wikimedia.org/osm-intl/{z}/{x}/{y}.png",
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
]

_pdf_log = __import__("logging").getLogger("mmqep.pdf")


def _fetch_tile(z, x, y):
    """Intenta descargar un tile de múltiples servidores. Devuelve bytes o None."""
    import urllib.request
    headers = {"User-Agent": "MMQEP-PortalDenuncias/1.0 (denuncias.mmqep.gob.ec)"}
    for tmpl in _TILE_SERVERS:
        url = tmpl.format(z=z, x=x, y=y)
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = resp.read()
            if data and len(data) > 200:
                return data
        except Exception:
            continue
    return None


def _cargar_mapa_osm(lat, lon, zoom=16):
    """
    Compone una cuadrícula 3×3 de tiles centrada en lat/lon con un marcador rojo.
    Devuelve Image de ReportLab o None si no se puede descargar ningún tile.
    """
    try:
        import math
        from PIL import Image as PILImage, ImageDraw
        from reportlab.lib.utils import ImageReader

        n = 2.0 ** zoom
        cx = int((float(lon) + 180.0) / 360.0 * n)
        lat_r = math.radians(float(lat))
        cy = int((1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n)

        TILE_PX = 256
        GRID = 3
        canvas = PILImage.new("RGBA", (TILE_PX * GRID, TILE_PX * GRID), (220, 220, 220, 255))

        tiles_ok = 0
        for dy in range(GRID):
            for dx in range(GRID):
                raw = _fetch_tile(zoom, cx - 1 + dx, cy - 1 + dy)
                if raw:
                    try:
                        tile = PILImage.open(BytesIO(raw)).convert("RGBA")
                        canvas.paste(tile, (dx * TILE_PX, dy * TILE_PX))
                        tiles_ok += 1
                    except Exception:
                        pass

        if tiles_ok == 0:
            _pdf_log.warning("_cargar_mapa_osm: no se descargó ningún tile para lat=%s lon=%s zoom=%s", lat, lon, zoom)
            return None

        # Posición del marcador dentro del canvas (tile central en posición 1,1)
        lon_f = (float(lon) + 180.0) / 360.0 * n - cx
        lat_r2 = math.radians(float(lat))
        lat_f = (1.0 - math.log(math.tan(lat_r2) + 1.0 / math.cos(lat_r2)) / math.pi) / 2.0 * n - cy
        px = int(TILE_PX + lon_f * TILE_PX)
        py = int(TILE_PX + lat_f * TILE_PX)

        # Marcador: círculo rojo con borde blanco y punto blanco central
        draw = ImageDraw.Draw(canvas)
        r = 10
        draw.ellipse([(px - r, py - r), (px + r, py + r)], fill=(220, 38, 38, 230), outline=(255, 255, 255, 255))
        draw.ellipse([(px - 4, py - 4), (px + 4, py + 4)], fill=(255, 255, 255, 255))

        bio = BytesIO()
        canvas.save(bio, format="PNG")
        bio.seek(0)
        ir = ImageReader(bio)
        iw, ih = ir.getSize()
        max_w = 11 * cm
        esc = min(max_w / float(iw), 1.0)
        bio.seek(0)
        return Image(ImageReader(bio), width=iw * esc, height=ih * esc)

    except Exception as exc:
        _pdf_log.warning("_cargar_mapa_osm: error inesperado: %s", exc)
        return None


def construir_pdf_resumen_expediente(d_row, adjuntos, *, generado_por, fecha_emision):
    """
    PDF de 4 secciones (sin historial) para descarga desde el panel:
    1. Resumen del Caso
    2. Datos del Denunciante
    3. Ubicación del Hecho  (imagen de mapa OSM con marcador)
    4. Descripción y Evidencias
    """
    buf = BytesIO()
    cod = (d_row.get("codigo") or str(d_row.get("id", ""))).strip()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.4 * cm,
        rightMargin=1.4 * cm,
        topMargin=1.1 * cm,
        bottomMargin=1.1 * cm,
        title="Expediente {}".format(cod),
    )
    styles = getSampleStyleSheet()
    st_title = ParagraphStyle("resTitle", parent=styles["Heading1"], fontSize=13,
                              textColor=colors.white, spaceAfter=2, leading=16)
    st_h3 = ParagraphStyle("resH3", parent=styles["Normal"], fontSize=10,
                            textColor=MMQ_BLUE, fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=4)
    st_norm = ParagraphStyle("resN", parent=styles["Normal"], fontSize=9,
                             textColor=colors.black, leading=12)
    st_small = ParagraphStyle("resS", parent=styles["Normal"], fontSize=8,
                              textColor=MUTED, leading=10)
    st_italic = ParagraphStyle("resIt", parent=styles["Normal"], fontSize=9,
                               textColor=MUTED, leading=12, fontName="Helvetica-Oblique")

    flow = []
    sello = _cargar_sello()
    tw = doc.width

    # ── Encabezado ───────────────────────────────────────────────────────
    titulo_hdr = (
        "<b>Expediente {}</b><br/>"
        "<font size='8' color='#e2e8f0'>Mercado Mayorista Quitumbe — MMQEP · Sistema de denuncias y quejas</font>"
    ).format(_esc_xml(cod))
    if sello:
        sw = sello.drawWidth + 0.35 * cm
        hdr_tbl = Table([[sello, Paragraph(titulo_hdr, st_title)]], colWidths=[sw, tw - sw])
    else:
        hdr_tbl = Table(
            [[Paragraph("<b>MMQEP</b>", st_title), Paragraph(titulo_hdr, st_title)]],
            colWidths=[2.8 * cm, tw - 2.8 * cm],
        )
    hdr_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), MMQ_BLUE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    flow.append(hdr_tbl)
    flow.append(Spacer(1, 0.25 * cm))

    meta = "<b>Fecha de emisión:</b> {} · <b>Generado por:</b> {}".format(
        _esc_xml(fecha_emision), _esc_xml(generado_por or "—")
    )
    flow.append(Paragraph(meta, st_small))
    flow.append(Spacer(1, 0.25 * cm))

    def _tabla_datos(filas):
        # IMPORTANTE: escapar solo el contenido de k/v, no las etiquetas <b>
        tdata = [
            [Paragraph("<b>{}</b>".format(_esc_xml(str(k))), st_small),
             Paragraph(_esc_xml(str(v) if v is not None else "—"), st_norm)]
            for k, v in filas
        ]
        t = Table(tdata, colWidths=[4.5 * cm, tw - 4.5 * cm])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -1), 0.35, BORDER),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
        ]))
        return t

    # ── 1. Resumen del Caso ──────────────────────────────────────────────
    flow.append(Paragraph("1. Resumen del Caso", st_h3))
    hora = str(d_row.get("hora_hecho") or "—")
    if hora and len(hora) == 8 and hora[2] == ":":
        hora = hora[:5]
    resumen = [
        ("Estado",               d_row.get("estado")),
        ("Categoría",            d_row.get("categoria")),
        ("Subcategoría",         d_row.get("subcategoria")),
        ("Área institucional",   d_row.get("area_nombre")),
        ("Responsable",          d_row.get("asignado_nombres") or d_row.get("asignado")),
        ("Fecha del hecho",      str(d_row.get("fecha_hecho") or "—")),
        ("Hora del hecho",       hora),
        ("Involucrado(s)",       d_row.get("involucrado")),
        ("Registro ciudadano",   _fmt_dt(d_row.get("fecha_creacion"))),
        ("Última actualización", _fmt_dt(d_row.get("fecha_actualizacion"))),
        ("Fecha de cierre",      _fmt_dt(d_row.get("fecha_cierre")) if d_row.get("fecha_cierre") else "—"),
    ]
    flow.append(_tabla_datos(resumen))
    flow.append(Spacer(1, 0.3 * cm))

    # ── 2. Datos del Denunciante ─────────────────────────────────────────
    flow.append(Paragraph("2. Datos del Denunciante", st_h3))
    if d_row.get("es_anonima"):
        flow.append(Paragraph(
            "Denuncia anónima: no se exponen datos personales del ciudadano.",
            st_italic,
        ))
    else:
        den_filas = [
            ("Nombres",        d_row.get("nombres_denunciante")),
            ("Identificación", d_row.get("identificacion_denunciante")),
            ("Teléfono",       d_row.get("telefono_denunciante")),
            ("Correo",         d_row.get("correo_denunciante")),
        ]
        flow.append(_tabla_datos(den_filas))
    flow.append(Spacer(1, 0.3 * cm))

    # ── 3. Ubicación del Hecho ───────────────────────────────────────────
    flow.append(Paragraph("3. Ubicación del Hecho", st_h3))
    flow.append(_tabla_datos([("Dirección / referencia", d_row.get("ubicacion") or "—")]))
    flow.append(Spacer(1, 0.2 * cm))
    lat = d_row.get("latitud")
    lon = d_row.get("longitud")
    if lat and lon:
        mapa_img = _cargar_mapa_osm(lat, lon)
        if mapa_img:
            flow.append(mapa_img)
        else:
            flow.append(Paragraph(
                "Coordenadas registradas: {}, {} (mapa no disponible al momento de la emisión).".format(lat, lon),
                st_italic,
            ))
    else:
        flow.append(Paragraph("No se registraron coordenadas en esta denuncia.", st_italic))
    flow.append(Spacer(1, 0.3 * cm))

    # ── 4. Descripción y Evidencias ──────────────────────────────────────
    flow.append(Paragraph("4. Descripción y Evidencias", st_h3))
    desc = (d_row.get("descripcion") or "").strip()
    flow.append(Paragraph(_esc_xml(desc) if desc else "<i>Sin descripción registrada.</i>", st_norm))
    flow.append(Spacer(1, 0.2 * cm))

    adj_ciudadano = [a for a in (adjuntos or []) if (a.get("contexto") or "ciudadano") == "ciudadano"]
    if adj_ciudadano:
        flow.append(Paragraph("<b>Archivos adjuntos del ciudadano:</b>", st_small))
        for a in adj_ciudadano:
            nombre = a.get("nombre_original") or a.get("nombre_guardado") or "—"
            flow.append(Paragraph("• {}".format(_esc_xml(nombre)), st_norm))
    else:
        flow.append(Paragraph("<i>No hay adjuntos registrados por el ciudadano.</i>", st_italic))

    flow.append(Spacer(1, 0.5 * cm))
    flow.append(Paragraph(
        "Documento generado electrónicamente desde el sistema MMQEP. "
        "La información debe manejarse conforme a la normativa institucional de protección de datos personales.",
        st_small,
    ))

    doc.build(flow)
    out = buf.getvalue()
    buf.close()
    return out


def construir_pdf_reporte_denuncia_individual(
    d_row,
    segs_rows,
    *,
    modo_externo,
    generado_por,
    fecha_emision,
):
    """
    PDF de un solo expediente. Reutiliza el motor de tablas de construir_pdf_reporte_bandeja.
    """
    did = int(d_row["id"])
    cod = (d_row.get("codigo") or str(did)).strip()
    segs_map = {did: list(segs_rows or [])}

    if modo_externo:
        titulo = "Reporte externo — expediente {}".format(cod)
        aviso = (
            "Este documento reúne únicamente los registros del sistema clasificados como "
            "«gestión realizada ante el ciudadano». No incluye observaciones internas ni otros movimientos reservados. "
            "Revise la pertinencia antes de entregarlo a terceros."
        )
    else:
        titulo = "Reporte interno — expediente {}".format(cod)
        aviso = (
            "Documento de uso interno institucional. Incluye la trazabilidad completa registrada en el sistema "
            "para este expediente. No entregar versiones completas a personas externas sin autorización."
        )

    return construir_pdf_reporte_bandeja(
        [d_row],
        segs_map,
        titulo_principal=titulo,
        aviso_confidencialidad=aviso,
        generado_por=generado_por,
        texto_filtros="Código «{}» · ID interno {}".format(cod, did),
        fecha_emision=fecha_emision,
        modo_externo=modo_externo,
        etiqueta_contexto="Identificación del expediente",
    )

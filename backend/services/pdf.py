import os
import io
import base64
from datetime import datetime
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import mm, inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.fonts import addMapping
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.barcode import qr
from reportlab.graphics import renderPDF
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ============================================================
# QR Code Generation (using reportlab's built-in QR)
# ============================================================

def generate_qr_code(data, size=80):
    """Generate QR code as a Drawing object for reportlab."""
    qr_code = qr.QrCodeWidget(data)
    bounds = qr_code.getBounds()
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    drawing = Drawing(size, size)
    drawing.add(qr_code)
    return drawing

# ============================================================
# Helper: Format currency
# ============================================================

def format_kes(amount):
    return f"KES {amount:,.0f}" if amount else "KES 0"

# ============================================================
# Generate Valuation Certificate PDF
# ============================================================

def generate_valuation_report(valuation_data):
    """
    Generate a PDF valuation certificate.
    valuation_data: dict with keys:
        - certificate_number
        - vehicle: {make, model, year, registration_number, vin, odometer}
        - market_value
        - insurance_value
        - trade_in_value
        - forced_sale_value
        - valuation_date
        - inspector: {name, credentials, signature}
        - purpose
        - methodology
        - region
        - confidence_score
        - qr_data (optional, URL or string)
        - logo_path (optional, path to logo image)
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Heading1', parent=styles['Heading1'], fontSize=22, alignment=TA_CENTER, spaceAfter=12, textColor=colors.HexColor('#eab308')))
    styles.add(ParagraphStyle(name='Heading2', parent=styles['Heading2'], fontSize=16, alignment=TA_CENTER, spaceAfter=8, textColor=colors.HexColor('#1a1a2e')))
    styles.add(ParagraphStyle(name='Body', parent=styles['Normal'], fontSize=10, alignment=TA_LEFT, spaceAfter=4))
    styles.add(ParagraphStyle(name='Centered', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, spaceAfter=4))
    styles.add(ParagraphStyle(name='Value', parent=styles['Normal'], fontSize=14, alignment=TA_LEFT, textColor=colors.HexColor('#22c55e'), fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='Label', parent=styles['Normal'], fontSize=9, alignment=TA_LEFT, textColor=colors.HexColor('#666'), fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='Footer', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=colors.HexColor('#999')))

    elements = []

    # --- Header with Logo ---
    # If you have a logo image, you can add it here:
    # try:
    #     logo = Image(logo_path, width=50*mm, height=20*mm)
    #     elements.append(logo)
    # except:
    #     pass

    elements.append(Paragraph("🚗 AUTO-V", styles['Heading1']))
    elements.append(Paragraph("Professional Valuation Certificate", styles['Heading2']))
    elements.append(Spacer(1, 0.2*inch))

    # Certificate Number & Date
    data = [
        [Paragraph(f"<b>Certificate No:</b> {valuation_data.get('certificate_number', 'N/A')}", styles['Body']),
         Paragraph(f"<b>Date:</b> {valuation_data.get('valuation_date', datetime.now().strftime('%d %B %Y'))}", styles['Body'])]
    ]
    t = Table(data, colWidths=[2.5*inch, 2.5*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('ALIGN', (0,0), (0,0), 'LEFT'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.2*inch))

    # Vehicle Details
    v = valuation_data.get('vehicle', {})
    vehicle_text = f"{v.get('make', 'N/A')} {v.get('model', 'N/A')} ({v.get('year', 'N/A')})"
    elements.append(Paragraph(f"<b>Vehicle:</b> {vehicle_text}", styles['Body']))
    elements.append(Paragraph(f"<b>Registration:</b> {v.get('registration_number', 'N/A')}", styles['Body']))
    if v.get('vin'):
        elements.append(Paragraph(f"<b>VIN / Chassis:</b> {v.get('vin')}", styles['Body']))
    elements.append(Paragraph(f"<b>Odometer:</b> {v.get('odometer', 0):,} km", styles['Body']))
    elements.append(Spacer(1, 0.1*inch))

    # Purpose & Methodology
    elements.append(Paragraph(f"<b>Purpose:</b> {valuation_data.get('purpose', 'Market Value')}", styles['Body']))
    elements.append(Paragraph(f"<b>Methodology:</b> {valuation_data.get('methodology', 'Market Comparison')}", styles['Body']))
    elements.append(Paragraph(f"<b>Region:</b> {valuation_data.get('region', 'Nairobi')}", styles['Body']))
    elements.append(Spacer(1, 0.1*inch))

    # Valuation Results Table
    results_data = [
        [Paragraph("<b>Value Type</b>", styles['Label']), Paragraph("<b>Amount</b>", styles['Label'])],
        ["Market Value", format_kes(valuation_data.get('market_value'))],
        ["Insurance Value", format_kes(valuation_data.get('insurance_value'))],
        ["Trade-In Value", format_kes(valuation_data.get('trade_in_value'))],
        ["Forced Sale Value", format_kes(valuation_data.get('forced_sale_value'))],
    ]
    t = Table(results_data, colWidths=[2.5*inch, 2.5*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#ddd')),
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#f5f5f5')),
        ('ALIGN', (1,1), (1,-1), 'RIGHT'),
        ('TEXTCOLOR', (1,1), (1,1), colors.HexColor('#22c55e')),
        ('FONTNAME', (1,1), (1,1), 'Helvetica-Bold'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.2*inch))

    # Confidence Score
    confidence = valuation_data.get('confidence_score', 85)
    elements.append(Paragraph(f"<b>Confidence Score:</b> {confidence}%", styles['Body']))
    elements.append(Spacer(1, 0.1*inch))

    # Inspector Section
    inspector = valuation_data.get('inspector', {})
    if inspector.get('name'):
        elements.append(Paragraph(f"<b>Inspector:</b> {inspector.get('name')} ({inspector.get('credentials', 'N/A')})", styles['Body']))
        elements.append(Spacer(1, 0.1*inch))
        elements.append(Paragraph(f"<b>Signature:</b> {inspector.get('signature', 'Not signed')}", styles['Body']))
    else:
        elements.append(Paragraph("<b>Inspector:</b> Not specified", styles['Body']))

    elements.append(Spacer(1, 0.3*inch))

    # QR Code
    qr_data = valuation_data.get('qr_data') or f"https://auto-v.meipressgroup.com/verify.html?code={valuation_data.get('certificate_number', '')}"
    try:
        qr_img = generate_qr_code(qr_data, size=60)
        elements.append(Spacer(1, 0.1*inch))
        elements.append(Paragraph("Scan to verify", styles['Centered']))
        elements.append(qr_img)
        elements.append(Spacer(1, 0.1*inch))
    except Exception as e:
        print(f"QR generation failed: {e}")
        elements.append(Paragraph("QR code unavailable", styles['Centered']))

    # Footer
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph("This certificate is electronically generated and signed. Verify authenticity using the QR code.", styles['Footer']))
    elements.append(Paragraph("AUTO-V Vehicle Intelligence Platform © 2024", styles['Footer']))

    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# ============================================================
# Generate Inspection Certificate PDF
# ============================================================

def generate_inspection_report(inspection_data):
    """
    Generate a PDF inspection certificate.
    Similar structure to valuation report but with inspection scores and issues.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Heading1', parent=styles['Heading1'], fontSize=22, alignment=TA_CENTER, spaceAfter=12, textColor=colors.HexColor('#eab308')))
    styles.add(ParagraphStyle(name='Heading2', parent=styles['Heading2'], fontSize=16, alignment=TA_CENTER, spaceAfter=8, textColor=colors.HexColor('#1a1a2e')))
    styles.add(ParagraphStyle(name='Body', parent=styles['Normal'], fontSize=10, alignment=TA_LEFT, spaceAfter=4))
    styles.add(ParagraphStyle(name='Centered', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, spaceAfter=4))
    styles.add(ParagraphStyle(name='Value', parent=styles['Normal'], fontSize=14, alignment=TA_LEFT, textColor=colors.HexColor('#22c55e'), fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='Label', parent=styles['Normal'], fontSize=9, alignment=TA_LEFT, textColor=colors.HexColor('#666'), fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='Footer', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=colors.HexColor('#999')))

    elements = []

    elements.append(Paragraph("🔍 AUTO-V", styles['Heading1']))
    elements.append(Paragraph("Professional Inspection Certificate", styles['Heading2']))
    elements.append(Spacer(1, 0.2*inch))

    # Certificate Number & Date
    data = [
        [Paragraph(f"<b>Certificate No:</b> {inspection_data.get('certificate_number', 'N/A')}", styles['Body']),
         Paragraph(f"<b>Date:</b> {inspection_data.get('inspection_date', datetime.now().strftime('%d %B %Y'))}", styles['Body'])]
    ]
    t = Table(data, colWidths=[2.5*inch, 2.5*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('ALIGN', (0,0), (0,0), 'LEFT'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.2*inch))

    # Vehicle Details
    v = inspection_data.get('vehicle', {})
    vehicle_text = f"{v.get('make', 'N/A')} {v.get('model', 'N/A')} ({v.get('year', 'N/A')})"
    elements.append(Paragraph(f"<b>Vehicle:</b> {vehicle_text}", styles['Body']))
    elements.append(Paragraph(f"<b>Registration:</b> {v.get('registration_number', 'N/A')}", styles['Body']))
    elements.append(Paragraph(f"<b>Odometer:</b> {v.get('odometer', 0):,} km", styles['Body']))
    elements.append(Spacer(1, 0.1*inch))

    # Inspection Scores
    scores = inspection_data.get('scores', {})
    elements.append(Paragraph("<b>Inspection Results</b>", styles['Heading2']))
    score_data = [
        ["Category", "Score"],
        ["Overall Vehicle Health", f"{scores.get('overall', 0):.1f}/10"],
        ["Exterior", f"{scores.get('exterior', 0):.1f}/10"],
        ["Interior", f"{scores.get('interior', 0):.1f}/10"],
        ["Mechanical", f"{scores.get('mechanical', 0):.1f}/10"],
        ["Electrical", f"{scores.get('electrical', 0):.1f}/10"],
        ["Safety", f"{scores.get('safety', 0):.1f}/10"],
    ]
    t = Table(score_data, colWidths=[2.5*inch, 2.5*inch])
    t.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#ddd')),
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#f5f5f5')),
        ('ALIGN', (1,1), (1,-1), 'CENTER'),
        ('TEXTCOLOR', (1,1), (1,1), colors.HexColor('#22c55e')),
        ('FONTNAME', (1,1), (1,1), 'Helvetica-Bold'),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.2*inch))

    # Issues
    issues = inspection_data.get('issues', [])
    if issues:
        elements.append(Paragraph("<b>Issues Found:</b>", styles['Body']))
        for issue in issues:
            elements.append(Paragraph(f"• {issue}", styles['Body']))
    else:
        elements.append(Paragraph("<b>No major issues detected.</b>", styles['Body']))
    elements.append(Spacer(1, 0.1*inch))

    # Inspector
    inspector = inspection_data.get('inspector', {})
    if inspector.get('name'):
        elements.append(Paragraph(f"<b>Inspector:</b> {inspector.get('name')} ({inspector.get('credentials', 'N/A')})", styles['Body']))
        elements.append(Paragraph(f"<b>Signature:</b> {inspector.get('signature', 'Not signed')}", styles['Body']))
    else:
        elements.append(Paragraph("<b>Inspector:</b> Not specified", styles['Body']))

    elements.append(Spacer(1, 0.3*inch))

    # QR Code
    qr_data = inspection_data.get('qr_data') or f"https://auto-v.meipressgroup.com/verify.html?code={inspection_data.get('certificate_number', '')}"
    try:
        qr_img = generate_qr_code(qr_data, size=60)
        elements.append(Spacer(1, 0.1*inch))
        elements.append(Paragraph("Scan to verify", styles['Centered']))
        elements.append(qr_img)
        elements.append(Spacer(1, 0.1*inch))
    except Exception as e:
        elements.append(Paragraph("QR code unavailable", styles['Centered']))

    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph("This certificate is electronically generated and signed. Verify authenticity using the QR code.", styles['Footer']))
    elements.append(Paragraph("AUTO-V Vehicle Intelligence Platform © 2024", styles['Footer']))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# ============================================================
# Utility: Generate simple PDF report from JSON
# ============================================================

def generate_simple_report(title, content_dict, output_format='bytes'):
    """
    Generate a simple PDF report from a dictionary of content.
    Useful for quick reports like mileage calculations.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Heading1', parent=styles['Heading1'], fontSize=20, alignment=TA_CENTER, spaceAfter=12, textColor=colors.HexColor('#eab308')))
    styles.add(ParagraphStyle(name='Body', parent=styles['Normal'], fontSize=10, alignment=TA_LEFT, spaceAfter=4))
    styles.add(ParagraphStyle(name='Label', parent=styles['Normal'], fontSize=9, alignment=TA_LEFT, textColor=colors.HexColor('#666'), fontName='Helvetica-Bold'))

    elements = []
    elements.append(Paragraph(f"📊 {title}", styles['Heading1']))
    elements.append(Spacer(1, 0.2*inch))

    for key, value in content_dict.items():
        if isinstance(value, dict):
            elements.append(Paragraph(f"<b>{key}:</b>", styles['Label']))
            for sub_key, sub_val in value.items():
                elements.append(Paragraph(f"&nbsp;&nbsp;{sub_key}: {sub_val}", styles['Body']))
        else:
            elements.append(Paragraph(f"<b>{key}:</b> {value}", styles['Body']))

    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%d %B %Y %H:%M')}", styles['Body']))
    elements.append(Paragraph("AUTO-V Vehicle Intelligence Platform", styles['Body']))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# ============================================================
# Usage Example (if run directly)
# ============================================================

if __name__ == "__main__":
    # Sample valuation data
    sample_valuation = {
        'certificate_number': 'VAL-20240618-ABC123',
        'valuation_date': '18 June 2026',
        'vehicle': {
            'make': 'Toyota',
            'model': 'Axio',
            'year': 2022,
            'registration_number': 'KDA 123A',
            'vin': 'JTEGD34V000123456',
            'odometer': 45000
        },
        'market_value': 2850000,
        'insurance_value': 3135000,
        'trade_in_value': 2280000,
        'forced_sale_value': 1995000,
        'purpose': 'Market Value',
        'methodology': 'Market Comparison',
        'region': 'Nairobi',
        'confidence_score': 92,
        'inspector': {
            'name': 'John M. Valuer',
            'credentials': 'AVM-45678',
            'signature': 'John M. Valuer'
        },
        'qr_data': 'https://auto-v.meipressgroup.com/verify/VAL-20240618-ABC123'
    }

    # Generate PDF
    pdf_bytes = generate_valuation_report(sample_valuation)
    with open('sample_valuation.pdf', 'wb') as f:
        f.write(pdf_bytes)
    print("✅ Sample valuation PDF generated: sample_valuation.pdf")

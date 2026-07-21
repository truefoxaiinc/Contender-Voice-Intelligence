from html import unescape
from io import BytesIO
from textwrap import wrap

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

GREEN = colors.HexColor("#153D29")
INK = colors.HexColor("#17211B")
MUTED = colors.HexColor("#647168")
PALE = colors.HexColor("#F4F7F3")
LINE = colors.HexColor("#DDE5DF")
PAGE_WIDTH, PAGE_HEIGHT = letter
LEFT, RIGHT, TOP, BOTTOM = 50, 50, 48, 48


def clean(value, fallback="Not provided") -> str:
    if value in (None, ""):
        return fallback
    return unescape(str(value)).replace("\r", " ").replace("\t", " ")


class ReportWriter:
    def __init__(self, output: BytesIO, call_id: str):
        self.canvas = canvas.Canvas(output, pagesize=letter)
        self.call_id = call_id
        self.page = 0
        self.y = 0
        self.new_page()

    def new_page(self):
        if self.page:
            self.footer()
            self.canvas.showPage()
        self.page += 1
        self.y = PAGE_HEIGHT - TOP

    def footer(self):
        self.canvas.setStrokeColor(LINE)
        self.canvas.line(LEFT, 38, PAGE_WIDTH - RIGHT, 38)
        self.canvas.setFont("Helvetica", 8)
        self.canvas.setFillColor(MUTED)
        self.canvas.drawString(LEFT, 24, f"Contender Voice Intelligence - {self.call_id}")
        self.canvas.drawRightString(PAGE_WIDTH - RIGHT, 24, f"Page {self.page}")

    def ensure(self, height: float):
        if self.y - height < BOTTOM:
            self.new_page()

    def line(self, value: str, font="Helvetica", size=9.5, color=INK, indent=0, gap=14):
        self.ensure(gap)
        self.canvas.setFont(font, size)
        self.canvas.setFillColor(color)
        self.canvas.drawString(LEFT + indent, self.y, value)
        self.y -= gap

    def paragraph(self, value: str, size=9.5, color=INK, indent=0, before=0, after=6, width=94):
        self.y -= before
        paragraphs = clean(value).split("\n")
        for paragraph in paragraphs:
            lines = wrap(paragraph, width=max(20, width - indent // 5), break_long_words=True) or [""]
            for item in lines:
                self.line(item, size=size, color=color, indent=indent, gap=size + 4)
        self.y -= after

    def heading(self, value: str):
        self.ensure(30)
        self.y -= 8
        self.line(value, font="Helvetica-Bold", size=13, color=GREEN, gap=18)

    def finish(self):
        self.footer()
        self.canvas.save()


def build_call_pdf(call: dict, events: list[dict] | None = None) -> bytes:
    """Create a complete, authenticated per-call PDF report."""
    output = BytesIO()
    writer = ReportWriter(output, clean(call.get("id"), "CALL"))

    writer.canvas.setFillColor(GREEN)
    writer.canvas.roundRect(LEFT, writer.y - 27, PAGE_WIDTH - LEFT - RIGHT, 27, 7, fill=1, stroke=0)
    writer.canvas.setFillColor(colors.white)
    writer.canvas.setFont("Helvetica-Bold", 10)
    writer.canvas.drawCentredString(PAGE_WIDTH / 2, writer.y - 17, "CONTENDER VOICE INTELLIGENCE")
    writer.y -= 49
    writer.canvas.setFillColor(INK)
    writer.canvas.setFont("Helvetica-Bold", 22)
    writer.canvas.drawCentredString(PAGE_WIDTH / 2, writer.y, "Call Intelligence Report")
    writer.y -= 18
    writer.canvas.setFillColor(MUTED)
    writer.canvas.setFont("Helvetica", 9)
    writer.canvas.drawCentredString(PAGE_WIDTH / 2, writer.y, f"{clean(call.get('id'))} | {clean(call.get('created_at'))}")
    writer.y -= 28

    fields = [
        ("Caller", call.get("caller_name")), ("Company", call.get("company_name")),
        ("Phone", call.get("caller_phone")), ("Filename", call.get("filename")),
        ("Category", call.get("category")), ("Priority", call.get("priority")),
        ("Workflow status", call.get("status")), ("Processing status", call.get("processing_status")),
    ]
    for label, value in fields:
        writer.ensure(24)
        writer.canvas.setFillColor(PALE)
        writer.canvas.rect(LEFT, writer.y - 17, PAGE_WIDTH - LEFT - RIGHT, 21, fill=1, stroke=0)
        writer.line(label.upper(), font="Helvetica-Bold", size=7.5, color=MUTED, indent=7, gap=0)
        writer.canvas.setFont("Helvetica-Bold", 9.5)
        writer.canvas.setFillColor(INK)
        writer.canvas.drawString(170, writer.y, clean(value))
        writer.y -= 23

    writer.heading("Priority reason")
    writer.paragraph(call.get("priority_reason"))
    writer.heading("Conversation summary")
    writer.paragraph(call.get("summary"))
    writer.heading("Important information")
    for item in call.get("important_information") or []:
        writer.paragraph(f"- {clean(item)}", indent=10, after=1)
    if not call.get("important_information"):
        writer.paragraph("None recorded.")
    writer.heading("Missing information")
    for item in call.get("missing_information") or []:
        writer.paragraph(f"- {clean(item)}", indent=10, after=1)
    if not call.get("missing_information"):
        writer.paragraph("None recorded.")
    writer.heading("Recommended next action")
    writer.paragraph(call.get("recommended_next_action"))

    writer.new_page()
    writer.heading("Full conversation transcript")
    segments = call.get("transcript_segments") or []
    if segments:
        for segment in segments:
            seconds = int(segment.get("start", 0))
            writer.paragraph(f"{seconds // 60}:{seconds % 60:02d}  {clean(segment.get('text'))}", after=4)
    else:
        writer.paragraph(call.get("transcript"), width=100)

    if events:
        writer.heading("Activity history")
        for event in events:
            writer.paragraph(f"{clean(event.get('timestamp'))} - {clean(event.get('event_type')).replace('_', ' ').title()}: {clean(event.get('new_value'))}", size=8.5, color=MUTED, after=3)

    writer.finish()
    return output.getvalue()

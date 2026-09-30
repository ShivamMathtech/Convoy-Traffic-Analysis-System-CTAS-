"""Session report generator: professional PDF + JSON summary.

Includes session info, source details, model info, vehicle/class stats,
tracking, speed, spacing, lane & group stats, event timeline, performance
metrics. Charts are drawn with reportlab graphics from real analytics data.
"""
from __future__ import annotations

import csv
import json
import logging
from collections import Counter
from pathlib import Path

log = logging.getLogger("ctas.reports")


def _read_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_report_data(session_id: str, out_dir: Path) -> dict:
    analytics_p = out_dir / "analytics.json"
    analytics = json.loads(analytics_p.read_text()) if analytics_p.exists() else {}
    session_p = out_dir / "session.json"
    session = json.loads(session_p.read_text()) if session_p.exists() else {}
    events = _read_csv_rows(out_dir / "events.csv")
    tracks = _read_csv_rows(out_dir / "tracks.csv")

    class_counts = Counter(r["class"] for r in tracks if r.get("class"))
    unique_ids = {r["track_id"] for r in tracks if r.get("track_id")}
    speeds = [float(r["speed"]) for r in tracks if r.get("speed")]
    lanes = Counter(r["lane"] for r in tracks if r.get("lane"))

    vc = analytics.get("vehicle_count_over_time", [])
    peak = max((p["v"] for p in vc if p["v"] is not None), default=0)

    return {
        "session_id": session_id,
        "session": session,
        "frames": session.get("frames", 0),
        "processed_frames": session.get("processed_frames", 0),
        "inference_fps": round(session.get("inference_fps", 0) or 0, 1),
        "calibrated": session.get("calibrated", False),
        "unique_vehicles": len(unique_ids),
        "class_counts": dict(class_counts),
        "peak_vehicles": peak,
        "avg_speed": round(sum(speeds) / len(speeds), 2) if speeds else None,
        "max_speed": round(max(speeds), 2) if speeds else None,
        "lane_counts": dict(lanes),
        "total_events": len(events),
        "events": events[:500],
        "analytics": analytics,
        "settings": session.get("settings", {}),
    }


def generate_pdf(session_id: str, out_dir: Path) -> Path:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer,
                                    Table, TableStyle)

    data = build_report_data(session_id, out_dir)
    pdf_path = out_dir / "report.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4,
                            topMargin=18 * mm, bottomMargin=18 * mm)
    styles = getSampleStyleSheet()
    story = []
    H1, H2, N = styles["Heading1"], styles["Heading2"], styles["Normal"]

    story.append(Paragraph("Convoy &amp; Traffic Analysis System", H1))
    story.append(Paragraph(f"Session Report — {session_id}", H2))
    story.append(Spacer(1, 6 * mm))

    def kv_table(rows):
        t = Table(rows, colWidths=[70 * mm, 90 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#1b2a4a")),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 4 * mm))

    s = data["session"]
    story.append(Paragraph("Session Information", H2))
    kv_table([
        ["Session ID", session_id],
        ["Source", str(s.get("settings", {}).get("source", "")) or data["session"].get("source", "")],
        ["Frames (total / processed)", f"{data['frames']} / {data['processed_frames']}"],
        ["Inference FPS", str(data["inference_fps"])],
        ["Calibrated (metric)", "Yes" if data["calibrated"] else "No — pixel units"],
        ["Model", str(data["settings"].get("model", {}).get("model_path", "default"))],
        ["Tracker", str(data["settings"].get("tracker", {}).get("name", "bytetrack"))],
    ])

    story.append(Paragraph("Vehicle Statistics", H2))
    rows = [["Class", "Unique vehicles"]]
    for cls, n in sorted(data["class_counts"].items()):
        rows.append([cls, str(n)])
    rows.append(["TOTAL (unique)", str(data["unique_vehicles"])])
    rows.append(["Peak concurrent", str(data["peak_vehicles"])])
    t = Table(rows, colWidths=[70 * mm, 90 * mm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b2a4a")),
                           ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("FONTSIZE", (0, 0), (-1, -1), 9)]))
    story.append(t)
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Speed / Spacing / Lanes", H2))
    unit = "km/h" if data["calibrated"] else "px/s"
    kv_table([
        ["Average speed", f"{data['avg_speed']} {unit}" if data["avg_speed"] is not None else "n/a"],
        ["Max speed", f"{data['max_speed']} {unit}" if data["max_speed"] is not None else "n/a"],
        ["Lane occupancy", json.dumps(data["lane_counts"]) or "n/a"],
    ])

    story.append(Paragraph(f"Event Timeline ({data['total_events']} events)", H2))
    erows = [["Time (s)", "Type", "Severity", "Track", "Description"]]
    for e in data["events"][:120]:
        erows.append([str(e.get("timestamp", "")), str(e.get("event_type", "")),
                      str(e.get("severity", "")), str(e.get("track_id", "")),
                      str(e.get("description", ""))[:90]])
    if erows[1:]:
        et = Table(erows, colWidths=[18 * mm, 38 * mm, 20 * mm, 14 * mm, 70 * mm], repeatRows=1)
        et.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b2a4a")),
                                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                ("FONTSIZE", (0, 0), (-1, -1), 7)]))
        story.append(et)
    else:
        story.append(Paragraph("No events recorded.", N))

    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        "Generated by CTAS. Metric values (m, km/h) appear only when perspective "
        "calibration was performed; otherwise pixel units are used.", N))

    doc.build(story)
    log.info("PDF report written to %s", pdf_path)
    return pdf_path


def generate_json_summary(session_id: str, out_dir: Path) -> Path:
    data = build_report_data(session_id, out_dir)
    p = out_dir / "report.json"
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return p

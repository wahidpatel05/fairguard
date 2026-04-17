"""Report generation service: PDF (ReportLab) and Markdown."""
from __future__ import annotations

import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Colour constants
_GRAY = colors.HexColor("#4A4A4A")
_LIGHT_GRAY = colors.HexColor("#F2F2F2")
_GREEN = colors.HexColor("#D4EDDA")
_RED = colors.HexColor("#F8D7DA")
_YELLOW = colors.HexColor("#FFF3CD")
_WHITE = colors.white
_HEADER_BG = colors.HexColor("#343A40")
_HEADER_FG = colors.white

_VERDICT_EMOJI = {
    "pass": "✅ PASS",
    "pass_with_warnings": "⚠️ PASS WITH WARNINGS",
    "fail": "❌ FAIL",
}


class ReportService:
    """Generates audit reports in Markdown and PDF formats."""

    # ------------------------------------------------------------------
    # Markdown
    # ------------------------------------------------------------------

    @staticmethod
    def generate_markdown(
        audit: dict,
        project: dict,
        contract_results: list[dict],
        metrics: dict,
        recommendations: list[dict],
    ) -> str:
        """Generate a complete Markdown audit report string.

        No individual records or raw sensitive attribute values are included –
        only aggregated statistics are reported.
        """
        verdict_raw = audit.get("verdict") or "unknown"
        verdict_label = _VERDICT_EMOJI.get(verdict_raw, verdict_raw.upper())
        created_at = audit.get("created_at") or ""
        dataset_hash = audit.get("dataset_hash") or "N/A"
        project_name = project.get("name") or "Unknown Project"

        lines: list[str] = [
            "# FairGuard Audit Report",
            "",
            f"## Project: {project_name}",
            "",
            f"**Audit Date:** {created_at}",
            "",
            f"**Dataset Hash:** `{dataset_hash}` (SHA-256)",
            "",
            f"**Verdict:** {verdict_label}",
            "",
            "---",
            "",
        ]

        # Fairness Contracts Evaluated
        lines += [
            "## Fairness Contracts Evaluated",
            "",
            "| Contract | Attribute | Metric | Value | Threshold | Status |",
            "|----------|-----------|--------|-------|-----------|--------|",
        ]
        for r in contract_results:
            value = r.get("value")
            value_str = f"{value:.4f}" if value is not None else "N/A"
            passed = r.get("passed", True)
            status_str = "✅ Pass" if passed else "❌ Fail"
            attribute = r.get("attribute") or "—"
            lines.append(
                f"| {r.get('contract_id', '')} "
                f"| {attribute} "
                f"| {r.get('metric', '')} "
                f"| {value_str} "
                f"| {r.get('threshold', '')} "
                f"| {status_str} |"
            )

        lines += ["", "---", ""]

        # Per-Group Metrics
        lines += ["## Per-Group Metrics", ""]
        by_attribute: dict = (metrics or {}).get("by_attribute", {})
        for attr, attr_data in by_attribute.items():
            lines += [f"### Attribute: `{attr}`", ""]
            lines += [
                "| Group | Count | Selection Rate | TPR | FPR | Accuracy |",
                "|-------|-------|----------------|-----|-----|----------|",
            ]
            per_group: dict = attr_data.get("per_group", {})
            for group_val, gdata in per_group.items():
                count = gdata.get("count", 0)
                sr = gdata.get("selection_rate", 0.0)
                tpr = gdata.get("tpr", 0.0)
                fpr = gdata.get("fpr", 0.0)
                acc = gdata.get("accuracy", 0.0)
                lines.append(
                    f"| {group_val} | {count} | {sr:.1%} | {tpr:.1%} | {fpr:.1%} | {acc:.1%} |"
                )
            lines.append("")

        lines += ["---", ""]

        # Failing Contracts & Explanations
        failing = [r for r in contract_results if not r.get("passed", True)]
        if failing:
            lines += ["## Failing Contracts & Explanations", ""]
            for r in failing:
                lines += [
                    f"### Contract `{r.get('contract_id', '')}` – {r.get('metric', '')}",
                    "",
                    r.get("explanation", ""),
                    "",
                ]

        # Mitigation Recommendations
        if recommendations:
            lines += ["## Mitigation Recommendations", ""]
            for rec in recommendations:
                metric = rec.get("metric", "")
                attr = rec.get("attribute") or "all attributes"
                lines.append(f"### {metric} ({attr})")
                lines.append("")
                for item in rec.get("recommendations", []):
                    lines.append(f"- {item}")
                lines.append("")

        # Data Integrity
        lines += [
            "---",
            "",
            "## Data Integrity",
            "",
            f"Dataset SHA-256: `{dataset_hash}`",
            "",
            "> **Note:** Raw data was not stored. Only aggregated statistics are reported.",
            "",
        ]

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # PDF
    # ------------------------------------------------------------------

    @staticmethod
    def generate_pdf(
        audit: dict,
        project: dict,
        contract_results: list[dict],
        metrics: dict,
        recommendations: list[dict],
    ) -> bytes:
        """Generate a PDF audit report using ReportLab.

        Returns raw bytes. PDF contains only aggregated statistics –
        no individual records or raw sensitive attribute values.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "FGTitle",
            parent=styles["Title"],
            fontSize=24,
            spaceAfter=12,
            textColor=_GRAY,
        )
        h1_style = ParagraphStyle(
            "FGH1",
            parent=styles["Heading1"],
            fontSize=16,
            spaceAfter=8,
            textColor=_GRAY,
        )
        h2_style = ParagraphStyle(
            "FGH2",
            parent=styles["Heading2"],
            fontSize=13,
            spaceAfter=6,
            textColor=_GRAY,
        )
        normal = styles["Normal"]

        verdict_raw = audit.get("verdict") or "unknown"
        verdict_label = _VERDICT_EMOJI.get(verdict_raw, verdict_raw.upper())
        created_at = audit.get("created_at") or ""
        dataset_hash = audit.get("dataset_hash") or "N/A"
        project_name = project.get("name") or "Unknown Project"

        story: list = []

        # ----- Title page -----
        story.append(Paragraph("FairGuard", title_style))
        story.append(Paragraph("Audit Report", h1_style))
        story.append(HRFlowable(width="100%", thickness=1, color=_GRAY))
        story.append(Spacer(1, 0.4 * cm))
        story.append(Paragraph(f"<b>Project:</b> {project_name}", normal))
        story.append(Paragraph(f"<b>Audit Date:</b> {created_at}", normal))
        story.append(Paragraph(f"<b>Dataset Hash:</b> {dataset_hash}", normal))

        # Verdict badge colour
        verdict_colour = {
            "pass": colors.HexColor("#28a745"),
            "pass_with_warnings": colors.HexColor("#ffc107"),
            "fail": colors.HexColor("#dc3545"),
        }.get(verdict_raw, _GRAY)

        verdict_style = ParagraphStyle(
            "Verdict",
            parent=normal,
            textColor=verdict_colour,
            fontSize=14,
            spaceBefore=8,
            spaceAfter=8,
        )
        story.append(Paragraph(f"<b>Verdict:</b> {verdict_label}", verdict_style))
        story.append(Spacer(1, 0.6 * cm))

        # ----- Executive summary: global metrics -----
        story.append(HRFlowable(width="100%", thickness=1, color=_LIGHT_GRAY))
        story.append(Paragraph("Executive Summary", h1_style))

        global_metrics: dict = (metrics or {}).get("global", {})
        if global_metrics:
            gm_data = [["Metric", "Value"]]
            for k, v in global_metrics.items():
                label = k.replace("_", " ").title()
                if isinstance(v, float):
                    val = f"{v:.4f}"
                else:
                    val = str(v)
                gm_data.append([label, val])

            gm_table = Table(gm_data, colWidths=[10 * cm, 6 * cm])
            gm_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
                        ("TEXTCOLOR", (0, 0), (-1, 0), _HEADER_FG),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("BACKGROUND", (0, 1), (-1, -1), _LIGHT_GRAY),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_WHITE, _LIGHT_GRAY]),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(gm_table)
            story.append(Spacer(1, 0.4 * cm))

        # ----- Fairness contracts table -----
        if contract_results:
            story.append(Paragraph("Fairness Contracts Evaluated", h1_style))

            ct_header = [
                "Contract ID",
                "Attribute",
                "Metric",
                "Value",
                "Threshold",
                "Status",
            ]
            ct_data = [ct_header]
            row_colours: list[tuple] = []

            for idx, r in enumerate(contract_results, start=1):
                value = r.get("value")
                value_str = f"{value:.4f}" if value is not None else "N/A"
                passed = r.get("passed", True)
                status_str = "Pass" if passed else "Fail"
                row_bg = _GREEN if passed else _RED
                row_colours.append(
                    ("BACKGROUND", (0, idx), (-1, idx), row_bg)
                )
                ct_data.append(
                    [
                        str(r.get("contract_id", ""))[:20],
                        str(r.get("attribute") or "—"),
                        str(r.get("metric", "")),
                        value_str,
                        str(r.get("threshold", "")),
                        status_str,
                    ]
                )

            col_w = [3.5 * cm, 3 * cm, 3.5 * cm, 2.5 * cm, 2.5 * cm, 2 * cm]
            ct_table = Table(ct_data, colWidths=col_w)
            base_style = [
                ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
                ("TEXTCOLOR", (0, 0), (-1, 0), _HEADER_FG),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
            ct_table.setStyle(TableStyle(base_style + row_colours))
            story.append(ct_table)
            story.append(Spacer(1, 0.4 * cm))

        # ----- Per-attribute sections -----
        by_attribute: dict = (metrics or {}).get("by_attribute", {})
        if by_attribute:
            story.append(Paragraph("Per-Group Metrics", h1_style))
            for attr, attr_data in by_attribute.items():
                story.append(Paragraph(f"Attribute: {attr}", h2_style))
                per_group: dict = attr_data.get("per_group", {})

                pg_header = ["Group", "Count", "Sel. Rate", "TPR", "FPR", "Accuracy"]
                pg_data = [pg_header]
                for group_val, gdata in per_group.items():
                    pg_data.append(
                        [
                            str(group_val),
                            str(gdata.get("count", 0)),
                            f"{gdata.get('selection_rate', 0.0):.1%}",
                            f"{gdata.get('tpr', 0.0):.1%}",
                            f"{gdata.get('fpr', 0.0):.1%}",
                            f"{gdata.get('accuracy', 0.0):.1%}",
                        ]
                    )

                col_w2 = [3 * cm, 2.5 * cm, 3 * cm, 2.5 * cm, 2.5 * cm, 3 * cm]
                pg_table = Table(pg_data, colWidths=col_w2)
                pg_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
                            ("TEXTCOLOR", (0, 0), (-1, 0), _HEADER_FG),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_WHITE, _LIGHT_GRAY]),
                            ("FONTSIZE", (0, 0), (-1, -1), 9),
                            ("TOPPADDING", (0, 0), (-1, -1), 3),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        ]
                    )
                )
                story.append(pg_table)
                story.append(Spacer(1, 0.3 * cm))

        # ----- Mitigation Recommendations -----
        if recommendations:
            story.append(HRFlowable(width="100%", thickness=1, color=_LIGHT_GRAY))
            story.append(Paragraph("Mitigation Recommendations", h1_style))
            for rec in recommendations:
                metric = rec.get("metric", "")
                attr = rec.get("attribute") or "all attributes"
                story.append(Paragraph(f"<b>{metric}</b> ({attr})", h2_style))
                for item in rec.get("recommendations", []):
                    story.append(Paragraph(f"• {item}", normal))
                story.append(Spacer(1, 0.2 * cm))

        # ----- Data integrity footer -----
        story.append(HRFlowable(width="100%", thickness=1, color=_LIGHT_GRAY))
        story.append(Paragraph("Data Integrity", h2_style))
        story.append(Paragraph(f"Dataset SHA-256: <tt>{dataset_hash}</tt>", normal))
        story.append(
            Paragraph(
                "Raw data was not stored. Only aggregated statistics are reported.",
                normal,
            )
        )
        story.append(
            Paragraph(
                f"Report generated: {datetime.now(timezone.utc).isoformat()}",
                normal,
            )
        )

        doc.build(story)
        return buffer.getvalue()

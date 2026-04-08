"""
reporter.py — Generates Markdown reports and JSON exports from AnalysisResult.
"""
import json, os
from datetime import datetime
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from synthesizer import AnalysisResult

SEVERITY_EMOJI = {"high": "🔴", "medium": "🟡", "low": "🟢"}
FREQUENCY_EMOJI = {"always": "⚡", "often": "🔁", "sometimes": "〰️", "rarely": "💤",
                   "high": "⚡", "medium": "🔁", "low": "〰️"}
FRAMEWORK_LABEL = {
    "jtbd_functional": "JTBD — Functional", "jtbd_emotional": "JTBD — Emotional",
    "jtbd_social": "JTBD — Social", "pain_point": "Pain Point",
    "motivation_goal": "Motivation — Goal", "motivation_desire": "Motivation — Desire",
    "motivation_fear": "Motivation — Fear", "key_theme": "Key Theme",
}

class Reporter:
    def __init__(self, result: "AnalysisResult"):
        self.result = result
        self._md = ""

    def save_markdown(self, path):
        _ensure_dir(path)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())
        print(f"Markdown report saved → {path}")

    def save_json(self, path):
        _ensure_dir(path)
        payload = {"meta": {"filename": self.result.transcript.filename,
                             "format": self.result.transcript.format,
                             "word_count": self.result.transcript.word_count,
                             "language": self.result.language,
                             "model_used": self.result.model_used,
                             "input_tokens": self.result.input_tokens,
                             "output_tokens": self.result.output_tokens,
                             "elapsed_seconds": round(self.result.elapsed_seconds, 2),
                             "generated_at": datetime.utcnow().isoformat() + "Z"},
                   "analysis": self.result.analysis}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"JSON export saved      → {path}")

    def to_markdown(self):
        if not self._md:
            self._md = self._render()
        return self._md

    def _render(self):
        r, a, s = self.result, self.result.analysis, []
        s += [f"# Research Synthesis Report", _meta_table(r)]
        s += [f"## Executive Summary", a.get("executive_summary", "_No summary generated._")]
        profile = a.get("participant_profile", {})
        if profile:
            s += [f"## Participant Profile",
                  f"**Summary:** {profile.get('summary','—')}\n\n**Inferred context:** {profile.get('inferred_context','—')}"]
        themes = a.get("key_themes", [])
        if themes:
            s.append("## Key Themes")
            for t in themes:
                freq = t.get("frequency", "")
                s += [f"### {FREQUENCY_EMOJI.get(freq,'')} {t.get('theme','?')}  `{freq}`",
                      t.get("description", "")]
                if t.get("supporting_quotes"):
                    s.append(_quote_list(t["supporting_quotes"]))
        jtbd = a.get("jobs_to_be_done", {})
        if any(jtbd.get(k) for k in ("functional", "emotional", "social")):
            s.append("## Jobs-to-be-Done (JTBD)")
            for jtype, label in [("functional","Functional Jobs"),("emotional","Emotional Jobs"),("social","Social Jobs")]:
                for job in jtbd.get(jtype, []):
                    s += [f"### {label}", f"**{job.get('job_statement','?')}**",
                          f"*Context:* {job.get('context','')}" if job.get("context") else ""]
                    if job.get("quotes"):
                        s.append(_quote_list(job["quotes"]))
                    s.append("")
        pps = a.get("pain_points", [])
        if pps:
            s.append("## Pain Points")
            for pp in pps:
                sev, freq = pp.get("severity",""), pp.get("frequency","")
                s += [f"### {SEVERITY_EMOJI.get(sev,'')} {pp.get('pain','?')}  `severity: {sev}` `frequency: {freq}`",
                      pp.get("description","")]
                if pp.get("current_workaround","").lower() not in ("", "none mentioned"):
                    s.append(f"\n**Current workaround:** {pp['current_workaround']}")
                if pp.get("quotes"):
                    s.append(_quote_list(pp["quotes"]))
                s.append("")
        motivations = a.get("motivations", {})
        if any(motivations.get(k) for k in ("goals","desires","fears")):
            s.append("## Motivations")
            for mtype, label in [("goals","Goals"),("desires","Desires"),("fears","Fears")]:
                for item in motivations.get(mtype, []):
                    s += [f"### {label}", f"**{item.get('motivation','?')}**", item.get("description","")]
                    if item.get("quotes"):
                        s.append(_quote_list(item["quotes"]))
                    s.append("")
        notable = a.get("notable_quotes", [])
        if notable:
            s.append("## Notable Quotes")
            for q in notable:
                orig, trans = q.get("original",""), q.get("translation","")
                s.append(f"> {orig}" + (f"\n>\n> *\"{trans}\"*" if trans and trans != orig else ""))
                if q.get("why_notable"):
                    s.append(f"\n_{q['why_notable']}_")
                s.append("")
        opps = a.get("opportunities", [])
        if opps:
            s.append("## Opportunities")
            for i, opp in enumerate(opps, 1):
                fw = FRAMEWORK_LABEL.get(opp.get("linked_framework",""), "")
                s += [f"**{i}. {opp.get('opportunity','?')}**", opp.get("rationale",""),
                      f"\n*Linked to:* {fw} — *{opp.get('linked_item','')}*", ""]
        notes = a.get("researcher_notes","")
        if notes:
            s += ["## Researcher Notes", f"> {notes}"]
        s += ["\n---",
              f"*Generated by AI Research Synthesizer · Model: `{r.model_used}` · "
              f"Tokens: {r.input_tokens} in / {r.output_tokens} out · "
              f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*"]
        return "\n\n".join(s)

def _meta_table(result):
    rows = [("File", result.transcript.filename), ("Format", result.transcript.format.upper()),
            ("Language", result.language), ("Word count", str(result.transcript.word_count)),
            ("Generated", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))]
    if result.transcript.estimated_duration_min > 0:
        rows.insert(4, ("Duration", f"~{result.transcript.estimated_duration_min:.0f} min"))
    return "| | |\n|---|---|\n" + "\n".join(f"| **{l}** | {v} |" for l, v in rows)

def _quote_list(quotes):
    parts = []
    for q in quotes:
        orig, trans = q.get("original","").strip(), q.get("translation","").strip()
        if orig:
            parts.append(f'> "{orig}"' + (f'\n>\n> *"{trans}"*' if trans and trans != orig else ""))
    return "\n\n".join(parts)

def _ensure_dir(filepath):
    d = os.path.dirname(filepath)
    if d:
        os.makedirs(d, exist_ok=True)

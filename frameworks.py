"""
frameworks.py — Research framework schema + Claude system prompt.
"""

def _quote_schema():
    return {"type": "object", "required": ["original", "translation"],
            "properties": {"original": {"type": "string", "description": "Exact quote as it appears in the transcript."},
                           "translation": {"type": "string", "description": "English translation. Same as original if already in English."}}}

def _jtbd_item_schema(job_type):
    stmt_desc = ("Canonical format: 'When I [situation], I want to [motivation], so I can [outcome].'"
                 if job_type == "functional" else f"Statement of the {job_type} job the participant is trying to satisfy.")
    return {"type": "object", "required": ["job_statement", "context", "quotes"],
            "properties": {"job_statement": {"type": "string", "description": stmt_desc},
                           "context": {"type": "string", "description": "Situational context in which this job arises."},
                           "quotes": {"type": "array", "items": _quote_schema()}}}

def _motivation_item_schema():
    return {"type": "object", "required": ["motivation", "description", "quotes"],
            "properties": {"motivation": {"type": "string", "description": "Short label for this motivation."},
                           "description": {"type": "string"},
                           "quotes": {"type": "array", "items": _quote_schema()}}}

ANALYSIS_SCHEMA = {
    "type": "object",
    "required": ["language", "participant_profile", "executive_summary", "key_themes",
                 "jobs_to_be_done", "pain_points", "motivations", "notable_quotes",
                 "opportunities", "researcher_notes"],
    "properties": {
        "language": {"type": "string", "description": "One of: 'arabic_darija', 'arabic_msa', 'english', 'french', 'mixed'."},
        "participant_profile": {"type": "object", "required": ["summary", "inferred_context"],
                                "properties": {"summary": {"type": "string"}, "inferred_context": {"type": "string"}}},
        "executive_summary": {"type": "string", "description": "3-5 sentence synthesis in English."},
        "key_themes": {"type": "array", "items": {
            "type": "object", "required": ["theme", "description", "frequency", "supporting_quotes"],
            "properties": {"theme": {"type": "string"}, "description": {"type": "string"},
                           "frequency": {"type": "string", "enum": ["high", "medium", "low"]},
                           "supporting_quotes": {"type": "array", "items": _quote_schema()}}}},
        "jobs_to_be_done": {"type": "object", "required": ["functional", "emotional", "social"],
                            "properties": {"functional": {"type": "array", "items": _jtbd_item_schema("functional")},
                                           "emotional": {"type": "array", "items": _jtbd_item_schema("emotional")},
                                           "social": {"type": "array", "items": _jtbd_item_schema("social")}}},
        "pain_points": {"type": "array", "items": {
            "type": "object", "required": ["pain", "description", "severity", "frequency", "current_workaround", "quotes"],
            "properties": {"pain": {"type": "string"}, "description": {"type": "string"},
                           "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                           "frequency": {"type": "string", "enum": ["always", "often", "sometimes", "rarely"]},
                           "current_workaround": {"type": "string"},
                           "quotes": {"type": "array", "items": _quote_schema()}}}},
        "motivations": {"type": "object", "required": ["goals", "desires", "fears"],
                        "properties": {"goals": {"type": "array", "items": _motivation_item_schema()},
                                       "desires": {"type": "array", "items": _motivation_item_schema()},
                                       "fears": {"type": "array", "items": _motivation_item_schema()}}},
        "notable_quotes": {"type": "array", "items": {
            "type": "object", "required": ["original", "translation", "why_notable"],
            "properties": {"original": {"type": "string"}, "translation": {"type": "string"},
                           "why_notable": {"type": "string"}}}},
        "opportunities": {"type": "array", "items": {
            "type": "object", "required": ["opportunity", "rationale", "linked_framework", "linked_item"],
            "properties": {"opportunity": {"type": "string"}, "rationale": {"type": "string"},
                           "linked_framework": {"type": "string",
                               "enum": ["jtbd_functional", "jtbd_emotional", "jtbd_social", "pain_point",
                                        "motivation_goal", "motivation_desire", "motivation_fear", "key_theme"]},
                           "linked_item": {"type": "string"}}}},
        "researcher_notes": {"type": "string"},
    }
}

SYSTEM_PROMPT = """\
You are an expert qualitative researcher and UX strategist specialising in user interview analysis. \
You are highly proficient in Arabic (both Darija — Moroccan dialectal Arabic — and MSA), English, French, \
and mixed-language interviews.

## Guidelines
1. **Language**: Transcripts may be Arabic Darija, MSA, English, French, or mixed. Preserve verbatim quotes \
in their original language. Provide an English translation for every quote.
2. **Framework fidelity**: JTBD functional jobs use "When I [situation], I want to [motivation], so I can [outcome]". \
Pain Points severity is based on emotional weight. Motivations distinguish stated goals from implicit desires and fears.
3. **Evidence-based**: Every insight MUST have at least one direct quote. Do NOT invent or paraphrase quotes. \
Return empty arrays when evidence is missing.
4. **Researcher value**: Opportunities are actionable directions. Researcher notes flag contradictions, ambiguities, \
and suggested follow-up questions.
5. **Output**: Use the `analyse_transcript` tool only. Labels/summaries in English. Quotes in original + English.
"""

ANALYSIS_TOOL_DEFINITION = {
    "name": "analyse_transcript",
    "description": "Submit the complete structured analysis of an interview transcript using the specified research frameworks.",
    "input_schema": ANALYSIS_SCHEMA,
}

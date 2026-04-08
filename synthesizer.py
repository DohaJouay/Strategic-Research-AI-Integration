"""
synthesizer.py — Core AI synthesis engine using Claude API.

Usage:
    from synthesizer import Synthesizer
    result = Synthesizer().analyse("interview.srt")
"""
import os, json, time
from dataclasses import dataclass
from typing import Optional
import anthropic
from transcript_parser import parse, TranscriptDocument
from frameworks import SYSTEM_PROMPT, ANALYSIS_TOOL_DEFINITION

DEFAULT_MODEL = "claude-sonnet-4-6"
WORD_COUNT_WARN_THRESHOLD = 15_000

@dataclass
class AnalysisResult:
    transcript: TranscriptDocument
    analysis: dict
    model_used: str
    input_tokens: int
    output_tokens: int
    elapsed_seconds: float

    @property
    def language(self): return self.analysis.get("language", "unknown")
    @property
    def executive_summary(self): return self.analysis.get("executive_summary", "")
    @property
    def key_themes(self): return self.analysis.get("key_themes", [])
    @property
    def pain_points(self): return self.analysis.get("pain_points", [])
    @property
    def jobs_to_be_done(self): return self.analysis.get("jobs_to_be_done", {})
    @property
    def motivations(self): return self.analysis.get("motivations", {})
    @property
    def opportunities(self): return self.analysis.get("opportunities", [])
    @property
    def notable_quotes(self): return self.analysis.get("notable_quotes", [])
    @property
    def researcher_notes(self): return self.analysis.get("researcher_notes", "")


class Synthesizer:
    def __init__(self, api_key=None, model=None, verbose=True):
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY not set. Export it or pass api_key= to Synthesizer().")
        self._client = anthropic.Anthropic(api_key=key)
        self._model = model or os.environ.get("SYNTHESIS_MODEL", DEFAULT_MODEL)
        self._verbose = verbose

    def analyse(self, filepath: str) -> AnalysisResult:
        self._log(f"Parsing transcript: {filepath}")
        transcript = parse(filepath)
        self._log(f"  Format: {transcript.format.upper()} | Words: {transcript.word_count} | Script: {transcript.language_hint}")
        if transcript.word_count > WORD_COUNT_WARN_THRESHOLD:
            self._log(f"  Warning: transcript is long ({transcript.word_count} words).")
        if transcript.word_count < 50:
            raise ValueError(f"Transcript too short ({transcript.word_count} words): {filepath}")
        self._log(f"Sending to Claude ({self._model})…")
        start = time.time()
        raw = self._call_claude(transcript)
        elapsed = time.time() - start
        self._log(f"  Done in {elapsed:.1f}s | Tokens: {raw['input_tokens']} in / {raw['output_tokens']} out")
        return AnalysisResult(transcript=transcript, analysis=raw["analysis"],
                              model_used=self._model, input_tokens=raw["input_tokens"],
                              output_tokens=raw["output_tokens"], elapsed_seconds=elapsed)

    def _call_claude(self, transcript):
        response = self._client.messages.create(
            model=self._model, max_tokens=8192, system=SYSTEM_PROMPT,
            tools=[ANALYSIS_TOOL_DEFINITION],
            tool_choice={"type": "tool", "name": "analyse_transcript"},
            messages=[{"role": "user", "content": self._build_user_message(transcript)}],
        )
        tool_block = next((b for b in response.content if b.type == "tool_use"), None)
        if not tool_block:
            raise RuntimeError(f"Claude did not return tool_use. Stop reason: {response.stop_reason}")
        analysis = tool_block.input
        if not isinstance(analysis, dict):
            analysis = json.loads(analysis)
        return {"analysis": analysis, "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens}

    def _build_user_message(self, transcript):
        notes = {"arabic": "NOTE: This transcript is in Arabic (Darija or MSA). Preserve all Arabic quotes verbatim.",
                 "latin":  "NOTE: This transcript is in a Latin-script language (English or French).",
                 "mixed":  "NOTE: This transcript is mixed-language (Arabic + Latin). Handle each segment in its original language."}
        header = "\n".join(filter(None, [
            "## Interview Transcript",
            f"**File:** {transcript.filename}",
            f"**Format:** {transcript.format.upper()}",
            f"**Word count:** {transcript.word_count}",
            f"**Estimated duration:** {transcript.estimated_duration_min:.1f} minutes" if transcript.estimated_duration_min > 0 else "",
            notes.get(transcript.language_hint, ""),
        ]))
        return f"{header}\n\n---\n\n{transcript.clean_text}\n\n---\n\nPlease analyse this transcript using the `analyse_transcript` tool."

    def _log(self, msg):
        if self._verbose:
            print(msg)

"""Explicit simulated model responses for program tests, never real trial results."""
import json
from model_adapter.contracts import ModelResponse


class FixtureAdapter:
    async def complete(self, request):
        question = json.loads(request.messages[1].content)
        data = json.loads(request.messages[2].content)
        evidence = data["evidence"][0]
        text = "SIMULATED DRAFT: " + question["question"]
        if "answer_id" not in question:
            return ModelResponse(json.dumps({"answer_units":[{"kind":"technical","text":text,
                "evidence_ids":[evidence["evidence_id"]]}],"assumptions":[],"missing_information":[],
                "evidence_sufficient":True}),"synthetic_fixture",finish_reason="fixture_stop")
        return ModelResponse(json.dumps({"answer_id": question["answer_id"], "version": 1,
            "text": text, "citations": [{"start_offset": 0, "end_offset": len(text),
            "evidence_ids": [evidence["evidence_id"]]}], "assumptions": [], "missing_information": [],
            "evidence_sufficient": True}), "synthetic_fixture", finish_reason="fixture_stop")

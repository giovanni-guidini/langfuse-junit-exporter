from dataclasses import dataclass
from typing import TypedDict
from langfuse.client import Langfuse

from langfuse.api.resources.commons.types.dataset_run_item import DatasetRunItem


class Score(TypedDict):
    name: str
    value: float


@dataclass
class GenericItemInfo:
    item_id: str
    trace_id: str
    cost: float | None
    duration: float | None
    scores: list[Score]

    def is_success(self, success_score_name: str) -> bool:
        return any(
            (score["name"] == success_score_name and score.get("value", 0) == 1)
            for score in self.scores
        )

    def to_junit(self, success_score_name: str) -> str:
        # Helper function to indent the XML output
        def ident(n: int, message: str) -> str:
            return " " * n + message

        lines: list[str] = [
            f"<testcase classname='langfuse' name='{self.item_id}' time='{self.duration}'>",
            ident(4, "<properties>"),
            ident(8, f"<property name='evals.trace_id' value='{self.trace_id}' />"),
        ]
        if self.cost is not None:
            lines.append(
                ident(8, f"<property name='evals.cost' value='{self.cost}' />")
            )

        if self.scores:
            # Add all scores to the properties
            for score in self.scores:
                # Score names can't have '.', so we replace them with '_'
                score_name = score["name"].replace(".", "_")
                lines.extend(
                    [
                        ident(
                            8,
                            f"<property name='evals.scores.{score_name}.value' value='{score['value']}' />",
                        ),
                    ]
                )
        lines.append(ident(4, "</properties>"))
        if not self.is_success(success_score_name):
            lines.append(
                ident(
                    4,
                    f"<failure message='Test case failed. {success_score_name} is either missing or its value is not 1.0' />",
                )
            )
        lines.append("</testcase>")
        return "\n".join(lines)

    @classmethod
    def from_langfuse_item(
        cls, langfuse_item: DatasetRunItem, langfuse: Langfuse
    ) -> "GenericItemInfo":
        trace = langfuse.fetch_trace(langfuse_item.trace_id)
        if trace is None:
            raise ValueError(f"Trace {langfuse_item.trace_id} not found")

        return GenericItemInfo(
            item_id=langfuse_item.id,
            trace_id=langfuse_item.trace_id,
            cost=trace.data.total_cost,
            duration=trace.data.latency,
            scores=[
                Score(
                    name=score.name,
                    value=score.value,
                )
                for score in trace.data.scores
                if score.value is not None
            ],
        )

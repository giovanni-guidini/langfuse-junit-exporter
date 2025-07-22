from functools import lru_cache
from collections import defaultdict

import click

from langfuse.client import Langfuse
from langfuse.api.resources.commons.errors import NotFoundError

from tqdm.auto import tqdm

from src.models import GenericItemInfo


def produce_junit_report(
    dataset_name: str, run_name: str, success_score_name: str, output_file: str | None
) -> None:
    output_fd = None if output_file is None else open(output_file, "w")
    generic_items = _get_dataset_run_items(dataset_name, run_name)
    if generic_items is None:
        return

    click.echo(
        f"<?xml version='1.0' encoding='UTF-8'?>\n<testsuite name='langfuse-eval' tests='{len(generic_items)}'>",
        file=output_fd,
    )
    for item in generic_items:
        click.echo(item.to_junit(success_score_name), file=output_fd)
    click.echo("</testsuite>", file=output_fd)
    if output_fd is not None:
        output_fd.close()


def produce_text_report(
    dataset_name: str, run_name: str, success_score_name: str, output_file: str | None
) -> None:
    output_fd = None if output_file is None else open(output_file, "w")
    generic_items = _get_dataset_run_items(dataset_name, run_name)
    if generic_items is None:
        return

    aggregate_scores = defaultdict(list)
    for item in generic_items:
        for score in item.scores:
            aggregate_scores[score["name"]].append(score["value"])

    output_fd = None if output_file is None else open(output_file, "w")

    click.echo(f"# Eval {run_name}", file=output_fd)
    click.echo(f"{len(generic_items)} items\n", file=output_fd)

    click.echo("# All scores\n", file=output_fd)
    for score_name, score_values in aggregate_scores.items():
        score_avg = (
            sum(score_values) / len(score_values) if len(score_values) > 0 else 0
        )
        click.echo(
            f"- {score_name}\n"
            f"  avg: {score_avg}\n"
            f"  count: {len(score_values)}\n"
            f"  sum: {sum(score_values)}",
            file=output_fd,
        )

    if output_fd is not None:
        output_fd.close()


@lru_cache
def _get_dataset_run_items(
    dataset_name: str, run_name: str
) -> list[GenericItemInfo] | None:
    langfuse = Langfuse()
    try:
        run = langfuse.get_dataset_run(dataset_name, run_name)
    except NotFoundError:
        click.secho(f"Run {run_name} not found in dataset {dataset_name}", fg="red")
        return

    dataset_run_items = run.dataset_run_items
    if dataset_run_items is None:
        click.secho(f"Run {run_name} has no items", fg="red")
        return

    return [
        GenericItemInfo.from_langfuse_item(item, langfuse)
        for item in tqdm(dataset_run_items, desc="Fetching traces")
    ]

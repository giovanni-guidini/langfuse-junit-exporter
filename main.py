"""
This module contains functions for getting run reports from Langfuse.

By default, the success-score-name is "did_item_pass".
"""

import click

import dotenv

from src.reporting import produce_junit_report, produce_text_report


@click.group()
def main():
    dotenv.load_dotenv()


@main.command()
@click.option("--dataset-name", type=str, required=True)
@click.option("--run-name", type=str, required=True)
@click.option(
    "--success-score-name",
    type=str,
    default="did_item_pass",
    help="The name of the score that indicates wether the item should be considered as 'pass' or 'fail'. It's expected to have values of 0 or 1.",
)
@click.option(
    "--report-type",
    type=click.Choice(["junit", "text"]),
    default="junit",
    help="The type of report to generate",
)
@click.option(
    "--output-file",
    type=str,
    default=None,
    help="The path to the file where the report should be saved (optional). If not provided, the report is printed to stdout.",
)
def report(
    dataset_name: str,
    run_name: str,
    success_score_name: str,
    report_type: str,
    output_file: str | None,
):
    """
    Generate a report for a dataset run and save it to a file or print it to stdout.

    Arguments:
        --dataset-name: Name of the dataset to generate the report for (required).
        --run-name: Name of the run within the dataset (required).
        --output-file: Path to the file where the report should be saved (optional). If not provided, the report is printed to stdout.
        --success-fn: Dotted path to a Python function (e.g., "my_module.my_function") that will be used to determine if an item is considered a success. The function should be importable and accept a single argument (the scores for an item). If not provided, all items are considered successful by default.

    The command fetches the specified dataset run, applies the success function to each item (if provided), and generates a JSON report. The report is either saved to the specified output file or printed to stdout.
    """
    if report_type == "junit":
        produce_junit_report(dataset_name, run_name, success_score_name, output_file)
    elif report_type == "text":
        produce_text_report(dataset_name, run_name, success_score_name, output_file)
    else:
        raise ValueError(f"Invalid report type: {report_type}")


if __name__ == "__main__":
    main()

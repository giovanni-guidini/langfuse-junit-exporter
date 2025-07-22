"""
Langfuse JUnit Exporter - CLI tool for generating reports from Langfuse dataset runs.

This module provides a command-line interface for exporting Langfuse evaluation runs
in different formats (JUnit XML and text) for integration with CI/CD pipelines
and reporting systems.

The tool fetches dataset runs from Langfuse, processes the evaluation scores,
and generates reports that can be used for:
- CI/CD integration (JUnit XML format)
- Human-readable summaries (text format)


By default, the success-score-name is "did_item_pass".
"""

import click

import dotenv

from src.reporting import produce_junit_report, produce_text_report


@click.group()
def main():
    dotenv.load_dotenv()


@main.command()
@click.option(
    "--dataset-name",
    type=str,
    required=True,
    help="Name of the Langfuse dataset containing the evaluation run to report on."
)
@click.option(
    "--run-name",
    type=str,
    required=True,
    help="Name of the specific run within the dataset to generate a report for."
)
@click.option(
    "--success-score-name",
    type=str,
    default="did_item_pass",
    help="Name of the evaluation score that determines if an item passes (value=1) or fails (value=0). Used for JUnit XML test case success/failure classification."
)
@click.option(
    "--report-type",
    type=click.Choice(["junit", "text"]),
    default="junit",
    help="Format of the generated report. 'junit' produces JUnit XML for CI/CD integration, 'text' produces human-readable summary with aggregated statistics."
)
@click.option(
    "--output-file",
    type=str,
    default=None,
    help="File path to save the report. If not specified, the report is printed to stdout."
)
def report(
    dataset_name: str,
    run_name: str,
    success_score_name: str,
    report_type: str,
    output_file: str | None,
):
    """
    Generate a report for a Langfuse dataset run in the specified format.

    This command fetches the specified dataset run from Langfuse, processes the
    evaluation scores, and generates a report in either JUnit XML or text format.
    The report can be saved to a file or printed to stdout for integration with
    CI/CD pipelines or analysis tools.

    Report Formats:
        - JUnit XML: Standard JUnit XML format for CI/CD integration. Each dataset
          item becomes a test case with properties for trace ID, cost, duration,
          and all evaluation scores. Failed items (success_score_name != 1) are
          marked as test failures.
        
        - Text: Human-readable format with aggregated statistics. Shows item count,
          average scores, and detailed breakdown of all evaluation metrics.

    Examples:
        # Generate JUnit XML report to stdout
        python main.py report --dataset-name "my-dataset" --run-name "test-run"

        # Generate text report to file
        python main.py report --dataset-name "my-dataset" --run-name "test-run" \\
                              --report-type text --output-file "report.txt"

        # Use custom success score name
        python main.py report --dataset-name "my-dataset" --run-name "test-run" \\
                              --success-score-name "accuracy"
    """
    if report_type == "junit":
        produce_junit_report(dataset_name, run_name, success_score_name, output_file)
    elif report_type == "text":
        produce_text_report(dataset_name, run_name, success_score_name, output_file)
    else:
        raise ValueError(f"Invalid report type: {report_type}")


if __name__ == "__main__":
    main()

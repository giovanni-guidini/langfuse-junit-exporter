# Langfuse JUnit Exporter

A command-line tool for exporting Langfuse evaluation runs in different formats for integration with CI/CD pipelines and reporting systems.

## Overview

Langfuse JUnit Exporter fetches dataset runs from Langfuse, processes evaluation scores, and generates reports that can be used for:

- **CI/CD Integration**: JUnit XML format for seamless integration with CI/CD pipelines
- **Human-readable Summaries**: Text format for analysis and reporting

## Installation

### Prerequisites

- Python 3.13 or higher
- Access to a Langfuse instance

### Install (with uv)

```bash
# Clone the repository
git clone https://github.com/giovanni-guidini/langfuse-junit-exporter.git
cd langfuse-junit-exporter

# Install dependencies and package
uv sync

# Use the tool (uv should have installed the script)
langfuse-reporter --help
```

### Environment Setup

Create a `.env` file in the project root with your Langfuse credentials:

```env
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com  # or your self-hosted instance
```

## Usage

### Basic Usage

Generate a JUnit XML report for a dataset run:

```bash
langfuse-reporter report --dataset-name "my-dataset" --run-name "test-run"
```

> Run `langfuse-reporter report --help` for all options

### Examples

#### Generate JUnit XML Report

```bash
# Print to console
langfuse-reporter report --dataset-name "evaluation-dataset" --run-name "v1.0-test"

# Save to file
langfuse-reporter report --dataset-name "evaluation-dataset" --run-name "v1.0-test" \
                        --output-file "test-results.xml"
```

#### Generate Text Report

```bash
# Print to console
langfuse-reporter report --dataset-name "evaluation-dataset" --run-name "v1.0-test" \
                        --report-type text

# Save to file
langfuse-reporter report --dataset-name "evaluation-dataset" --run-name "v1.0-test" \
                        --report-type text --output-file "summary.txt"
```

#### Custom Success Criteria

```bash
# Use 'accuracy' score instead of default 'did_item_pass'
langfuse-reporter report --dataset-name "evaluation-dataset" --run-name "v1.0-test" \
                        --success-score-name "accuracy"
```

## Report Formats

### JUnit XML Format

The JUnit XML format is designed for CI/CD integration. Each dataset item becomes a test case with:

- **Test case properties**: Trace ID, cost, duration
- **Evaluation scores**: All scores as properties with dot-to-underscore conversion
- **Success/failure status**: Based on the specified success score (1 = pass, 0 = fail)

**Example Output Structure:**
```xml
<?xml version='1.0' encoding='UTF-8'?>
<testsuite name='langfuse-eval' tests='2'>
<testcase classname='langfuse' name='item-1' time='2.5'>
    <properties>
        <property name='evals.trace_id' value='trace-123' />
        <property name='evals.cost' value='0.15' />
        <property name='evals.scores.accuracy.value' value='0.95' />
        <property name='evals.scores.did_item_pass.value' value='1.0' />
    </properties>
</testcase>
<testcase classname='langfuse' name='item-2' time='1.8'>
    <properties>
        <property name='evals.trace_id' value='trace-456' />
        <property name='evals.cost' value='0.12' />
        <property name='evals.scores.accuracy.value' value='0.75' />
        <property name='evals.scores.did_item_pass.value' value='0.0' />
    </properties>
    <failure message='Test case failed. did_item_pass is either missing or its value is not 1.0' />
</testcase>
</testsuite>
```

### Text Format

The text format provides human-readable summaries with aggregated statistics:

**Example Output:**
```
# Eval v1.0-test

2 items

# All scores

- accuracy
  avg: 0.85
  count: 2
  sum: 1.7

- did_item_pass
  avg: 0.5
  count: 2
  sum: 1.0
```

## Example Outputs

For detailed examples of both report formats, see the snapshot test files.

- **JUnit XML Examples**: `tests/snapshots/test_reporting/junit_report/`
- **Text Report Examples**: `tests/snapshots/test_reporting/text_report/`


## Development

### Setup Development Environment

```bash
# Clone and setup
git clone https://github.com/giovanni-guidini/langfuse-junit-exporter.git
cd langfuse-junit-exporter

# Install with dev dependencies
uv sync --group dev

# Run tests
uv run pytest

# Update snapshots
uv run pytest --snapshot-update
```

### Project Structure

```
langfuse-junit-exporter/
├── main.py              # CLI entry point
├── src/
│   ├── models.py        # Data models and JUnit XML generation
│   └── reporting.py     # Report generation functions
├── tests/
│   ├── test_models.py   # Unit tests for models
│   ├── test_reporting.py # Unit tests for reporting
│   └── snapshots/       # Snapshot test examples
└── pyproject.toml       # Project configuration
```

## License

[Add your license information here]
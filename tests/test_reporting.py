import pytest
from unittest.mock import Mock, patch, mock_open
import tempfile
import os

from src.reporting import produce_junit_report, produce_text_report, _get_dataset_run_items
from langfuse.api.resources.commons.errors import NotFoundError, UnauthorizedError
from langfuse.api.resources.commons.types.dataset_run_item import DatasetRunItem


class TestProduceJunitReport:
    """Test cases for produce_junit_report function."""

    def setup_method(self):
        """Clear the cache before each test."""
        _get_dataset_run_items.cache_clear()

    @pytest.fixture
    def mock_langfuse(self):
        """Mock Langfuse client."""
        return Mock()

    @pytest.fixture
    def mock_dataset_run_item(self):
        """Mock dataset run item."""
        item = Mock(spec=DatasetRunItem)
        item.id = "test-item-123"
        item.trace_id = "test-trace-456"
        return item

    @pytest.fixture
    def mock_trace(self):
        """Mock trace with scores."""
        mock_score1 = Mock()
        mock_score1.name = "accuracy"
        mock_score1.value = 0.95

        mock_score2 = Mock()
        mock_score2.name = "success"
        mock_score2.value = 1.0

        mock_trace_data = Mock()
        mock_trace_data.total_cost = 0.25
        mock_trace_data.latency = 2.5
        mock_trace_data.scores = [mock_score1, mock_score2]

        mock_trace = Mock()
        mock_trace.data = mock_trace_data
        return mock_trace

    @pytest.fixture
    def mock_run(self, mock_dataset_run_item):
        """Mock dataset run."""
        run = Mock()
        run.dataset_run_items = [mock_dataset_run_item]
        return run

    @patch("src.reporting.Langfuse")
    def test_produce_junit_report_success_to_stdout(
        self, mock_langfuse_class, mock_langfuse, mock_run, mock_trace, capsys
    ):
        """Test produce_junit_report writes to stdout when output_file is None."""
        # Setup mocks
        mock_langfuse_class.return_value = mock_langfuse
        mock_langfuse.get_dataset_run.return_value = mock_run
        mock_langfuse.fetch_trace.return_value = mock_trace

        # Call function
        produce_junit_report("test-dataset", "test-run", "success", None)

        # Verify Langfuse was called correctly
        mock_langfuse.get_dataset_run.assert_called_once_with(
            "test-dataset", "test-run"
        )
        mock_langfuse.fetch_trace.assert_called_once_with("test-trace-456")

        # Capture stdout output
        captured = capsys.readouterr()
        output = captured.out

        # Verify output contains expected XML
        assert "<?xml version='1.0' encoding='UTF-8'?>" in output
        assert "<testsuite name='langfuse-eval' tests='1'>" in output
        assert "<testcase classname='langfuse' name='test-item-123'" in output
        assert "<property name='evals.trace_id' value='test-trace-456' />" in output
        assert "<property name='evals.scores.success.value' value='1.0' />" in output
        assert "</testsuite>" in output

    @patch("src.reporting.Langfuse")
    def test_produce_junit_report_success_to_file(
        self, mock_langfuse_class, mock_langfuse, mock_run, mock_trace
    ):
        """Test produce_junit_report writes to file when output_file is provided."""
        # Setup mocks
        mock_langfuse_class.return_value = mock_langfuse
        mock_langfuse.get_dataset_run.return_value = mock_run
        mock_langfuse.fetch_trace.return_value = mock_trace

        # Use temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
            temp_filename = temp_file.name

        try:
            # Call function
            produce_junit_report("test-dataset", "test-run", "success", temp_filename)

            # Read the file content
            with open(temp_filename, "r") as f:
                content = f.read()

            # Verify content
            assert "<?xml version='1.0' encoding='UTF-8'?>" in content
            assert "<testsuite name='langfuse-eval' tests='1'>" in content
            assert "<testcase classname='langfuse' name='test-item-123'" in content
            assert (
                "<property name='evals.trace_id' value='test-trace-456' />" in content
            )
            assert (
                "<property name='evals.scores.success.value' value='1.0' />" in content
            )
            assert "</testsuite>" in content

        finally:
            # Cleanup
            os.unlink(temp_filename)

    @patch("src.reporting.Langfuse")
    def test_produce_junit_report_not_found_error(
        self, mock_langfuse_class, mock_langfuse, capsys
    ):
        """Test produce_junit_report handles NotFoundError gracefully."""
        # Setup mocks
        mock_langfuse_class.return_value = mock_langfuse
        mock_langfuse.get_dataset_run.side_effect = NotFoundError("Not found")

        # Should not raise exception
        produce_junit_report("nonexistent-dataset", "nonexistent-run", "success", None)

        # Verify Langfuse was called
        mock_langfuse.get_dataset_run.assert_called_once_with(
            "nonexistent-dataset", "nonexistent-run"
        )

        # Verify error message was printed
        captured = capsys.readouterr()
        assert (
            "Run nonexistent-run not found in dataset nonexistent-dataset"
            in captured.out
        )

    @patch("src.reporting.Langfuse")
    def test_produce_junit_report_no_dataset_items(
        self, mock_langfuse_class, mock_langfuse, capsys
    ):
        """Test produce_junit_report handles case when dataset_run_items is None."""
        # Setup mocks
        mock_langfuse_class.return_value = mock_langfuse
        mock_run = Mock()
        mock_run.dataset_run_items = None
        mock_langfuse.get_dataset_run.return_value = mock_run

        # Call function
        produce_junit_report("test-dataset", "test-run", "success", None)

        # Verify error message was printed
        captured = capsys.readouterr()
        assert "Run test-run has no items" in captured.out

    @patch("src.reporting.Langfuse")
    def test_produce_junit_report_unauthorized_error(
        self, mock_langfuse_class, mock_langfuse, capsys
    ):
        """Test produce_junit_report handles UnauthorizedError from Langfuse."""
        # Setup mocks
        mock_langfuse_class.return_value = mock_langfuse
        mock_langfuse.get_dataset_run.side_effect = UnauthorizedError("Invalid credentials")

        # Call function
        produce_junit_report("test-dataset", "test-run", "success", None)

        # Verify error message was printed
        captured = capsys.readouterr()
        assert "Could not access Langfuse. Please check your .env file" in captured.out

    @patch("src.reporting.Langfuse")
    def test_produce_junit_report_general_exception(
        self, mock_langfuse_class, mock_langfuse, capsys
    ):
        """Test produce_junit_report handles general exceptions from Langfuse."""
        # Setup mocks
        mock_langfuse_class.return_value = mock_langfuse
        mock_langfuse.get_dataset_run.side_effect = Exception("Network timeout")

        # Call function
        produce_junit_report("test-dataset", "test-run", "success", None)

        # Verify error message was printed
        captured = capsys.readouterr()
        assert "Unknown error fetching items: Network timeout" in captured.out

    @patch("src.reporting.Langfuse")
    def test_produce_junit_report_multiple_items(
        self, mock_langfuse_class, mock_langfuse, mock_trace, capsys
    ):
        """Test produce_junit_report with multiple dataset items."""
        # Setup multiple items
        item1 = Mock(spec=DatasetRunItem)
        item1.id = "item-1"
        item1.trace_id = "trace-1"

        item2 = Mock(spec=DatasetRunItem)
        item2.id = "item-2"
        item2.trace_id = "trace-2"

        mock_run = Mock()
        mock_run.dataset_run_items = [item1, item2]

        # Setup mocks
        mock_langfuse_class.return_value = mock_langfuse
        mock_langfuse.get_dataset_run.return_value = mock_run
        mock_langfuse.fetch_trace.return_value = mock_trace

        # Call function
        produce_junit_report("test-dataset", "test-run", "success", None)

        # Verify fetch_trace was called for each item
        assert mock_langfuse.fetch_trace.call_count == 2
        mock_langfuse.fetch_trace.assert_any_call("trace-1")
        mock_langfuse.fetch_trace.assert_any_call("trace-2")

        # Capture stdout output
        captured = capsys.readouterr()
        output = captured.out

        # Check XML header has correct test count
        assert "<testsuite name='langfuse-eval' tests='2'>" in output

    @patch("src.reporting.Langfuse")
    def test_produce_junit_report_with_failure_case(
        self, mock_langfuse_class, mock_langfuse, capsys
    ):
        """Test produce_junit_report with a test case that fails."""
        # Setup item
        item = Mock(spec=DatasetRunItem)
        item.id = "failing-item"
        item.trace_id = "failing-trace"

        # Setup trace with no success score
        mock_score = Mock()
        mock_score.name = "accuracy"
        mock_score.value = 0.5

        mock_trace_data = Mock()
        mock_trace_data.total_cost = 0.1
        mock_trace_data.latency = 1.0
        mock_trace_data.scores = [mock_score]

        mock_trace = Mock()
        mock_trace.data = mock_trace_data

        mock_run = Mock()
        mock_run.dataset_run_items = [item]

        # Setup mocks
        mock_langfuse_class.return_value = mock_langfuse
        mock_langfuse.get_dataset_run.return_value = mock_run
        mock_langfuse.fetch_trace.return_value = mock_trace

        # Call function
        produce_junit_report("test-dataset", "test-run", "success", None)

        # Capture stdout output
        captured = capsys.readouterr()
        output = captured.out

        # Check that failure tag is present
        assert (
            "<failure message='Test case failed. success is either missing or its value is not 1.0' />"
            in output
        )

    @patch("src.reporting.Langfuse")
    def test_produce_junit_report_empty_dataset(
        self, mock_langfuse_class, mock_langfuse, capsys
    ):
        """Test produce_junit_report with empty dataset."""
        # Setup empty run
        mock_run = Mock()
        mock_run.dataset_run_items = []

        # Setup mocks
        mock_langfuse_class.return_value = mock_langfuse
        mock_langfuse.get_dataset_run.return_value = mock_run

        # Call function
        produce_junit_report("test-dataset", "test-run", "success", None)

        # Capture stdout output
        captured = capsys.readouterr()
        output = captured.out

        # Verify click.echo was called with empty testsuite
        assert "<testsuite name='langfuse-eval' tests='0'>" in output

    @patch("src.reporting.Langfuse")
    def test_produce_junit_report_file_handling(
        self, mock_langfuse_class, mock_langfuse, mock_run, mock_trace
    ):
        """Test produce_junit_report properly handles file operations."""
        # Setup mocks
        mock_langfuse_class.return_value = mock_langfuse
        mock_langfuse.get_dataset_run.return_value = mock_run
        mock_langfuse.fetch_trace.return_value = mock_trace

        # Mock file operations
        mock_file = mock_open()

        with patch("builtins.open", mock_file):
            produce_junit_report("test-dataset", "test-run", "success", "test.xml")

            # Verify file was opened and closed
            mock_file.assert_called_once_with("test.xml", "w")
            mock_file().close.assert_called_once()

    @patch("src.reporting.Langfuse")
    def test_produce_junit_report_with_dots_in_score_names(
        self, mock_langfuse_class, mock_langfuse, capsys
    ):
        """Test produce_junit_report handles dots in score names correctly."""
        # Setup item
        item = Mock(spec=DatasetRunItem)
        item.id = "test-item"
        item.trace_id = "test-trace"

        # Setup trace with score containing dots
        mock_score = Mock()
        mock_score.name = "test.score"
        mock_score.value = 0.8

        mock_trace_data = Mock()
        mock_trace_data.total_cost = 0.1
        mock_trace_data.latency = 1.0
        mock_trace_data.scores = [mock_score]

        mock_trace = Mock()
        mock_trace.data = mock_trace_data

        mock_run = Mock()
        mock_run.dataset_run_items = [item]

        # Setup mocks
        mock_langfuse_class.return_value = mock_langfuse
        mock_langfuse.get_dataset_run.return_value = mock_run
        mock_langfuse.fetch_trace.return_value = mock_trace

        # Call function
        produce_junit_report("test-dataset", "test-run", "test.score", None)

        # Capture stdout output
        captured = capsys.readouterr()
        output = captured.out

        # Check that dots are replaced with underscores in property names
        assert "<property name='evals.scores.test_score.value' value='0.8' />" in output

    @patch("src.reporting.Langfuse")
    def test_produce_junit_report_with_none_values(
        self, mock_langfuse_class, mock_langfuse, capsys
    ):
        """Test produce_junit_report handles None values in trace data."""
        # Setup item
        item = Mock(spec=DatasetRunItem)
        item.id = "test-item"
        item.trace_id = "test-trace"

        # Setup trace with None values
        mock_trace_data = Mock()
        mock_trace_data.total_cost = None
        mock_trace_data.latency = None
        mock_trace_data.scores = []

        mock_trace = Mock()
        mock_trace.data = mock_trace_data

        mock_run = Mock()
        mock_run.dataset_run_items = [item]

        # Setup mocks
        mock_langfuse_class.return_value = mock_langfuse
        mock_langfuse.get_dataset_run.return_value = mock_run
        mock_langfuse.fetch_trace.return_value = mock_trace

        # Call function
        produce_junit_report("test-dataset", "test-run", "success", None)

        # Capture stdout output
        captured = capsys.readouterr()
        output = captured.out

        # Check that cost property is not included when None
        assert "<property name='evals.cost'" not in output
        assert "<property name='evals.trace_id' value='test-trace' />" in output


class TestProduceJunitReportSnapshots:
    """Snapshot tests for produce_junit_report function."""

    def setup_method(self):
        """Clear the cache before each test."""
        _get_dataset_run_items.cache_clear()

    @pytest.fixture
    def snapshot_configured(self, snapshot):
        """Snapshot fixture."""
        snapshot.snapshot_dir = "tests/snapshots/test_reporting/junit_report"
        return snapshot

    @patch("src.reporting.Langfuse")
    def test_produce_junit_report_success_snapshot(
        self, mock_langfuse_class, snapshot_configured, capsys
    ):
        """Snapshot test for successful JUnit report generation."""
        # Setup mocks
        mock_langfuse = Mock()
        mock_langfuse_class.return_value = mock_langfuse

        # Setup item
        item = Mock(spec=DatasetRunItem)
        item.id = "snapshot-test-item"
        item.trace_id = "snapshot-test-trace"

        # Setup trace
        mock_score1 = Mock()
        mock_score1.name = "accuracy"
        mock_score1.value = 0.95

        mock_score2 = Mock()
        mock_score2.name = "success"
        mock_score2.value = 1.0

        mock_trace_data = Mock()
        mock_trace_data.total_cost = 0.25
        mock_trace_data.latency = 2.5
        mock_trace_data.scores = [mock_score1, mock_score2]

        mock_trace = Mock()
        mock_trace.data = mock_trace_data

        mock_run = Mock()
        mock_run.dataset_run_items = [item]

        mock_langfuse.get_dataset_run.return_value = mock_run
        mock_langfuse.fetch_trace.return_value = mock_trace

        # Call function
        produce_junit_report("test-dataset", "test-run", "success", None)

        # Capture stdout output
        captured = capsys.readouterr()
        full_output = captured.out

        # Compare with snapshot
        snapshot_configured.assert_match(full_output, "junit_report_success.xml")

    @patch("src.reporting.Langfuse")
    def test_produce_junit_report_failure_snapshot(
        self, mock_langfuse_class, snapshot_configured, capsys
    ):
        """Snapshot test for failed JUnit report generation."""
        # Setup mocks
        mock_langfuse = Mock()
        mock_langfuse_class.return_value = mock_langfuse

        # Setup item
        item = Mock(spec=DatasetRunItem)
        item.id = "failing-snapshot-item"
        item.trace_id = "failing-snapshot-trace"

        # Setup trace with no success score
        mock_score = Mock()
        mock_score.name = "accuracy"
        mock_score.value = 0.5

        mock_trace_data = Mock()
        mock_trace_data.total_cost = 0.1
        mock_trace_data.latency = 1.0
        mock_trace_data.scores = [mock_score]

        mock_trace = Mock()
        mock_trace.data = mock_trace_data

        mock_run = Mock()
        mock_run.dataset_run_items = [item]

        mock_langfuse.get_dataset_run.return_value = mock_run
        mock_langfuse.fetch_trace.return_value = mock_trace

        # Call function
        produce_junit_report("test-dataset", "test-run", "success", None)

        # Capture stdout output
        captured = capsys.readouterr()
        full_output = captured.out

        # Compare with snapshot
        snapshot_configured.assert_match(full_output, "junit_report_failure.xml")

    @patch("src.reporting.Langfuse")
    def test_produce_junit_report_multiple_items_snapshot(
        self, mock_langfuse_class, snapshot_configured, capsys
    ):
        """Snapshot test for JUnit report with multiple items."""
        # Setup mocks
        mock_langfuse = Mock()
        mock_langfuse_class.return_value = mock_langfuse

        # Setup multiple items
        item1 = Mock(spec=DatasetRunItem)
        item1.id = "multi-item-1"
        item1.trace_id = "multi-trace-1"

        item2 = Mock(spec=DatasetRunItem)
        item2.id = "multi-item-2"
        item2.trace_id = "multi-trace-2"

        # Setup trace data
        mock_score1 = Mock()
        mock_score1.name = "success"
        mock_score1.value = 1.0

        mock_score2 = Mock()
        mock_score2.name = "accuracy"
        mock_score2.value = 0.8

        mock_trace_data = Mock()
        mock_trace_data.total_cost = 0.15
        mock_trace_data.latency = 1.5
        mock_trace_data.scores = [mock_score1, mock_score2]

        mock_trace = Mock()
        mock_trace.data = mock_trace_data

        mock_run = Mock()
        mock_run.dataset_run_items = [item1, item2]

        mock_langfuse.get_dataset_run.return_value = mock_run
        mock_langfuse.fetch_trace.return_value = mock_trace

        # Call function
        produce_junit_report("test-dataset", "test-run", "success", None)

        # Capture stdout output
        captured = capsys.readouterr()
        full_output = captured.out

        # Compare with snapshot
        snapshot_configured.assert_match(full_output, "junit_report_multiple_items.xml")

    @patch("src.reporting.Langfuse")
    def test_produce_junit_report_empty_snapshot(
        self, mock_langfuse_class, snapshot_configured, capsys
    ):
        """Snapshot test for empty JUnit report."""
        # Setup mocks
        mock_langfuse = Mock()
        mock_langfuse_class.return_value = mock_langfuse

        mock_run = Mock()
        mock_run.dataset_run_items = []

        mock_langfuse.get_dataset_run.return_value = mock_run

        # Call function
        produce_junit_report("test-dataset", "test-run", "success", None)

        # Capture stdout output
        captured = capsys.readouterr()
        full_output = captured.out

        # Compare with snapshot
        snapshot_configured.assert_match(full_output, "junit_report_empty.xml")

class TestProduceTextReportSnapshots:
    """Snapshot tests for produce_text_report function."""

    @pytest.fixture
    def snapshot_configured(self, snapshot):
        """Snapshot fixture."""
        snapshot.snapshot_dir = "tests/snapshots/test_reporting/text_report"
        return snapshot

    def setup_method(self):
        """Clear the cache before each test."""
        _get_dataset_run_items.cache_clear()

    @patch("src.reporting.Langfuse")
    def test_produce_text_report_success_snapshot(
        self, mock_langfuse_class, snapshot_configured, capsys
    ):
        """Snapshot test for successful text report generation."""
        # Setup mocks
        mock_langfuse = Mock()
        mock_langfuse_class.return_value = mock_langfuse

        # Setup item
        item = Mock(spec=DatasetRunItem)
        item.id = "text-test-item"
        item.trace_id = "text-test-trace"

        # Setup trace with multiple scores
        mock_score1 = Mock()
        mock_score1.name = "accuracy"
        mock_score1.value = 0.95

        mock_score2 = Mock()
        mock_score2.name = "precision"
        mock_score2.value = 0.88

        mock_score3 = Mock()
        mock_score3.name = "recall"
        mock_score3.value = 0.92

        mock_trace_data = Mock()
        mock_trace_data.total_cost = 0.25
        mock_trace_data.latency = 2.5
        mock_trace_data.scores = [mock_score1, mock_score2, mock_score3]

        mock_trace = Mock()
        mock_trace.data = mock_trace_data

        # Create mock run with specific item
        mock_run = Mock()
        mock_run.dataset_run_items = [item]

        mock_langfuse.get_dataset_run.return_value = mock_run
        mock_langfuse.fetch_trace.return_value = mock_trace

        # Call function
        produce_text_report("test-dataset", "test-run", "success", None)

        # Capture stdout output
        captured = capsys.readouterr()
        full_output = captured.out

        # Compare with snapshot
        snapshot_configured.assert_match(full_output, "text_report_success.txt")

    @patch("src.reporting.Langfuse")
    def test_produce_text_report_multiple_items_snapshot(
        self, mock_langfuse_class, snapshot_configured, capsys
    ):
        """Snapshot test for text report with multiple items."""
        # Setup mocks
        mock_langfuse = Mock()
        mock_langfuse_class.return_value = mock_langfuse

        # Setup multiple items
        item1 = Mock(spec=DatasetRunItem)
        item1.id = "text-item-1"
        item1.trace_id = "text-trace-1"

        item2 = Mock(spec=DatasetRunItem)
        item2.id = "text-item-2"
        item2.trace_id = "text-trace-2"

        # Setup trace data with different scores for each item
        mock_score1 = Mock()
        mock_score1.name = "accuracy"
        mock_score1.value = 0.8

        mock_score2 = Mock()
        mock_score2.name = "precision"
        mock_score2.value = 0.75

        mock_trace_data = Mock()
        mock_trace_data.total_cost = 0.15
        mock_trace_data.latency = 1.5
        mock_trace_data.scores = [mock_score1, mock_score2]

        mock_trace = Mock()
        mock_trace.data = mock_trace_data

        # Create mock run with specific items
        mock_run = Mock()
        mock_run.dataset_run_items = [item1, item2]

        mock_langfuse.get_dataset_run.return_value = mock_run
        mock_langfuse.fetch_trace.return_value = mock_trace

        # Call function
        produce_text_report("test-dataset", "test-run", "success", None)

        # Capture stdout output
        captured = capsys.readouterr()
        full_output = captured.out

        # Compare with snapshot
        snapshot_configured.assert_match(full_output, "text_report_multiple_items.txt")

    @patch("src.reporting.Langfuse")
    def test_produce_text_report_empty_snapshot(
        self, mock_langfuse_class, snapshot_configured, capsys
    ):
        """Snapshot test for empty text report."""
        # Setup mocks
        mock_langfuse = Mock()
        mock_langfuse_class.return_value = mock_langfuse

        # Create mock run with empty items
        mock_run = Mock()
        mock_run.dataset_run_items = []

        mock_langfuse.get_dataset_run.return_value = mock_run

        # Call function
        produce_text_report("test-dataset", "test-run", "success", None)

        # Capture stdout output
        captured = capsys.readouterr()
        full_output = captured.out

        # Compare with snapshot
        snapshot_configured.assert_match(full_output, "text_report_empty.txt")

    @patch("src.reporting.Langfuse")
    def test_produce_text_report_no_scores_snapshot(
        self, mock_langfuse_class, snapshot_configured, capsys
    ):
        """Snapshot test for text report with items but no scores."""
        # Setup mocks
        mock_langfuse = Mock()
        mock_langfuse_class.return_value = mock_langfuse

        # Setup item
        item = Mock(spec=DatasetRunItem)
        item.id = "no-scores-item"
        item.trace_id = "no-scores-trace"

        # Setup trace with no scores
        mock_trace_data = Mock()
        mock_trace_data.total_cost = 0.1
        mock_trace_data.latency = 1.0
        mock_trace_data.scores = []

        mock_trace = Mock()
        mock_trace.data = mock_trace_data

        # Create mock run with specific item
        mock_run = Mock()
        mock_run.dataset_run_items = [item]

        mock_langfuse.get_dataset_run.return_value = mock_run
        mock_langfuse.fetch_trace.return_value = mock_trace

        # Call function
        produce_text_report("test-dataset", "test-run", "success", None)

        # Capture stdout output
        captured = capsys.readouterr()
        full_output = captured.out

        # Compare with snapshot
        snapshot_configured.assert_match(full_output, "text_report_no_scores.txt")

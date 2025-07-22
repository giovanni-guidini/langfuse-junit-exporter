import textwrap
import pytest
from unittest.mock import Mock
from src.models import GenericItemInfo, Score
from langfuse.api.resources.commons.types.dataset_run_item import DatasetRunItem


class TestGenericItemInfo:
    """Test cases for GenericItemInfo class."""

    @pytest.fixture
    def sample_scores(self) -> list[Score]:
        """Sample scores for testing."""
        return [
            Score(name="accuracy", value=0.95),
            Score(name="precision", value=0.88),
            Score(name="success", value=1.0),
            Score(name="false-positives", value=0),
        ]

    @pytest.fixture
    def sample_item_info(self, sample_scores) -> GenericItemInfo:
        """Sample GenericItemInfo instance for testing."""
        return GenericItemInfo(
            item_id="test-item-123",
            trace_id="test-trace-456",
            cost=0.15,
            duration=2.5,
            scores=sample_scores,
        )

    @pytest.mark.parametrize(
        "success_score_name,expected",
        [
            ("success", True),
            ("accuracy", False),
            ("false-positives", False),
            ("nonexistent", False),
        ],
    )
    def test_is_success(
        self, sample_item_info: GenericItemInfo, success_score_name: str, expected: bool
    ):
        """Test is_success method with different score names."""
        result = sample_item_info.is_success(success_score_name)
        assert result == expected

    @pytest.mark.parametrize(
        "scores,success_score_name,expected",
        [
            ([Score(name="success", value=1.0)], "success", True),
            ([Score(name="success", value=0.0)], "success", False),
            ([Score(name="success", value=0.5)], "success", False),
            ([Score(name="other", value=1.0)], "success", False),
            ([], "success", False),
        ],
    )
    def test_is_success_edge_cases(
        self, scores: list[Score], success_score_name: str, expected: bool
    ):
        """Test is_success method with edge cases."""
        item = GenericItemInfo(
            item_id="test",
            trace_id="trace",
            cost=None,
            duration=None,
            scores=scores,
        )
        result = item.is_success(success_score_name)
        assert result == expected

    def test_to_junit_success_case(self, sample_item_info: GenericItemInfo):
        """Test to_junit method for successful test case."""
        result = sample_item_info.to_junit("success")

        expected_junit = textwrap.dedent(
            """\
            <testcase classname='langfuse' name='test-item-123' time='2.5'>
                <properties>
                    <property name='evals.trace_id' value='test-trace-456' />
                    <property name='evals.cost' value='0.15' />
                    <property name='evals.scores.accuracy.value' value='0.95' />
                    <property name='evals.scores.precision.value' value='0.88' />
                    <property name='evals.scores.success.value' value='1.0' />
                    <property name='evals.scores.false-positives.value' value='0' />
                </properties>
            </testcase>"""
        )

        assert result == expected_junit

    def test_to_junit_failure_case(self, sample_item_info):
        """Test to_junit method for failed test case."""
        result = sample_item_info.to_junit("nonexistent_score")

        expected_junit = textwrap.dedent(
            """\
            <testcase classname='langfuse' name='test-item-123' time='2.5'>
                <properties>
                    <property name='evals.trace_id' value='test-trace-456' />
                    <property name='evals.cost' value='0.15' />
                    <property name='evals.scores.accuracy.value' value='0.95' />
                    <property name='evals.scores.precision.value' value='0.88' />
                    <property name='evals.scores.success.value' value='1.0' />
                    <property name='evals.scores.false-positives.value' value='0' />
                </properties>
                <failure message='Test case failed. nonexistent_score is either missing or its value is not 1.0' />
            </testcase>"""
        )

        assert result == expected_junit

    def test_to_junit_with_none_cost(self):
        """Test to_junit method when cost is None."""
        item = GenericItemInfo(
            item_id="test",
            trace_id="trace",
            cost=None,
            duration=1.0,
            scores=[Score(name="success", value=1.0)],
        )
        result = item.to_junit("success")

        # Should not include cost property
        assert "<property name='evals.cost'" not in result
        assert "<property name='evals.trace_id' value='trace' />" in result

    def test_to_junit_with_dot_in_score_name(self):
        """Test to_junit method with dots in score names."""
        item = GenericItemInfo(
            item_id="test",
            trace_id="trace",
            cost=1.0,
            duration=1.0,
            scores=[Score(name="test.score", value=1)],
        )
        result = item.to_junit("test.score")

        expected_junit = textwrap.dedent(
            """\
            <testcase classname='langfuse' name='test' time='1.0'>
                <properties>
                    <property name='evals.trace_id' value='trace' />
                    <property name='evals.cost' value='1.0' />
                    <property name='evals.scores.test_score.value' value='1' />
                </properties>
            </testcase>"""
        )
        assert result == expected_junit

    def test_to_junit_with_no_scores(self):
        """Test to_junit method with no scores."""
        item = GenericItemInfo(
            item_id="test",
            trace_id="trace",
            cost=1.0,
            duration=1.0,
            scores=[],
        )
        result = item.to_junit("success")

        expected_junit = textwrap.dedent(
            """\
            <testcase classname='langfuse' name='test' time='1.0'>
                <properties>
                    <property name='evals.trace_id' value='trace' />
                    <property name='evals.cost' value='1.0' />
                </properties>
                <failure message='Test case failed. success is either missing or its value is not 1.0' />
            </testcase>"""
        )
        assert result == expected_junit


class TestGenericItemInfoFromLangfuseItem:
    """Test cases for from_langfuse_item class method."""

    def test_from_langfuse_item_success(self):
        """Test successful creation from Langfuse item."""
        # Mock the DatasetRunItem
        mock_item = Mock(spec=DatasetRunItem)
        mock_item.id = "test-item-id"
        mock_item.trace_id = "test-trace-id"

        # Mock the trace data
        mock_score1 = Mock()
        mock_score1.name = "accuracy"
        mock_score1.value = 0.95

        mock_score2 = Mock()
        mock_score2.name = "success"
        mock_score2.value = 1.0

        mock_score3 = Mock()
        mock_score3.name = "null_score"
        mock_score3.value = None

        mock_trace_data = Mock()
        mock_trace_data.total_cost = 0.25
        mock_trace_data.latency = 3.5
        mock_trace_data.scores = [mock_score1, mock_score2, mock_score3]

        mock_trace = Mock()
        mock_trace.data = mock_trace_data

        # Mock the Langfuse client
        mock_langfuse = Mock()
        mock_langfuse.fetch_trace.return_value = mock_trace

        # Call the method
        result = GenericItemInfo.from_langfuse_item(mock_item, mock_langfuse)

        # Verify the result
        assert result.item_id == "test-item-id"
        assert result.trace_id == "test-trace-id"
        assert result.cost == 0.25
        assert result.duration == 3.5
        assert len(result.scores) == 2  # Should exclude None value score

        # Check scores
        score_names = [score["name"] for score in result.scores]
        score_values = [score["value"] for score in result.scores]
        assert "accuracy" in score_names
        assert "success" in score_names
        assert "null_score" not in score_names
        assert 0.95 in score_values
        assert 1.0 in score_values

        # Verify fetch_trace was called
        mock_langfuse.fetch_trace.assert_called_once_with("test-trace-id")

    def test_from_langfuse_item_trace_not_found(self):
        """Test from_langfuse_item when trace is not found."""
        mock_item = Mock(spec=DatasetRunItem)
        mock_item.trace_id = "nonexistent-trace"

        mock_langfuse = Mock()
        mock_langfuse.fetch_trace.return_value = None

        # Should raise ValueError
        with pytest.raises(ValueError, match="Trace nonexistent-trace not found"):
            GenericItemInfo.from_langfuse_item(mock_item, mock_langfuse)

    def test_from_langfuse_item_with_none_values(self):
        """Test from_langfuse_item with None values in trace data."""
        mock_item = Mock(spec=DatasetRunItem)
        mock_item.id = "test-item-id"
        mock_item.trace_id = "test-trace-id"

        mock_trace_data = Mock()
        mock_trace_data.total_cost = None
        mock_trace_data.latency = None
        mock_trace_data.scores = []

        mock_trace = Mock()
        mock_trace.data = mock_trace_data

        mock_langfuse = Mock()
        mock_langfuse.fetch_trace.return_value = mock_trace

        result = GenericItemInfo.from_langfuse_item(mock_item, mock_langfuse)

        assert result.item_id == "test-item-id"
        assert result.trace_id == "test-trace-id"
        assert result.cost is None
        assert result.duration is None
        assert result.scores == []

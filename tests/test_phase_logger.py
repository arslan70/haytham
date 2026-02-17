"""Tests for stage-level logging system.

Updated for stage-based API - uses stage_slug/stage_name instead of phase_number/phase_name.
Tests the StageLogger (imported via backward-compat aliases PhaseLogger/PhaseLogEntry).
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

from haytham.agents.utils.phase_logger import PhaseLogEntry, PhaseLogger


@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for test logs."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def phase_logger(temp_log_dir):
    """Create a PhaseLogger (StageLogger) instance with temporary directory."""
    return PhaseLogger(base_log_dir=temp_log_dir)


def test_phase_logger_initialization(temp_log_dir):
    """Test PhaseLogger initialization creates base directory."""
    logger = PhaseLogger(base_log_dir=temp_log_dir)
    assert Path(temp_log_dir).exists()
    assert logger.base_log_dir == Path(temp_log_dir)


def test_log_stage_start(phase_logger, temp_log_dir):
    """Test logging stage start event."""
    stage_slug = "idea-analysis"
    stage_name = "Idea Analysis"

    phase_logger.log_stage_start(
        stage_slug=stage_slug,
        stage_name=stage_name,
        metadata={"execution_mode": "mvp"},
    )

    # Verify directory structure
    stage_dir = Path(temp_log_dir) / stage_slug
    assert stage_dir.exists()

    # Verify events file
    events_file = stage_dir / "stage_events.jsonl"
    assert events_file.exists()

    with open(events_file) as f:
        lines = f.readlines()
        assert len(lines) == 1

        entry = json.loads(lines[0])
        assert entry["stage_slug"] == stage_slug
        assert entry["stage_name"] == stage_name
        assert entry["event_type"] == "stage_start"
        assert entry["data"]["status"] == "in_progress"
        assert entry["data"]["execution_mode"] == "mvp"


def test_log_stage_complete(phase_logger, temp_log_dir):
    """Test logging stage completion event."""
    stage_slug = "market-context"
    stage_name = "Market Context"
    duration = 125.5

    phase_logger.log_stage_complete(
        stage_slug=stage_slug,
        stage_name=stage_name,
        duration_seconds=duration,
        metrics={
            "total_tokens": 50000,
            "input_tokens": 40000,
            "output_tokens": 10000,
            "cost": 0.125,
        },
    )

    stage_dir = Path(temp_log_dir) / stage_slug
    events_file = stage_dir / "stage_events.jsonl"
    assert events_file.exists()

    with open(events_file) as f:
        entry = json.loads(f.readline())
        assert entry["event_type"] == "stage_complete"
        assert entry["data"]["status"] == "completed"
        assert entry["data"]["duration_seconds"] == duration
        assert entry["data"]["total_tokens"] == 50000

    # Verify metrics file
    metrics_file = stage_dir / "metrics.json"
    assert metrics_file.exists()

    with open(metrics_file) as f:
        metrics = json.load(f)
        assert metrics["stage_slug"] == stage_slug
        assert metrics["stage_name"] == stage_name
        assert metrics["status"] == "completed"
        assert metrics["duration_seconds"] == duration
        assert metrics["total_tokens"] == 50000
        assert metrics["cost"] == 0.125


def test_log_stage_fail(phase_logger, temp_log_dir):
    """Test logging stage failure event."""
    stage_slug = "risk-assessment"
    stage_name = "Risk Assessment"
    error = ValueError("Test error message")
    duration = 45.2

    phase_logger.log_stage_fail(
        stage_slug=stage_slug,
        stage_name=stage_name,
        error=error,
        duration_seconds=duration,
        context="Agent execution failed",
    )

    stage_dir = Path(temp_log_dir) / stage_slug
    events_file = stage_dir / "stage_events.jsonl"
    assert events_file.exists()

    with open(events_file) as f:
        entry = json.loads(f.readline())
        assert entry["event_type"] == "stage_fail"
        assert entry["data"]["status"] == "failed"
        assert entry["data"]["error_type"] == "ValueError"
        assert entry["data"]["error_message"] == "Test error message"
        assert entry["data"]["context"] == "Agent execution failed"

    # Verify metrics file
    metrics_file = stage_dir / "metrics.json"
    assert metrics_file.exists()

    with open(metrics_file) as f:
        metrics = json.load(f)
        assert metrics["status"] == "failed"
        assert metrics["error_type"] == "ValueError"


def test_log_checkpoint(phase_logger, temp_log_dir):
    """Test logging checkpoint creation event."""
    stage_slug = "idea-analysis"
    stage_name = "Idea Analysis"

    checkpoint_data = {
        "status": "completed",
        "outputs": ["concept_expansion.md"],
        "agents": ["concept_expansion"],
        "next_stage": "market-context",
    }

    phase_logger.log_checkpoint(
        stage_slug=stage_slug,
        stage_name=stage_name,
        checkpoint_data=checkpoint_data,
    )

    stage_dir = Path(temp_log_dir) / stage_slug
    events_file = stage_dir / "stage_events.jsonl"
    assert events_file.exists()

    with open(events_file) as f:
        entry = json.loads(f.readline())
        assert entry["event_type"] == "checkpoint"
        assert entry["data"]["status"] == "completed"
        assert entry["data"]["outputs"] == ["concept_expansion.md"]


def test_log_user_feedback(phase_logger, temp_log_dir):
    """Test logging user feedback event."""
    stage_slug = "market-context"
    stage_name = "Market Context"

    phase_logger.log_user_feedback(
        stage_slug=stage_slug,
        stage_name=stage_name,
        action="request_changes",
        feedback={
            "comments": "Need more competitor analysis",
            "requested_changes": ["Add more competitors", "Include pricing data"],
        },
    )

    stage_dir = Path(temp_log_dir) / stage_slug
    feedback_file = stage_dir / "user_feedback.jsonl"
    assert feedback_file.exists()

    with open(feedback_file) as f:
        entry = json.loads(f.readline())
        assert entry["event_type"] == "user_feedback"
        assert entry["data"]["action"] == "request_changes"
        assert entry["data"]["comments"] == "Need more competitor analysis"
        assert len(entry["data"]["requested_changes"]) == 2


def test_log_change_request(phase_logger, temp_log_dir):
    """Test logging change request event."""
    stage_slug = "risk-assessment"
    stage_name = "Risk Assessment"

    phase_logger.log_change_request(
        stage_slug=stage_slug,
        stage_name=stage_name,
        change_type="modify_prompt",
        change_data={"modified_prompt": "Focus on B2B SaaS niches only", "retry_count": 1},
    )

    stage_dir = Path(temp_log_dir) / stage_slug
    feedback_file = stage_dir / "user_feedback.jsonl"
    assert feedback_file.exists()

    with open(feedback_file) as f:
        entry = json.loads(f.readline())
        assert entry["event_type"] == "change_request"
        assert entry["data"]["change_type"] == "modify_prompt"
        assert entry["data"]["retry_count"] == 1


def test_log_agent_execution(phase_logger, temp_log_dir):
    """Test logging agent execution event."""
    stage_slug = "market-context"
    stage_name = "Market Context"

    phase_logger.log_agent_execution(
        stage_slug=stage_slug,
        stage_name=stage_name,
        agent_name="market_intelligence",
        execution_data={
            "status": "completed",
            "duration_seconds": 65.3,
            "input_tokens": 15000,
            "output_tokens": 5000,
            "tools_used": ["http_request", "file_write"],
        },
    )

    stage_dir = Path(temp_log_dir) / stage_slug
    executions_file = stage_dir / "agent_executions.jsonl"
    assert executions_file.exists()

    with open(executions_file) as f:
        entry = json.loads(f.readline())
        assert entry["event_type"] == "agent_execution"
        assert entry["data"]["agent_name"] == "market_intelligence"
        assert entry["data"]["status"] == "completed"
        assert entry["data"]["duration_seconds"] == 65.3


def test_write_session_summary(phase_logger, temp_log_dir):
    """Test writing session summary."""
    summary_data = {
        "execution_mode": "mvp",
        "total_duration_seconds": 850.5,
        "total_tokens": 250000,
        "total_cost": 0.625,
        "stages_completed": 5,
        "stages_failed": 0,
        "status": "completed",
    }

    phase_logger.write_session_summary(summary_data=summary_data)

    summary_file = Path(temp_log_dir) / "session_summary.json"
    assert summary_file.exists()

    with open(summary_file) as f:
        summary = json.load(f)
        assert summary["execution_mode"] == "mvp"
        assert summary["total_duration_seconds"] == 850.5
        assert summary["stages_completed"] == 5


def test_get_stage_metrics(phase_logger, temp_log_dir):
    """Test retrieving stage metrics."""
    stage_slug = "idea-analysis"
    stage_name = "Idea Analysis"

    phase_logger.log_stage_complete(
        stage_slug=stage_slug,
        stage_name=stage_name,
        duration_seconds=45.2,
        metrics={"total_tokens": 10000},
    )

    metrics = phase_logger.get_stage_metrics(stage_slug)
    assert metrics is not None
    assert metrics["stage_slug"] == stage_slug
    assert metrics["duration_seconds"] == 45.2
    assert metrics["total_tokens"] == 10000


def test_get_stage_metrics_not_found(phase_logger):
    """Test retrieving metrics for non-existent stage."""
    metrics = phase_logger.get_stage_metrics("nonexistent-stage")
    assert metrics is None


def test_get_session_summary(phase_logger, temp_log_dir):
    """Test retrieving session summary."""
    summary_data = {"total_duration_seconds": 500.0}
    phase_logger.write_session_summary(summary_data)

    summary = phase_logger.get_session_summary()
    assert summary is not None
    assert summary["total_duration_seconds"] == 500.0


def test_get_session_summary_not_found(phase_logger):
    """Test retrieving summary for non-existent session."""
    summary = phase_logger.get_session_summary()
    assert summary is None


def test_multiple_events_same_stage(phase_logger, temp_log_dir):
    """Test logging multiple events to the same stage."""
    stage_slug = "market-context"
    stage_name = "Market Context"

    phase_logger.log_stage_start(stage_slug, stage_name)
    phase_logger.log_agent_execution(
        stage_slug, stage_name, "market_intelligence", {"status": "completed"}
    )
    phase_logger.log_agent_execution(
        stage_slug, stage_name, "competitor_analysis", {"status": "completed"}
    )
    phase_logger.log_stage_complete(stage_slug, stage_name, 120.5)

    stage_dir = Path(temp_log_dir) / stage_slug
    events_file = stage_dir / "stage_events.jsonl"

    with open(events_file) as f:
        lines = f.readlines()
        assert len(lines) == 2  # stage_start and stage_complete

    executions_file = stage_dir / "agent_executions.jsonl"
    with open(executions_file) as f:
        lines = f.readlines()
        assert len(lines) == 2  # Two agent executions


def test_stage_log_entry_to_dict():
    """Test StageLogEntry (PhaseLogEntry alias) serialization."""
    entry = PhaseLogEntry(
        timestamp="2024-01-15T10:00:00",
        stage_slug="idea-analysis",
        stage_name="Idea Analysis",
        event_type="test_event",
        data={"key": "value"},
    )

    entry_dict = entry.to_dict()
    assert entry_dict["timestamp"] == "2024-01-15T10:00:00"
    assert entry_dict["stage_slug"] == "idea-analysis"
    assert entry_dict["event_type"] == "test_event"
    assert entry_dict["data"]["key"] == "value"


def test_jsonl_format_multiple_entries(phase_logger, temp_log_dir):
    """Test that JSONL format is maintained with multiple entries."""
    stage_slug = "idea-analysis"
    stage_name = "Idea Analysis"

    for i in range(3):
        phase_logger.log_user_feedback(
            stage_slug, stage_name, action="approve", feedback={"iteration": i}
        )

    stage_dir = Path(temp_log_dir) / stage_slug
    feedback_file = stage_dir / "user_feedback.jsonl"

    with open(feedback_file) as f:
        lines = f.readlines()
        assert len(lines) == 3

        for i, line in enumerate(lines):
            entry = json.loads(line)
            assert entry["data"]["iteration"] == i

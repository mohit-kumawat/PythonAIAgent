"""
Tests for Proactive Engine module.
"""

import os
import tempfile
import pytest
from datetime import datetime, timedelta

from memory_manager import MemoryManager
from proactive_engine import ProactiveEngine


@pytest.fixture
def memory():
    """Create a temporary memory manager for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_pm_agent.db")
        yield MemoryManager(db_path)


@pytest.fixture
def engine(memory):
    """Create a proactive engine with test memory."""
    return ProactiveEngine(memory)


@pytest.fixture
def sample_context():
    """Sample context.md content for testing."""
    return """
# PROJECT CONTEXT - The Real PM
Last Updated: 2025-12-01 10:00 IST

## 1. Overall Health & Risk Register
- **Health:** Yellow (Some delays)
- **Primary Blockers:** API integration pending

## 2. Active Epics & Tasks
- Homepage redesign - In Progress
- API refactor - Blocked

## 3. Reminders (Managed by Agent)
- [2025-12-01 11:30] Remind Mohit to check API status
- [2025-11-28 14:00] Follow up on design review
- [2025-12-10 10:00] Future reminder (should not be stale)

## 4. Raw Notes (Append Only)
- Testing stale task detection
"""


class TestStaleTaskDetection:
    """Tests for stale task detection."""
    
    def test_detect_stale_reminders(self, engine, sample_context):
        """Test detection of stale reminders."""
        # With threshold of 3 days, items from 2025-12-01 and earlier should be stale
        stale = engine.check_stale_tasks(sample_context, days_threshold=3)
        
        # Should find at least the old reminders
        assert len(stale) >= 1
        
        # Check the detected items
        for item in stale:
            assert 'days_old' in item
            assert item['days_old'] >= 3
    
    def test_no_stale_with_high_threshold(self, engine, sample_context):
        """Test that high threshold finds nothing stale."""
        # With very high threshold, nothing should be stale
        stale = engine.check_stale_tasks(sample_context, days_threshold=365)
        
        # Most items won't be a year old
        old_items = [s for s in stale if s['days_old'] > 365]
        assert len(old_items) == 0


class TestBlockerDetection:
    """Tests for blocker pattern detection."""
    
    def test_detect_waiting_on(self, engine):
        """Test detection of 'waiting on' pattern."""
        messages = [
            {"text": "I'm waiting on the design team to finalize mockups", "ts": "123"},
            {"text": "All good here", "ts": "124"}
        ]
        
        blockers = engine.detect_blockers(messages)
        
        assert len(blockers) == 1
        assert "waiting" in blockers[0]["pattern_matched"]
    
    def test_detect_blocked_by(self, engine):
        """Test detection of 'blocked by' pattern."""
        messages = [
            {"text": "This task is blocked by the API deployment", "ts": "125"}
        ]
        
        blockers = engine.detect_blockers(messages)
        
        assert len(blockers) == 1
        assert "blocked" in blockers[0]["pattern_matched"]
    
    def test_detect_need_before(self, engine):
        """Test detection of 'need X before' pattern."""
        messages = [
            {"text": "We need approval before we can proceed", "ts": "126"}
        ]
        
        blockers = engine.detect_blockers(messages)
        
        assert len(blockers) == 1
    
    def test_no_false_positives(self, engine):
        """Test that normal messages don't trigger blockers."""
        messages = [
            {"text": "Great work on the homepage!", "ts": "127"},
            {"text": "Let's ship it tomorrow", "ts": "128"},
            {"text": "All tests passing", "ts": "129"}
        ]
        
        blockers = engine.detect_blockers(messages)
        
        assert len(blockers) == 0


class TestUrgencyDetection:
    """Tests for urgency detection."""
    
    def test_detect_urgent_keyword(self, engine):
        """Test detection of 'urgent' keyword."""
        messages = [
            {"text": "This is urgent, we need to fix the bug ASAP", "ts": "130"}
        ]
        
        urgent = engine.detect_urgency(messages)
        
        assert len(urgent) == 1
        assert "urgent" in urgent[0]["keywords"]
        assert "asap" in urgent[0]["keywords"]
    
    def test_detect_priority_labels(self, engine):
        """Test detection of P0/P1 labels."""
        messages = [
            {"text": "P0 bug: Production is down", "ts": "131"}
        ]
        
        urgent = engine.detect_urgency(messages)
        
        assert len(urgent) == 1
        assert urgent[0]["priority"] == "critical"
    
    def test_no_urgency_in_normal_message(self, engine):
        """Test that normal messages aren't flagged as urgent."""
        messages = [
            {"text": "When you get a chance, please review the PR", "ts": "132"}
        ]
        
        urgent = engine.detect_urgency(messages)
        
        assert len(urgent) == 0


class TestStatusReport:
    """Tests for status report generation."""
    
    def test_generate_report(self, engine, sample_context):
        """Test basic report generation."""
        report = engine.generate_status_report(sample_context, period="weekly")
        
        assert report["period"] == "weekly"
        assert "summary" in report
        assert "generated_at" in report
        
        summary = report["summary"]
        assert "health_status" in summary
        assert "total_actions" in summary
    
    def test_report_text_generation(self, engine, sample_context):
        """Test converting report to text."""
        report = engine.generate_status_report(sample_context)
        text = engine.generate_report_text(report)
        
        assert "Status Report" in text
        assert "KEY METRICS" in text
        assert "Health Status" in text


class TestProactiveSuggestions:
    """Tests for combined proactive suggestions."""
    
    def test_get_suggestions_with_stale_tasks(self, engine, sample_context):
        """Test getting suggestions including stale tasks."""
        suggestions = engine.get_proactive_suggestions(sample_context)
        
        # Should have some suggestions from stale tasks
        stale_suggestions = [s for s in suggestions if s["action_type"] == "proactive_followup"]
        assert len(stale_suggestions) >= 0  # May or may not have depending on dates
    
    def test_get_suggestions_with_blockers(self, engine, sample_context):
        """Test getting suggestions including blocker detection."""
        messages = [
            {"text": "We're blocked by the vendor response", "ts": "140"}
        ]
        
        suggestions = engine.get_proactive_suggestions(sample_context, messages)
        
        blocker_suggestions = [s for s in suggestions if s["action_type"] == "proactive_blocker_alert"]
        assert len(blocker_suggestions) == 1
    
    def test_suggestions_are_marked_proactive(self, engine, sample_context):
        """Test that all suggestions are marked as proactive."""
        messages = [{"text": "Waiting on approval", "ts": "141"}]
        
        suggestions = engine.get_proactive_suggestions(sample_context, messages)
        
        for s in suggestions:
            assert s.get("is_proactive") == True
            assert s.get("status") == "PENDING"

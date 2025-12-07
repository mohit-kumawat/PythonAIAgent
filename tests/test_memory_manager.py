"""
Tests for Memory Manager module.
"""

import os
import tempfile
import pytest
from memory_manager import MemoryManager


@pytest.fixture
def memory():
    """Create a temporary memory manager for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_pm_agent.db")
        yield MemoryManager(db_path)


class TestDecisions:
    """Tests for decision logging functionality."""
    
    def test_log_decision_approved(self, memory):
        """Test logging an approved decision."""
        decision_id = memory.log_decision(
            action_type="schedule_reminder",
            approved=True,
            reasoning="User requested a reminder for tomorrow",
            action_data={"time_iso": "2025-12-08T10:00:00"}
        )
        
        assert decision_id is not None
        assert decision_id > 0
    
    def test_log_decision_rejected(self, memory):
        """Test logging a rejected decision."""
        decision_id = memory.log_decision(
            action_type="send_email_summary",
            approved=False,
            reasoning="User wanted weekly, not daily summary"
        )
        
        assert decision_id is not None
    
    def test_get_decision_history(self, memory):
        """Test retrieving decision history."""
        # Log some decisions
        memory.log_decision("schedule_reminder", True, "Reminder 1")
        memory.log_decision("send_email_summary", False, "Email rejected")
        memory.log_decision("schedule_reminder", True, "Reminder 2")
        
        # Get all decisions
        history = memory.get_decision_history(limit=10)
        assert len(history) == 3
        
        # Filter by action type
        reminder_history = memory.get_decision_history(action_type="schedule_reminder")
        assert len(reminder_history) == 2
    
    def test_approval_rate(self, memory):
        """Test approval rate calculation."""
        # Log mixed decisions
        memory.log_decision("test_action", True, "Approved 1")
        memory.log_decision("test_action", True, "Approved 2")
        memory.log_decision("test_action", False, "Rejected 1")
        memory.log_decision("test_action", True, "Approved 3")
        
        rate = memory.get_approval_rate()
        
        assert rate["total"] == 4
        assert rate["approved"] == 3
        assert rate["rejected"] == 1
        assert rate["rate"] == 75.0


class TestThreadContext:
    """Tests for thread context storage."""
    
    def test_store_and_retrieve_thread_context(self, memory):
        """Test storing and retrieving thread context."""
        memory.store_thread_context(
            thread_ts="1234567890.123456",
            channel_id="C123ABC",
            summary="Discussion about feature release timeline",
            entities=["@mohit", "@pravin", "homepage", "release"]
        )
        
        context = memory.get_thread_context("1234567890.123456", "C123ABC")
        
        assert context is not None
        assert context["summary"] == "Discussion about feature release timeline"
        assert "@mohit" in context["entities"]
    
    def test_update_thread_context(self, memory):
        """Test updating existing thread context."""
        memory.store_thread_context(
            thread_ts="1234567890.123456",
            channel_id="C123ABC",
            summary="Initial summary"
        )
        
        memory.store_thread_context(
            thread_ts="1234567890.123456",
            channel_id="C123ABC",
            summary="Updated summary with more details"
        )
        
        context = memory.get_thread_context("1234567890.123456", "C123ABC")
        assert context["summary"] == "Updated summary with more details"
    
    def test_nonexistent_thread(self, memory):
        """Test retrieving non-existent thread returns None."""
        context = memory.get_thread_context("nonexistent", "C123")
        assert context is None


class TestKnowledge:
    """Tests for knowledge/insights storage."""
    
    def test_store_insight(self, memory):
        """Test storing an insight."""
        memory.store_insight(
            category="user_preference",
            content="Mohit prefers reminders at 11:30 AM IST",
            source="slack:C123:ts456"
        )
        
        results = memory.search_memory("11:30")
        assert len(results) == 1
        assert "Mohit" in results[0]["content"]
    
    def test_search_memory(self, memory):
        """Test searching through knowledge."""
        memory.store_insight("project_fact", "Homepage redesign due date is Jan 15")
        memory.store_insight("project_fact", "API refactor starts next week")
        memory.store_insight("team_pattern", "Standups happen at 10 AM")
        
        # Search for homepage
        results = memory.search_memory("homepage")
        assert len(results) == 1
        
        # Search with category filter
        results = memory.search_memory("10", category="team_pattern")
        assert len(results) == 1
    
    def test_get_knowledge_by_category(self, memory):
        """Test getting all knowledge in a category."""
        memory.store_insight("blocker_pattern", "External API timeouts")
        memory.store_insight("blocker_pattern", "Waiting on design approval")
        memory.store_insight("project_fact", "Other fact")
        
        blockers = memory.get_knowledge_by_category("blocker_pattern")
        assert len(blockers) == 2


class TestActionHistory:
    """Tests for action execution history."""
    
    def test_log_action_execution(self, memory):
        """Test logging executed action."""
        memory.log_action_execution(
            action_id="action-123",
            action_type="schedule_reminder",
            status="SUCCESS",
            reasoning="User requested reminder",
            action_data={"channel": "C123", "time": "2025-12-08T10:00:00"},
            result="Scheduled message ID: 12345"
        )
        
        history = memory.get_action_history(limit=1)
        assert len(history) == 1
        assert history[0]["action_id"] == "action-123"
        assert history[0]["status"] == "SUCCESS"
    
    def test_filter_by_status(self, memory):
        """Test filtering action history by status."""
        memory.log_action_execution("a1", "reminder", "SUCCESS", "r1")
        memory.log_action_execution("a2", "email", "FAILED", "r2")
        memory.log_action_execution("a3", "reminder", "SUCCESS", "r3")
        
        success_only = memory.get_action_history(status="SUCCESS")
        assert len(success_only) == 2


class TestStats:
    """Tests for statistics."""
    
    def test_get_stats(self, memory):
        """Test getting overall stats."""
        # Add some data
        memory.log_decision("test", True, "r1")
        memory.log_decision("test", False, "r2")
        memory.store_thread_context("ts1", "c1", "summary")
        memory.store_insight("category", "content")
        memory.log_action_execution("a1", "type", "SUCCESS", "r")
        
        stats = memory.get_stats()
        
        assert stats["decisions"] == 2
        assert stats["threads"] == 1
        assert stats["knowledge_entries"] == 1
        assert stats["total_actions"] == 1
        assert stats["successful_actions"] == 1
        assert stats["approval_rate"] == 50.0

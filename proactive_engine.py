"""
Proactive Engine - Transform the PM Agent from reactive to proactive.
Detects stale tasks, blockers, and generates automatic suggestions.
"""

import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import uuid

from memory_manager import MemoryManager, get_memory_manager


class ProactiveEngine:
    """
    Proactive intelligence engine for the PM Agent.
    
    Capabilities:
    - Detect stale tasks (no updates in N days)
    - Detect blocker patterns in messages
    - Generate weekly/daily status reports
    - Suggest follow-up actions proactively
    """
    
    # Patterns that indicate blockers
    BLOCKER_PATTERNS = [
        r'waiting\s+(on|for)\s+',
        r'blocked\s+(by|on)\s+',
        r'need\s+.*\s+before',
        r'can\'t\s+proceed',
        r'dependency\s+on',
        r'stuck\s+(on|at)',
        r'pending\s+(approval|review)',
    ]
    
    # Keywords that suggest urgency
    URGENCY_KEYWORDS = [
        'urgent', 'asap', 'critical', 'blocker', 'deadline', 
        'today', 'immediately', 'priority', 'p0', 'p1'
    ]
    
    def __init__(self, memory: MemoryManager = None):
        self.memory = memory or get_memory_manager()
    
    def check_stale_tasks(
        self, 
        context_md: str, 
        days_threshold: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Detect tasks in context.md that haven't been updated recently.
        
        Args:
            context_md: Current project context content
            days_threshold: Days without update to consider stale
            
        Returns:
            List of stale task alerts with suggested actions
        """
        stale_items = []
        now = datetime.now()
        threshold_date = now - timedelta(days=days_threshold)
        
        # Parse reminders section for old dates
        lines = context_md.split('\n')
        in_reminders = False
        in_epics = False
        
        for line in lines:
            if '## 3. Reminders' in line:
                in_reminders = True
                in_epics = False
                continue
            elif '## 2. Active Epics' in line:
                in_epics = True
                in_reminders = False
                continue
            elif line.startswith('## '):
                in_reminders = False
                in_epics = False
                continue
            
            # Look for date patterns [YYYY-MM-DD]
            date_match = re.search(r'\[(\d{4}-\d{2}-\d{2})', line)
            if date_match:
                try:
                    item_date = datetime.strptime(date_match.group(1), '%Y-%m-%d')
                    
                    # Check if this date is in the past
                    if item_date < threshold_date:
                        days_old = (now - item_date).days
                        
                        stale_items.append({
                            "id": str(uuid.uuid4())[:8],
                            "type": "stale_reminder" if in_reminders else "stale_task",
                            "content": line.strip(),
                            "date": date_match.group(1),
                            "days_old": days_old,
                            "suggested_action": f"Follow up on this item (last activity {days_old} days ago)",
                            "action_type": "schedule_reminder",
                            "priority": "high" if days_old > 7 else "medium"
                        })
                except ValueError:
                    continue
        
        return stale_items

    def _was_recently_suggested(self, content: str, days: int = 1) -> bool:
        """Check if this content was suggesting in the last N days."""
        # Get recent decisions from memory
        recent_decisions = self.memory.get_decision_history(limit=50)
        
        cutoff = datetime.now() - timedelta(days=days)
        
        for decision in recent_decisions:
            created_at = datetime.strptime(decision['created_at'], '%Y-%m-%d %H:%M:%S')
            if created_at < cutoff:
                continue
                
            # Check if data matches
            if decision.get('action_data'):
                try:
                    data = json.loads(decision['action_data'])
                    if data.get('original_content') == content:
                        return True
                except:
                    pass
        return False

    def detect_blockers(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Scan messages for blocker patterns.
        
        Args:
            messages: List of Slack messages to analyze
            
        Returns:
            List of detected blockers with details
        """
        blockers = []
        
        for msg in messages:
            text = msg.get('text', '')
            text_lower = text.lower()
            
            for pattern in self.BLOCKER_PATTERNS:
                match = re.search(pattern, text_lower)
                if match:
                    # Extract context around the blocker phrase
                    start = max(0, match.start() - 20)
                    end = min(len(text), match.end() + 50)
                    context = text[start:end]
                    
                    blockers.append({
                        "id": str(uuid.uuid4())[:8],
                        "type": "blocker",
                        "pattern_matched": pattern,
                        "message_text": text[:200],  # Truncate
                        "context": context,
                        "timestamp": msg.get('ts'),
                        "user": msg.get('user'),
                        "suggested_action": "Address this blocker or follow up",
                        "priority": "high"
                    })
                    break  # One blocker per message
        
        return blockers
    
    def detect_urgency(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect messages with urgency indicators.
        
        Args:
            messages: List of Slack messages
            
        Returns:
            List of urgent items
        """
        urgent_items = []
        
        for msg in messages:
            text = msg.get('text', '')
            text_lower = text.lower()
            
            matched_keywords = [kw for kw in self.URGENCY_KEYWORDS if kw in text_lower]
            
            if matched_keywords:
                urgent_items.append({
                    "id": str(uuid.uuid4())[:8],
                    "type": "urgent",
                    "keywords": matched_keywords,
                    "message_text": text[:200],
                    "timestamp": msg.get('ts'),
                    "user": msg.get('user'),
                    "priority": "critical" if 'p0' in matched_keywords or 'blocker' in matched_keywords else "high"
                })
        
        return urgent_items
    
    def generate_status_report(self, context_text: str, period: str = "weekly", custom_directive: str = "") -> Dict[str, Any]:
        """
        Generates a status report based on the context.
        period: 'weekly' or 'daily'
        custom_directive: Optional specific instructions (e.g., "Morning Standup")
        """
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        prompt = f"""You are The Real PM. specific task: Generate a {period} status report.
        
        Current Context:
        {context_text}
        
        {custom_directive}
        
        Return a JSON object with:
        {{
            "title": "...",
            "summary": "...",
            "key_updates": ["...", "..."],
            "blockers": ["..."],
            "next_steps": ["..."]
        }}
        """
        # Get stats from memory
        stats = self.memory.get_stats()
        recent_actions = self.memory.get_action_history(limit=20)
        
        # Parse context for current state
        health_status = "Unknown"
        blockers_count = 0
        
        for line in context_text.split('\n'):
            if '**Health:**' in line:
                health_status = line.split('**Health:**')[-1].strip()
            if 'Blocker' in line or 'blocker' in line:
                blockers_count += 1
        
        # Count actions by type
        action_counts = {}
        for action in recent_actions:
            atype = action.get('action_type', 'unknown')
            action_counts[atype] = action_counts.get(atype, 0) + 1
        
        # Calculate success rate
        successful = len([a for a in recent_actions if a.get('status') == 'SUCCESS'])
        success_rate = round(successful / len(recent_actions) * 100, 1) if recent_actions else 0
        
        report = {
            "period": period,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "health_status": health_status,
                "blockers_count": blockers_count,
                "total_actions": stats.get('total_actions', 0),
                "successful_actions": stats.get('successful_actions', 0),
                "success_rate": success_rate,
                "approval_rate": stats.get('approval_rate', 0),
                "knowledge_entries": stats.get('knowledge_entries', 0)
            },
            "action_breakdown": action_counts,
            "recent_actions": recent_actions[:10]
        }
        
        return report
    
    def generate_report_text(self, report: Dict[str, Any]) -> str:
        """Convert structured report to readable text."""
        summary = report.get('summary', {})
        
        lines = [
            f"📊 {report.get('period', 'Weekly').title()} Status Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} IST",
            "",
            "═" * 40,
            "",
            "📈 KEY METRICS",
            f"  • Health Status: {summary.get('health_status', 'Unknown')}",
            f"  • Active Blockers: {summary.get('blockers_count', 0)}",
            f"  • Actions Executed: {summary.get('total_actions', 0)}",
            f"  • Success Rate: {summary.get('success_rate', 0)}%",
            f"  • Approval Rate: {summary.get('approval_rate', 0)}%",
            "",
        ]
        
        # Action breakdown
        breakdown = report.get('action_breakdown', {})
        if breakdown:
            lines.append("📋 ACTIONS BY TYPE")
            for action_type, count in breakdown.items():
                lines.append(f"  • {action_type}: {count}")
            lines.append("")
        
        lines.extend([
            "═" * 40,
            "Generated by The Real PM Agent"
        ])
        
        return '\n'.join(lines)


        # Check for stale tasks
        stale_tasks = self.check_stale_tasks(context_md)
        for task in stale_tasks:
            suggestions.append({
                "id": f"proactive-{task['id']}",
                "action_type": "proactive_followup",
                "reasoning": f"🔔 Stale item detected: {task['content'][:100]}",
                "status": "PENDING",
                "created_at": datetime.now().isoformat(),
                "data": {
                    "source": "stale_task_detection",
                    "days_old": task["days_old"],
                    "original_content": task["content"],
                    "suggested_action": task["suggested_action"]
                },
                "is_proactive": True,
                "priority": task.get("priority", "medium")
            })
        
        # Check for blockers in messages
        if messages:
            blockers = self.detect_blockers(messages)
            for blocker in blockers:
                suggestions.append({
                    "id": f"proactive-{blocker['id']}",
                    "action_type": "proactive_blocker_alert",
                    "reasoning": f"🚨 Blocker detected: {blocker['context']}",
                    "status": "PENDING",
                    "created_at": datetime.now().isoformat(),
                    "data": {
                        "source": "blocker_detection",
                        "message_text": blocker["message_text"],
                        "pattern": blocker["pattern_matched"]
                    },
                    "is_proactive": True,
                    "priority": "high"
                })
        
        # Store insights for learning
        for suggestion in suggestions:
            self.memory.store_insight(
                category="proactive_suggestion",
                content=suggestion["reasoning"],
                source=f"proactive_engine:{suggestion['action_type']}",
                metadata={"priority": suggestion.get("priority")}
            )
        
        return suggestions
    
    def should_send_weekly_report(self) -> bool:
        """
        Check if it's time to send weekly report.
        
        Returns True if:
        - It's Friday afternoon (after 4 PM)
        - No report was sent today
        """
        now = datetime.now()
        
        # Check if it's Friday
        if now.weekday() != 4:  # Friday = 4
            return False
        
        # Check if it's after 4 PM
        if now.hour < 16:
            return False
        
        # Check if report was already sent today
        recent_actions = self.memory.get_action_history(
            limit=10, 
            status="SUCCESS"
        )
        
        today = now.strftime('%Y-%m-%d')
        for action in recent_actions:
            if action.get('action_type') == 'weekly_report':
                if today in action.get('created_at', ''):
                    return False
        
        return True


def run_proactive_check(context_md: str, messages: List[Dict] = None) -> List[Dict]:
    """
    Convenience function to run all proactive checks.
    
    Args:
        context_md: Project context content
        messages: Optional recent Slack messages
        
    Returns:
        List of proactive suggestions
    """
    engine = ProactiveEngine()
    return engine.get_proactive_suggestions(context_md, messages)

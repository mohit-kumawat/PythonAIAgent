"""
Proactive Engine - Transform the PM Agent from reactive to proactive.
Detects stale tasks, blockers, and generates automatic suggestions.
"""

import re
import os
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
        Generates a status report by asking the LLM to summarize the context.
        """
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # We need the client to generate content
        from client_manager import ClientManager
        from google.genai import types
        
        cm = ClientManager()
        client = cm.get_client()
        
        prompt = f"""You are The Real PM. 
        Task: Generate a high-quality {period} status report for the team.
        
        Current Time: {current_time}
        
        PROJECT CONTEXT:
        {context_text}
        
        DIRECTIVE:
        {custom_directive}
        
        USER DIRECTORY (Use these names):
        - {os.environ.get("SLACK_USER_ID", "U07FDMFFM5F")}: Mohit
        - U0A1J73B8JH: Pravin
        - U07NJKB5HA7: Umang
        - U08T2AJQ1NF: Badal
        
        INSTRUCTIONS:
        1. Digest the context above (Tasks, Epics, Blockers, Health).
        2. Write a professional, concise status update message.
        3. Do NOT just list system stats. Focus on:
           - What is achieved?
           - What is blocked?
           - *Team Focus: Briefly list what each person (Mohit, Pravin, Umang, Badal) has on their plate today.*
           - Call to Action / Next Steps.
        4. If it is high-level, keep it high-level. If detailed, be detailed.
        5. Tone: Professional, clear, confident project manager.
        6. FORMATTING RULES (CRITICAL):
           - Use single asterisks for *bold text* (e.g., *Heading*). Do NOT use double asterisks (**).
           - Use bullet points (•) for lists.
           - Keep it clean and easy to read on mobile.
           - REPLACE ALL User IDs with Names or Mentions:
             - If you know the name (from directory above), use the Name (e.g., "Pravin").
             - If you need to tag them, use <@USER_ID>.
             - NEVER output a raw ID like "U12345" alone.
        """
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        return {
            "period": period,
            "report_text": response.text,
            "generated_at": current_time
        }
    
    def generate_report_text(self, report: Dict[str, Any]) -> str:
        """Return the pre-generated text from the LLM."""
        return report.get('report_text', "Report generation failed.")


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

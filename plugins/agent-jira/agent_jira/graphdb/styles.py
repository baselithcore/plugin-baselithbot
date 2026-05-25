"""
Graph styling and priority configuration.
"""

# Centralized styling configuration for Frontend consistency
NODE_STYLES = {
    "Document": {"color": "#1e40af", "label": "Document"},
    "KnowledgeBase": {"color": "#4f46e5", "label": "Knowledge Base"},
    "Analysis": {"color": "#a21caf", "label": "Analysis"},
    "Risk": {"color": "#dc2626", "label": "Risk"},
    "Milestone": {"color": "#16a34a", "label": "Milestone"},
    "Technology": {"color": "#ea580c", "label": "Technology"},
    "Stakeholder": {"color": "#7c3aed", "label": "Stakeholder"},
    "Topic": {"color": "#0891b2", "label": "Topic"},
    "Story": {"color": "#f59e0b", "label": "User Story"},
    "TestCase": {"color": "#ec4899", "label": "Test Case"},
    "Epic": {"color": "#8b5cf6", "label": "Epic"},
    "Requirement": {"color": "#10b981", "label": "Requirement"},
    "JiraIssue": {"color": "#3b82f6", "label": "Jira Issue"},
    "Unknown": {"color": "#6b7280", "label": "Unknown"},
}

# Priority order for labels (high priority first)
# Lower integer value = Higher priority
LABEL_PRIORITY = {
    "Analysis": 1,
    "KnowledgeBase": 1,
    "Risk": 2,
    "Milestone": 3,
    "Story": 4,
    "TestCase": 4,
    "Epic": 4,
    "Requirement": 4,
    "Technology": 5,
    "Stakeholder": 5,
    "Topic": 6,
    "JiraIssue": 8,
    "Document": 9,
    "Unknown": 10,
}

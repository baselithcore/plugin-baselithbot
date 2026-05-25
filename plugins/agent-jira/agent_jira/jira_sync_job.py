"""
Jira Sync Job

Synchronization module to update GraphDB nodes with the latest status from Jira.
This is an on-demand/scheduled job, not real-time via webhooks.

Usage:
    python -m app.jira_sync_job
"""

import argparse
import logging

from agent_jira.graphdb import graph_db
from agent_jira.integrations.jira import JiraClient
from agent_jira.config import JIRA_ENABLED

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jira_sync")


def sync_jira_status():
    if not JIRA_ENABLED:
        logger.warning("Jira integration is disabled.")
        return

    # Init GraphAgent
    from agent_jira.agents.graph_agent import GraphAgent

    agent = GraphAgent(graph_db)
    if not graph_db.is_enabled():
        logger.warning("GraphDB is disabled.")
        return

    client = JiraClient()
    if not client.is_ready():
        logger.error("Jira Client failed to initialize.")
        return

    # 1. Get tracked issues via Agent
    issue_map = agent.get_tracked_issues()
    if not issue_map:
        logger.info("No tracked issues in GraphDB.")
        return

    logger.info(f"Found {len(issue_map)} tracked issues in GraphDB.")

    keys = list(issue_map.keys())
    batch_size = 20
    updated_count = 0

    for i in range(0, len(keys), batch_size):
        batch_keys = keys[i : i + batch_size]
        # Clean keys (ensure no weird chars)
        batch_keys = [
            k for k in batch_keys if k and "-" in k
        ]  # Simple check for Jira Key format (PROJ-123)

        if not batch_keys:
            continue

        jql = f"key in ({','.join(batch_keys)})"
        logger.info(f"Syncing batch: {batch_keys}")

        try:
            found_issues = client.search_issues(jql, fields="status")

            for issue in found_issues:
                key = issue.get("key")
                fields = issue.get("fields", {})
                status_obj = fields.get("status", {})
                current_status_name = (
                    status_obj.get("name")
                    if isinstance(status_obj, dict)
                    else str(status_obj)
                )

                if current_status_name and key:
                    old_status = issue_map.get(key)
                    # Normalize comparison
                    if old_status != current_status_name:
                        agent.update_issue_status(key, current_status_name)
                        updated_count += 1

        except Exception as e:
            logger.error(f"Error syncing batch {batch_keys}: {e}")

    logger.info(f"Sync complete. Updated {updated_count} issues.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.parse_args()  # No args for now

    sync_jira_status()

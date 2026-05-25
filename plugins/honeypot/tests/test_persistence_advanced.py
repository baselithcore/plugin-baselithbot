"""Tests for Advanced Persistence Features.

Covers retention policies, time-series analytics, and advanced aggregations.
Uses mocking to avoid PostgreSQL dependency in unit tests.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from plugins.honeypot.persistence.retention import (
    apply_retention_policy,
    get_retention_status,
)
from plugins.honeypot.persistence.timeseries import (
    get_timeseries,
    get_trends,
    _VALID_INTERVALS,
    _VALID_GROUPS,
)
from plugins.honeypot.persistence.aggregations import (
    get_top_attackers,
    get_attack_heatmap,
    get_cve_trends,
)


# =========================================================================
# Retention Policy Tests
# =========================================================================


class TestRetentionPolicy:
    """Tests for data retention service."""

    @pytest.mark.asyncio
    @patch("plugins.honeypot.persistence.retention.get_connection")
    async def test_apply_retention_deletes_old_data(self, mock_conn):
        """Verify retention deletes events and sessions older than cutoff."""
        mock_cursor = AsyncMock()
        mock_cursor.rowcount = 5
        mock_cursor.fetchone = AsyncMock(return_value=(10,))  # 10 rows left

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_conn_instance = AsyncMock()
        mock_conn_instance.cursor = MagicMock(return_value=mock_ctx)

        mock_conn_ctx = AsyncMock()
        mock_conn_ctx.__aenter__ = AsyncMock(return_value=mock_conn_instance)
        mock_conn_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_conn.return_value = mock_conn_ctx

        result = await apply_retention_policy(max_age_days=30, max_rows=1_000_000)

        assert "events_deleted_by_age" in result
        assert "sessions_deleted_by_age" in result
        assert "retention_applied_at" in result

    @pytest.mark.asyncio
    @patch("plugins.honeypot.persistence.retention.get_connection")
    async def test_apply_retention_handles_errors(self, mock_conn):
        """Verify retention handles connection errors gracefully."""
        mock_conn.side_effect = Exception("DB connection failed")

        result = await apply_retention_policy()

        assert "error" in result
        assert result["events_deleted_by_age"] == 0

    @pytest.mark.asyncio
    @patch("plugins.honeypot.persistence.retention.get_connection")
    async def test_retention_status_returns_metrics(self, mock_conn):
        """Verify retention status returns expected keys."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(
            side_effect=[
                (100,),  # events count
                (25,),  # sessions count
                (
                    datetime(2025, 1, 1, tzinfo=timezone.utc),
                    datetime(2025, 6, 1, tzinfo=timezone.utc),
                ),  # event age range
                (datetime(2025, 2, 1, tzinfo=timezone.utc),),  # oldest session
                (52428800,),  # estimated size (50 MB)
            ]
        )

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_conn_instance = AsyncMock()
        mock_conn_instance.cursor = MagicMock(return_value=mock_ctx)

        mock_conn_ctx = AsyncMock()
        mock_conn_ctx.__aenter__ = AsyncMock(return_value=mock_conn_instance)
        mock_conn_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_conn.return_value = mock_conn_ctx

        status = await get_retention_status()

        assert status["events_count"] == 100
        assert status["sessions_count"] == 25


# =========================================================================
# Time-Series Analytics Tests
# =========================================================================


class TestTimeSeries:
    """Tests for time-series analytics."""

    def test_valid_intervals(self):
        """Verify valid interval constants are defined."""
        assert "hour" in _VALID_INTERVALS
        assert "day" in _VALID_INTERVALS
        assert "week" in _VALID_INTERVALS
        assert "month" in _VALID_INTERVALS

    def test_valid_groups(self):
        """Verify valid group-by dimensions are defined."""
        assert "protocol" in _VALID_GROUPS
        assert "severity" in _VALID_GROUPS
        assert "category" in _VALID_GROUPS
        assert "country" in _VALID_GROUPS

    @pytest.mark.asyncio
    async def test_invalid_interval_raises(self):
        """Verify invalid interval raises ValueError."""
        with pytest.raises(ValueError, match="Invalid interval"):
            await get_timeseries(interval="minute")

    @pytest.mark.asyncio
    async def test_invalid_group_by_raises(self):
        """Verify invalid group_by raises ValueError."""
        with pytest.raises(ValueError, match="Invalid group_by"):
            await get_timeseries(group_by="nonexistent")

    @pytest.mark.asyncio
    @patch("plugins.honeypot.persistence.timeseries.get_connection")
    async def test_timeseries_returns_list(self, mock_conn):
        """Verify timeseries query returns a list of dicts."""
        now = datetime.now(timezone.utc)
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(
            return_value=[
                (now, 10),
                (now - timedelta(hours=1), 5),
            ]
        )

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_conn_instance = AsyncMock()
        mock_conn_instance.cursor = MagicMock(return_value=mock_ctx)

        mock_conn_ctx = AsyncMock()
        mock_conn_ctx.__aenter__ = AsyncMock(return_value=mock_conn_instance)
        mock_conn_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_conn.return_value = mock_conn_ctx

        results = await get_timeseries(interval="hour", days=1)

        assert isinstance(results, list)
        assert len(results) == 2
        assert "bucket" in results[0]
        assert "count" in results[0]

    @pytest.mark.asyncio
    @patch("plugins.honeypot.persistence.timeseries.get_connection")
    async def test_trends_returns_velocity(self, mock_conn):
        """Verify trends returns attack velocity metrics."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(
            side_effect=[
                (100,),  # current count
                (50,),  # previous count
            ]
        )
        mock_cursor.fetchall = AsyncMock(return_value=[])

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_conn_instance = AsyncMock()
        mock_conn_instance.cursor = MagicMock(return_value=mock_ctx)

        mock_conn_ctx = AsyncMock()
        mock_conn_ctx.__aenter__ = AsyncMock(return_value=mock_conn_instance)
        mock_conn_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_conn.return_value = mock_conn_ctx

        trends = await get_trends(days=7)

        assert "attack_velocity" in trends
        assert "current_events_per_hour" in trends["attack_velocity"]


# =========================================================================
# Aggregation Tests
# =========================================================================


class TestAggregations:
    """Tests for advanced aggregation queries."""

    @pytest.mark.asyncio
    @patch("plugins.honeypot.persistence.aggregations.get_connection")
    async def test_top_attackers_returns_list(self, mock_conn):
        """Verify top_attackers returns structured attacker list."""
        now = datetime.now(timezone.utc)
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(
            return_value=[
                ("192.168.1.100", 50, now, now, ["ssh", "http"], "critical", None),
            ]
        )

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_conn_instance = AsyncMock()
        mock_conn_instance.cursor = MagicMock(return_value=mock_ctx)

        mock_conn_ctx = AsyncMock()
        mock_conn_ctx.__aenter__ = AsyncMock(return_value=mock_conn_instance)
        mock_conn_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_conn.return_value = mock_conn_ctx

        attackers = await get_top_attackers(days=7, limit=10)

        assert isinstance(attackers, list)
        assert len(attackers) == 1
        assert attackers[0]["ip"] == "192.168.1.100"
        assert attackers[0]["event_count"] == 50

    @pytest.mark.asyncio
    @patch("plugins.honeypot.persistence.aggregations.get_connection")
    async def test_heatmap_returns_list(self, mock_conn):
        """Verify heatmap returns category × hour grid."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(
            return_value=[
                ("sql_injection", 14, 25),
                ("command_injection", 3, 10),
            ]
        )

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_conn_instance = AsyncMock()
        mock_conn_instance.cursor = MagicMock(return_value=mock_ctx)

        mock_conn_ctx = AsyncMock()
        mock_conn_ctx.__aenter__ = AsyncMock(return_value=mock_conn_instance)
        mock_conn_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_conn.return_value = mock_conn_ctx

        heatmap = await get_attack_heatmap(days=7)

        assert isinstance(heatmap, list)
        assert heatmap[0]["category"] == "sql_injection"
        assert heatmap[0]["hour"] == 14

    @pytest.mark.asyncio
    @patch("plugins.honeypot.persistence.aggregations.get_connection")
    async def test_cve_trends_returns_dict(self, mock_conn):
        """Verify CVE trends returns structured response."""
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=(15,))
        mock_cursor.fetchall = AsyncMock(return_value=[])

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_conn_instance = AsyncMock()
        mock_conn_instance.cursor = MagicMock(return_value=mock_ctx)

        mock_conn_ctx = AsyncMock()
        mock_conn_ctx.__aenter__ = AsyncMock(return_value=mock_conn_instance)
        mock_conn_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_conn.return_value = mock_conn_ctx

        trends = await get_cve_trends(days=30)

        assert "top_cves" in trends
        assert "daily_counts" in trends
        assert trends["total_correlations"] == 15

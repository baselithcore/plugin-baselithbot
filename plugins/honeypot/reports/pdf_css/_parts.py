"""Assembles the full REPORT_CSS from parts."""

from ._part1 import _PART1
from ._part2 import _PART2
from ._part3 import _PART3

REPORT_CSS = _PART1 + _PART2 + _PART3

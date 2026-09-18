"""Logging configuration.

All logging goes to stderr and to a file at logs/<script>_<run_id>.log
(Rule R5.7). Uses the standard logging module — never raw print().
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def setup_logging(
    script_name: str,
    run_id: str | None = None,
    level: int = logging.INFO,
    log_dir: str | Path = "logs",
) -> logging.Logger:
    """Configure logging for a script.

    Args:
        script_name: Name of the calling script (e.g. 'run_verifiers').
        run_id: Optional run identifier for the log filename.
        level: Logging level.
        log_dir: Directory for log files.

    Returns:
        The root logger, configured.
    """
    root = logging.getLogger()
    root.setLevel(level)

    # Clear existing handlers to avoid duplicates.
    root.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Stderr handler.
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    root.addHandler(stderr_handler)

    # File handler.
    if run_id:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(
            log_path / f"{script_name}_{run_id}.log",
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    return root

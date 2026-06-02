# tests/test_cli.py
import argparse

from cli import _cmd_generate


def test_generate_requires_out_when_not_dry_run(capsys):
    """--out is required when not in dry-run mode; omitting it prints an error and returns 1."""
    result = _cmd_generate(argparse.Namespace(dry_run=False, out=None))
    assert result == 1
    assert "--out is required" in capsys.readouterr().err

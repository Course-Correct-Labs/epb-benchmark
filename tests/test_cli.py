"""Tests for CLI commands."""

import pytest
from click.testing import CliRunner

from epb.cli.main import cli


def test_cli_help():
    """Test that CLI help works."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "EPB: Epistemic Pathology Benchmark" in result.output


def test_cli_version():
    """Test that CLI version works."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "epb_v1" in result.output


def test_init_config_help():
    """Test init-config help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["init-config", "--help"])
    assert result.exit_code == 0
    assert "Initialize" in result.output


def test_run_help():
    """Test run help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--help"])
    assert result.exit_code == 0
    assert "Run the EPB benchmark" in result.output


def test_score_help():
    """Test score help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["score", "--help"])
    assert result.exit_code == 0
    assert "Score EPB benchmark results" in result.output


def test_submit_help():
    """Test submit help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["submit", "--help"])
    assert result.exit_code == 0
    assert "Submit results" in result.output


def test_init_config_creates_file():
    """Test that init-config creates a file."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["init-config", "--output", "test_config.yaml"])
        assert result.exit_code == 0
        assert "Created config file" in result.output

        # Check file was created
        import os
        assert os.path.exists("test_config.yaml")

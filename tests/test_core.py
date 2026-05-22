import pytest
import os
from src.core.harness import ProjectHarness

def test_harness_initialization(tmp_path):
    """Verify that the SDD-Harness can initialize correctly."""
    # Mocking project root
    os_chdir = os.getcwd()
    try:
        os.chdir(tmp_path)
        harness = ProjectHarness("Test-Project")
        health = harness.check_health()
        assert health["status"] == "OK"
        assert os.path.exists(".harness_state.json")
    finally:
        os.chdir(os_chdir)

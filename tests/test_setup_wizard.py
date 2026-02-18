"""
Unit tests for Setup Wizard.

Tests interactive setup, configuration generation, and encryption.

Author: Frankenstein 1.0 Team
Phase: 3, Step 6, Test Suite 6
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

from permissions.setup_wizard import SetupWizard, run_setup_wizard


@pytest.fixture
def temp_config_dir(monkeypatch):
    """Create a temporary config directory for testing."""
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir) / ".frankenstein" / "config"
    temp_path.mkdir(parents=True, exist_ok=True)

    # Monkey patch the home directory
    monkeypatch.setattr(
        "permissions.setup_wizard.Path.home",
        lambda: Path(temp_dir)
    )

    yield temp_path

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def wizard(temp_config_dir):
    """Create a fresh SetupWizard instance for each test."""
    return SetupWizard()


class TestWizardInitialization:
    """Test wizard initialization and encryption."""

    def test_wizard_creates_config_dir(self, wizard, temp_config_dir):
        """Test that wizard creates config directory."""
        assert temp_config_dir.exists()
        assert temp_config_dir.is_dir()

    def test_wizard_creates_encryption_key(self, wizard, temp_config_dir):
        """Test that encryption key is created."""
        key_file = temp_config_dir / "setup.key"
        assert key_file.exists()

    def test_config_exists_false_initially(self, wizard):
        """Test that config doesn't exist initially."""
        assert not wizard.config_exists()


class TestDefaultConfiguration:
    """Test default configuration generation."""

    def test_get_default_config(self, wizard):
        """Test getting default configuration."""
        config = wizard.get_default_config()

        assert config["user_role"] == "Admin"
        assert config["automation_enabled"] is True
        assert config["provider_access"]["all_providers"] is True
        assert len(config["provider_access"]["quantum_providers"]) == 15
        assert len(config["provider_access"]["classical_providers"]) == 13

    def test_default_config_all_workflows_enabled(self, wizard):
        """Test that default config enables all workflows."""
        config = wizard.get_default_config()

        workflows = config["automated_workflows"]
        assert workflows["quantum_queue_optimization"] is True
        assert workflows["classical_queue_optimization"] is True
        assert workflows["credential_expiry_warnings"] is True
        assert workflows["resource_usage_reporting"] is True
        assert workflows["provider_health_monitoring"] is True
        assert workflows["hardware_auto_tuning"] is True

    def test_default_config_has_timestamp(self, wizard):
        """Test that default config includes timestamp."""
        config = wizard.get_default_config()

        assert "consent_timestamp" in config
        assert "consent_version" in config
        assert config["consent_version"] == "1.0"


class TestConfigurationSaveLoad:
    """Test configuration save and load functionality."""

    def test_save_and_load_config(self, wizard):
        """Test saving and loading configuration."""
        config = wizard.get_default_config()
        wizard._save_config(config)

        loaded_config = wizard.load_config()

        assert loaded_config is not None
        assert loaded_config["user_role"] == "Admin"
        assert loaded_config["automation_enabled"] is True

    def test_config_is_encrypted(self, wizard, temp_config_dir):
        """Test that saved config is encrypted."""
        config = wizard.get_default_config()
        wizard._save_config(config)

        config_file = temp_config_dir / "user_permissions.json"

        # Read raw file
        with open(config_file, 'rb') as f:
            raw_data = f.read()

        # Should not be plain JSON
        try:
            json.loads(raw_data)
            assert False, "Config should be encrypted, not plain JSON"
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Expected - file is encrypted
            pass

    def test_load_nonexistent_config(self, wizard):
        """Test loading config when file doesn't exist."""
        loaded_config = wizard.load_config()
        assert loaded_config is None

    def test_config_exists_after_save(self, wizard):
        """Test that config_exists returns True after saving."""
        config = wizard.get_default_config()
        wizard._save_config(config)

        assert wizard.config_exists() is True


class TestWizardInteraction:
    """Test wizard interactive methods."""

    def test_get_yes_no_default_true(self, wizard):
        """Test _get_yes_no with default True."""
        with patch('builtins.input', return_value=''):
            result = wizard._get_yes_no("Test question?", default=True)
            assert result is True

    def test_get_yes_no_explicit_yes(self, wizard):
        """Test _get_yes_no with explicit yes."""
        with patch('builtins.input', return_value='y'):
            result = wizard._get_yes_no("Test question?", default=False)
            assert result is True

    def test_get_yes_no_explicit_no(self, wizard):
        """Test _get_yes_no with explicit no."""
        with patch('builtins.input', return_value='n'):
            result = wizard._get_yes_no("Test question?", default=True)
            assert result is False

    def test_get_choice_default(self, wizard):
        """Test _get_choice with default selection."""
        with patch('builtins.input', return_value=''):
            options = ["Option 1", "Option 2", "Option 3"]
            result = wizard._get_choice("Choose:", options, default=1)
            assert result == 1

    def test_get_choice_explicit(self, wizard):
        """Test _get_choice with explicit selection."""
        with patch('builtins.input', return_value='2'):
            options = ["Option 1", "Option 2", "Option 3"]
            result = wizard._get_choice("Choose:", options, default=0)
            assert result == 1  # 0-indexed


class TestProviderSelection:
    """Test provider selection functionality."""

    def test_select_all_providers(self, wizard):
        """Test selecting all 28 providers."""
        with patch.object(wizard, '_get_yes_no', return_value=True):
            providers = wizard._select_provider_categories()

            assert len(providers["quantum_providers"]) == 15
            assert len(providers["classical_providers"]) == 13

    def test_selective_provider_selection(self, wizard):
        """Test selective provider selection."""
        # Simulate: No to all, Yes to quantum only
        responses = [False, True, False, False, False]  # All providers, quantum, nvidia, classical, specialized
        with patch.object(wizard, '_get_yes_no', side_effect=responses):
            providers = wizard._select_provider_categories()

            assert len(providers["quantum_providers"]) == 15
            # Should have no classical providers since all selective options were False
            assert len(providers["classical_providers"]) == 0


class TestAutomationConfiguration:
    """Test automation workflow configuration."""

    def test_configure_all_workflows_enabled(self, wizard):
        """Test configuring all workflows as enabled."""
        with patch.object(wizard, '_get_yes_no', return_value=True):
            workflows = wizard._configure_automation()

            assert workflows["quantum_queue_optimization"] is True
            assert workflows["classical_queue_optimization"] is True
            assert workflows["credential_expiry_warnings"] is True
            assert workflows["resource_usage_reporting"] is True
            assert workflows["provider_health_monitoring"] is True
            assert workflows["hardware_auto_tuning"] is True

    def test_configure_all_workflows_disabled(self, wizard):
        """Test configuring all workflows as disabled."""
        with patch.object(wizard, '_get_yes_no', return_value=False):
            workflows = wizard._configure_automation()

            assert all(v is False for v in workflows.values())


class TestFullWizardRun:
    """Test complete wizard execution."""

    def test_run_wizard_all_defaults(self, wizard):
        """Test running wizard with all default choices."""
        # Mock all inputs to accept defaults
        with patch.object(wizard, '_get_choice', return_value=0), \
             patch.object(wizard, '_get_yes_no', return_value=True):

            config = wizard.run_wizard()

            assert config is not None
            assert config["user_role"] == "Admin"
            assert config["automation_enabled"] is True
            assert config["provider_access"]["all_providers"] is True

    def test_run_wizard_saves_config(self, wizard):
        """Test that running wizard saves configuration."""
        with patch.object(wizard, '_get_choice', return_value=0), \
             patch.object(wizard, '_get_yes_no', return_value=True):

            wizard.run_wizard()

            assert wizard.config_exists() is True

    def test_run_wizard_user_cancels(self, wizard):
        """Test running wizard when user cancels."""
        # Mock inputs: select role, select providers, enable automation, configure workflows, then cancel
        yes_no_responses = [True, True, True, True, True, True, True, True, False]  # Last False cancels
        with patch.object(wizard, '_get_choice', return_value=0), \
             patch.object(wizard, '_get_yes_no', side_effect=yes_no_responses):

            config = wizard.run_wizard()

            assert config is None
            assert not wizard.config_exists()


class TestProviderCoverage:
    """Test that all 28 providers are handled."""

    def test_default_config_has_28_providers(self, wizard):
        """Test that default config includes all 28 providers."""
        config = wizard.get_default_config()

        total_providers = (
            len(config["provider_access"]["quantum_providers"]) +
            len(config["provider_access"]["classical_providers"])
        )

        assert total_providers == 28

    def test_all_quantum_providers_in_config(self, wizard):
        """Test that all 15 quantum providers are in config."""
        config = wizard.get_default_config()

        quantum_providers = config["provider_access"]["quantum_providers"]
        assert "IBM Quantum" in quantum_providers
        assert "AWS Braket" in quantum_providers
        assert len(quantum_providers) == 15

    def test_all_classical_providers_in_config(self, wizard):
        """Test that all 13 classical providers are in config."""
        config = wizard.get_default_config()

        classical_providers = config["provider_access"]["classical_providers"]
        assert "NVIDIA CUDA" in classical_providers
        assert "cuQuantum" in classical_providers
        assert len(classical_providers) == 13


class TestRunSetupWizardFunction:
    """Test the run_setup_wizard helper function."""

    def test_run_setup_wizard_new_config(self, temp_config_dir):
        """Test run_setup_wizard with no existing config."""
        with patch('permissions.setup_wizard.SetupWizard') as MockWizard:
            mock_wizard = MockWizard.return_value
            mock_wizard.config_exists.return_value = False
            mock_wizard.run_wizard.return_value = {"user_role": "Admin"}

            result = run_setup_wizard()

            mock_wizard.run_wizard.assert_called_once()
            assert result == {"user_role": "Admin"}

    def test_run_setup_wizard_existing_config_keep(self, temp_config_dir):
        """Test run_setup_wizard with existing config (keep)."""
        with patch('permissions.setup_wizard.SetupWizard') as MockWizard:
            mock_wizard = MockWizard.return_value
            mock_wizard.config_exists.return_value = True
            mock_wizard._get_yes_no.return_value = False  # Don't reconfigure
            mock_wizard.load_config.return_value = {"user_role": "User"}

            result = run_setup_wizard()

            mock_wizard.load_config.assert_called_once()
            assert result == {"user_role": "User"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

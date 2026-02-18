"""
Setup Wizard - Interactive consent and configuration for Frankenstein 1.0

Provides first-run setup experience for permissions and automation across
all 28 quantum and classical computing providers.

Author: Frankenstein 1.0 Team
Phase: 3, Step 6
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from cryptography.fernet import Fernet
import base64
import hashlib
import os

from permissions.rbac import ALL_PROVIDERS, get_quantum_providers, get_classical_providers


class SetupWizard:
    """
    Interactive CLI wizard for first-run setup.

    Manages user consent for permissions and automation across all 28 providers.
    """

    def __init__(self):
        """Initialize the setup wizard."""
        self.config_dir = Path.home() / ".frankenstein" / "config"
        self.config_file = self.config_dir / "user_permissions.json"
        self.key_file = self.config_dir / "setup.key"

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Initialize encryption
        self.cipher = self._initialize_encryption()

    def _initialize_encryption(self) -> Fernet:
        """Initialize or load encryption key for secure config storage."""
        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                key = f.read()
        else:
            # Generate a deterministic key from system info
            system_id = f"{os.name}-{Path.home()}-setup".encode()
            key_material = hashlib.sha256(system_id).digest()
            key = base64.urlsafe_b64encode(key_material)

            with open(self.key_file, 'wb') as f:
                f.write(key)

            # Restrict permissions on key file (Unix-like systems)
            try:
                os.chmod(self.key_file, 0o600)
            except (OSError, AttributeError):
                pass  # Windows doesn't support chmod

        return Fernet(key)

    def _print_header(self, title: str):
        """Print a formatted header."""
        print("\n" + "=" * 70)
        print(f"  {title}")
        print("=" * 70 + "\n")

    def _print_section(self, title: str):
        """Print a section header."""
        print(f"\n--- {title} ---\n")

    def _get_yes_no(self, prompt: str, default: bool = True) -> bool:
        """
        Get yes/no input from user.

        Args:
            prompt: Question to ask
            default: Default value if user just presses Enter

        Returns:
            True for yes, False for no
        """
        default_str = "Y/n" if default else "y/N"
        while True:
            response = input(f"{prompt} [{default_str}]: ").strip().lower()

            if not response:
                return default

            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            else:
                print("Please enter 'y' or 'n'")

    def _get_choice(self, prompt: str, options: List[str], default: int = 0) -> int:
        """
        Get a choice from a list of options.

        Args:
            prompt: Question to ask
            options: List of option strings
            default: Default option index

        Returns:
            Index of selected option
        """
        print(f"\n{prompt}")
        for i, option in enumerate(options, 1):
            default_marker = " (default)" if i - 1 == default else ""
            print(f"  {i}. {option}{default_marker}")

        while True:
            response = input(f"\nSelect option [1-{len(options)}]: ").strip()

            if not response:
                return default

            try:
                choice = int(response) - 1
                if 0 <= choice < len(options):
                    return choice
                else:
                    print(f"Please enter a number between 1 and {len(options)}")
            except ValueError:
                print("Please enter a valid number")

    def _select_provider_categories(self) -> Dict[str, List[str]]:
        """
        Let user select which provider categories to enable.

        Returns:
            Dictionary with quantum_providers and classical_providers lists
        """
        self._print_section("Provider Access Selection")

        # Ask about all 28 providers
        enable_all = self._get_yes_no(
            "Grant access to all 28 providers (quantum + classical)?",
            default=True
        )

        if enable_all:
            return {
                "quantum_providers": get_quantum_providers(),
                "classical_providers": get_classical_providers()
            }

        # Selective provider access
        print("\nSelect provider categories to enable:")
        categories = {
            "quantum_providers": [],
            "classical_providers": []
        }

        # Quantum providers
        enable_quantum = self._get_yes_no(
            "  Enable all 15 Quantum Providers?",
            default=True
        )
        if enable_quantum:
            categories["quantum_providers"] = get_quantum_providers()

        # NVIDIA Quantum/GPU
        enable_nvidia_quantum = self._get_yes_no(
            "  Enable NVIDIA Quantum/GPU (Quantum Cloud, cuQuantum)?",
            default=True
        )
        if enable_nvidia_quantum:
            categories["classical_providers"].extend([
                "NVIDIA Quantum Cloud",
                "cuQuantum"
            ])

        # Classical Compute Platforms
        enable_classical = self._get_yes_no(
            "  Enable Classical Compute Platforms (CUDA, ROCm, Metal, oneAPI, TPU, etc.)?",
            default=True
        )
        if enable_classical:
            classical_list = [
                "NVIDIA CUDA", "AMD ROCm", "Apple Metal", "Intel oneAPI",
                "Google TPU", "Intel", "AMD"
            ]
            categories["classical_providers"].extend(classical_list)

        # Specialized Hardware
        enable_specialized = self._get_yes_no(
            "  Enable Specialized Hardware (FPGA, NPU, ARM, RISC-V)?",
            default=True
        )
        if enable_specialized:
            specialized_list = [
                "FPGA Compute", "Neural Processing Unit",
                "ARM Compute", "RISC-V Compute"
            ]
            categories["classical_providers"].extend(specialized_list)

        return categories

    def _configure_automation(self) -> Dict[str, bool]:
        """
        Configure automation workflow preferences.

        Returns:
            Dictionary of workflow names to enabled status
        """
        self._print_section("Automation Consent")

        print("Frankenstein can automate several tasks for you.")
        print("Each workflow respects CPU 80% / RAM 75% resource limits.\n")

        workflows = {}

        workflows["quantum_queue_optimization"] = self._get_yes_no(
            "Enable quantum job queue optimization?",
            default=True
        )

        workflows["classical_queue_optimization"] = self._get_yes_no(
            "Enable classical compute queue optimization?",
            default=True
        )

        workflows["credential_expiry_warnings"] = self._get_yes_no(
            "Enable credential expiry warnings (all 28 providers)?",
            default=True
        )

        workflows["resource_usage_reporting"] = self._get_yes_no(
            "Enable resource usage reporting (all 28 providers)?",
            default=True
        )

        workflows["provider_health_monitoring"] = self._get_yes_no(
            "Enable provider health monitoring (all 28 providers)?",
            default=True
        )

        workflows["hardware_auto_tuning"] = self._get_yes_no(
            "Enable hardware optimization auto-tuning (classical providers)?",
            default=True
        )

        return workflows

    def run_wizard(self) -> Dict:
        """
        Run the interactive setup wizard.

        Returns:
            Configuration dictionary
        """
        self._print_header("Frankenstein 1.0 - Setup Wizard")

        print("Welcome to Frankenstein 1.0!")
        print("\nThis wizard will help you configure permissions and automation")
        print("for all 28 quantum and classical computing providers.\n")

        # Step 1: Role Selection
        self._print_section("Role Selection")
        print("Select your user role:")

        role_options = ["Admin", "User", "Agent", "ReadOnly"]
        role_descriptions = [
            "Admin - Full access to all features and providers",
            "User - Access to providers and automation, limited system config",
            "Agent - Automated access only, no credential viewing",
            "ReadOnly - View audit logs only, no execution permissions"
        ]

        role_choice = self._get_choice(
            "Which role would you like?",
            role_descriptions,
            default=0  # Admin
        )
        selected_role = role_options[role_choice]

        # Step 2: Provider Access
        provider_config = self._select_provider_categories()

        # Step 3: Automation Consent
        automation_enabled = self._get_yes_no(
            "\nWould you like to enable automated workflows?",
            default=True
        )

        if automation_enabled:
            workflows = self._configure_automation()
        else:
            # All workflows disabled
            workflows = {
                "quantum_queue_optimization": False,
                "classical_queue_optimization": False,
                "credential_expiry_warnings": False,
                "resource_usage_reporting": False,
                "provider_health_monitoring": False,
                "hardware_auto_tuning": False
            }

        # Step 4: Summary and Confirmation
        self._print_section("Configuration Summary")
        print(f"Role: {selected_role}")
        print(f"Quantum Providers: {len(provider_config['quantum_providers'])} enabled")
        print(f"Classical Providers: {len(provider_config['classical_providers'])} enabled")
        print(f"Automation: {'Enabled' if automation_enabled else 'Disabled'}")

        if automation_enabled:
            enabled_workflows = [k for k, v in workflows.items() if v]
            print(f"Active Workflows: {len(enabled_workflows)}/6")

        print()

        confirm = self._get_yes_no("Save this configuration?", default=True)

        if not confirm:
            print("\nSetup cancelled. Run 'frankenstein setup' to try again.")
            return None

        # Build configuration
        config = {
            "user_role": selected_role,
            "automation_enabled": automation_enabled,
            "provider_access": {
                "all_providers": len(provider_config["quantum_providers"]) == 15 and
                                 len(provider_config["classical_providers"]) == 13,
                "quantum_providers": provider_config["quantum_providers"],
                "classical_providers": provider_config["classical_providers"]
            },
            "automated_workflows": workflows,
            "consent_timestamp": datetime.now().isoformat(),
            "consent_version": "1.0"
        }

        # Save configuration
        self._save_config(config)

        self._print_header("Setup Complete!")
        print("Your configuration has been saved.")
        print("\nYou can reconfigure anytime with: frankenstein setup")
        print()

        return config

    def _save_config(self, config: Dict):
        """
        Save configuration to encrypted file.

        Args:
            config: Configuration dictionary to save
        """
        config_json = json.dumps(config, indent=2)
        encrypted_data = self.cipher.encrypt(config_json.encode())

        with open(self.config_file, 'wb') as f:
            f.write(encrypted_data)

    def load_config(self) -> Optional[Dict]:
        """
        Load configuration from encrypted file.

        Returns:
            Configuration dictionary or None if not found
        """
        if not self.config_file.exists():
            return None

        try:
            with open(self.config_file, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = self.cipher.decrypt(encrypted_data)
            config = json.loads(decrypted_data.decode())

            return config

        except Exception:
            return None

    def config_exists(self) -> bool:
        """
        Check if configuration file exists.

        Returns:
            True if config exists, False otherwise
        """
        return self.config_file.exists()

    def get_default_config(self) -> Dict:
        """
        Get default configuration (all enabled).

        Returns:
            Default configuration dictionary
        """
        return {
            "user_role": "Admin",
            "automation_enabled": True,
            "provider_access": {
                "all_providers": True,
                "quantum_providers": get_quantum_providers(),
                "classical_providers": get_classical_providers()
            },
            "automated_workflows": {
                "quantum_queue_optimization": True,
                "classical_queue_optimization": True,
                "credential_expiry_warnings": True,
                "resource_usage_reporting": True,
                "provider_health_monitoring": True,
                "hardware_auto_tuning": True
            },
            "consent_timestamp": datetime.now().isoformat(),
            "consent_version": "1.0"
        }


def run_setup_wizard() -> Dict:
    """
    Run the setup wizard and return configuration.

    Returns:
        Configuration dictionary
    """
    wizard = SetupWizard()

    # Check if config already exists
    if wizard.config_exists():
        print("\nExisting configuration detected.")
        reconfigure = wizard._get_yes_no(
            "Would you like to reconfigure?",
            default=False
        )

        if not reconfigure:
            print("Keeping existing configuration.")
            return wizard.load_config()

    return wizard.run_wizard()

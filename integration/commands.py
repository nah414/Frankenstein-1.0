#!/usr/bin/env python3
"""
FRANKENSTEIN 1.0 - Integration Terminal Commands
Phase 3: Terminal command handlers for hardware discovery and provider registry.

Commands:
  hardware    - Hardware discovery and fingerprinting (Step 1)
  providers   - Provider registry listing and management (Step 2)
  connect     - Connect to a compute provider
  disconnect  - Disconnect from a provider
  credentials - Manage provider API keys and credentials

ALL imports are lazy — modules only load when the command is invoked.
"""

from typing import List, Callable


def handle_providers_command(args: List[str], write_fn: Callable) -> None:
    """
    Handle the 'providers' terminal command.

    Usage:
      providers              Show provider summary
      providers scan         Refresh SDK availability scan
      providers info <id>    Detailed info for a provider
      providers install <id> Show pip install command
      providers quantum      List quantum providers only
      providers classical    List classical providers only
    """
    from integration.providers.registry import get_registry, ProviderType

    registry = get_registry()

    if not args:
        write_fn(registry.format_summary() + "\n")
        return

    subcmd = args[0].lower()

    if subcmd == "scan":
        write_fn("🔍 Scanning all provider SDKs...\n")
        results = registry.scan_all(force=True)
        installed = sum(1 for s in results.values() if s.sdk_installed)
        write_fn(f"✅ Scan complete: {installed}/{len(results)} SDKs installed\n\n")
        write_fn(registry.format_summary() + "\n")

    elif subcmd == "info":
        if len(args) < 2:
            write_fn("❌ Usage: providers info <provider_id>\n")
            write_fn("   Example: providers info ibm_quantum\n")
            return
        write_fn(registry.format_provider_detail(args[1]) + "\n\n")

    elif subcmd == "install":
        if len(args) < 2:
            write_fn("❌ Usage: providers install <provider_id>\n")
            return
        info = registry.get_provider(args[1])
        if not info:
            write_fn(f"❌ Unknown provider: {args[1]}\n")
            return
        write_fn(f"\n📦 To install {info.name} SDK:\n")
        write_fn(f"   pip install {info.sdk_package}\n\n")
        if info.notes:
            write_fn(f"   Note: {info.notes}\n\n")

    elif subcmd == "quantum":
        write_fn("\n⚛️  QUANTUM PROVIDERS:\n\n")
        for p in registry.list_providers(ProviderType.QUANTUM_CLOUD):
            state = registry.get_state(p.id)
            icon = "🟢" if state.sdk_installed else "⚪"
            write_fn(f"  {icon} {p.id:<22} {p.name:<24} {p.max_qubits}q\n")
        for p in registry.list_providers(ProviderType.QUANTUM_LOCAL):
            state = registry.get_state(p.id)
            icon = "🟢" if state.sdk_installed else "⚪"
            write_fn(f"  {icon} {p.id:<22} {p.name:<24} {p.max_qubits}q\n")
        write_fn("\n")

    elif subcmd == "classical":
        write_fn("\n⚡ CLASSICAL PROVIDERS:\n\n")
        for ptype in [ProviderType.CLASSICAL_CPU, ProviderType.CLASSICAL_GPU, ProviderType.CLASSICAL_ACCEL]:
            for p in registry.list_providers(ptype):
                state = registry.get_state(p.id)
                icon = "🟢" if state.sdk_installed else "⚪"
                write_fn(f"  {icon} {p.id:<22} {p.name}\n")
        write_fn("\n")

    elif subcmd == "list":
        # Alias for no-arg
        write_fn(registry.format_summary() + "\n")

    elif subcmd in ("suggest", "recommend", "guide"):
        from integration.guide import generate_suggestions
        generate_suggestions(write_fn)

    elif subcmd == "setup":
        if len(args) < 2:
            write_fn("❌ Usage: providers setup <provider_id>\n")
            write_fn("   Example: providers setup ibm_quantum\n")
            return
        from integration.guide import generate_setup_guide
        generate_setup_guide(args[1], write_fn)

    else:
        write_fn(f"❌ Unknown subcommand: {subcmd}\n")
        write_fn("   Usage: providers [scan|info|install|quantum|classical|suggest|setup <id>]\n")


def handle_connect_command(args: List[str], write_fn: Callable) -> None:
    """
    Handle the 'connect' terminal command.

    Usage:
      connect <provider_id>                          Connect with saved credentials
      connect <provider_id> --token TOKEN            Connect with API token
      connect <provider_id> --credentials '{...}'    Connect with JSON credentials
      connect                                        Show usage help
    """
    from integration.providers.registry import get_registry, ProviderStatus
    import json

    if not args:
        write_fn("\n🔌 CONNECT — Establish provider connection\n\n")
        write_fn("  Usage: connect <provider_id> [--token TOKEN] [--credentials JSON]\n\n")
        write_fn("  Examples:\n")
        write_fn("    connect local_simulator\n")
        write_fn("    connect ibm_quantum --token 'your_api_token_here'\n")
        write_fn("    connect aws_braket --credentials '{\"aws_access_key_id\":\"...\"}'\n\n")
        write_fn("  Run 'providers' to see available provider IDs.\n")
        write_fn("  Run 'help connect' for detailed credential setup.\n\n")
        return

    provider_id = args[0].lower()
    credentials = None
    save_creds = False

    # Parse credential arguments
    i = 1
    while i < len(args):
        if args[i] == '--token' and i + 1 < len(args):
            credentials = {"token": args[i + 1]}
            i += 2
        elif args[i] == '--credentials' and i + 1 < len(args):
            try:
                credentials = json.loads(args[i + 1])
            except json.JSONDecodeError:
                write_fn(f"❌ Invalid JSON in --credentials argument\n")
                write_fn(f"   Expected: --credentials '{{\"key\": \"value\"}}'\n")
                return
            i += 2
        elif args[i] == '--save':
            save_creds = True
            i += 1
        else:
            i += 1

    registry = get_registry()
    info = registry.get_provider(provider_id)

    if not info:
        write_fn(f"❌ Unknown provider: {provider_id}\n")
        write_fn("   Run 'providers' to see available IDs.\n")
        return

    # Auto-load saved credentials if none provided inline
    if credentials is None:
        try:
            from integration.credentials import get_credential_manager
            saved = get_credential_manager().get_credentials(provider_id)
            if saved:
                credentials = saved
                write_fn(f"   Using saved credentials for {provider_id}\n")
        except Exception:
            pass

    # Check if credentials are required but missing
    if credentials is None:
        from integration.credentials import get_required_fields
        req = get_required_fields(provider_id)
        if req["fields"]:
            # Provider needs credentials — show guidance instead of attempting
            fields_str = ", ".join(req["fields"])
            write_fn(f"\n⚠️  {provider_id} requires credentials to connect.\n\n")
            write_fn(f"  Required: {fields_str}\n")
            write_fn(f"  Get it at: {req['help']}\n\n")
            write_fn(f"  Save credentials:\n")
            if len(req["fields"]) == 1 and req["fields"][0] == "token":
                write_fn(f"    credentials save {provider_id} --token \"YOUR_API_TOKEN\"\n\n")
            else:
                cred_example = ", ".join(f'"{f}":"..."' for f in req["fields"])
                write_fn(f"    credentials save {provider_id} --credentials '{{{cred_example}}}'\n\n")
            write_fn(f"  Then connect:\n")
            write_fn(f"    connect {provider_id}\n\n")
            return

    write_fn(f"🔌 Connecting to {info.name}...\n")

    # Pass credentials to registry
    if credentials:
        state = registry.connect(provider_id, credentials=credentials)
    else:
        state = registry.connect(provider_id)

    if state.status == ProviderStatus.CONNECTED:
        write_fn(f"✅ Connected to {info.name}\n")
        if state.available_backends:
            write_fn(f"   Backends: {', '.join(str(b) for b in state.available_backends[:5])}")
            if len(state.available_backends) > 5:
                write_fn(f" (+{len(state.available_backends) - 5} more)")
            write_fn("\n")
        # Optionally save credentials for future use
        if save_creds and credentials:
            try:
                from integration.credentials import get_credential_manager
                get_credential_manager().save_credentials(provider_id, credentials)
                write_fn(f"   💾 Credentials saved for future connections\n")
            except Exception:
                pass
        write_fn(f"\n💡 Tip: Run 'providers info {provider_id}' to see backend details\n")
    elif state.status == ProviderStatus.UNAVAILABLE:
        write_fn(f"❌ SDK not installed.\n")
        write_fn(f"   Install: pip install {info.sdk_package}\n")
    elif state.status == ProviderStatus.NOT_CONFIGURED:
        write_fn(f"⚠️  SDK installed but credentials not configured.\n")
        write_fn(f"   Option 1: connect {provider_id} --token 'YOUR_API_TOKEN'\n")
        write_fn(f"   Option 2: credentials save {provider_id} --token 'YOUR_TOKEN'\n")
        write_fn(f"   Provider website: {info.website}\n")
    else:
        write_fn(f"❌ Connection failed: {state.last_error}\n")
        if "token" in str(state.last_error).lower() or "credential" in str(state.last_error).lower():
            write_fn(f"\n💡 Try providing credentials:\n")
            write_fn(f"   connect {provider_id} --token 'YOUR_API_TOKEN'\n")
            write_fn(f"   See 'help connect' for more options.\n")


def handle_disconnect_command(args: List[str], write_fn: Callable) -> None:
    """
    Handle the 'disconnect' terminal command.

    Usage:
      disconnect <provider_id>   Disconnect from a provider
      disconnect all              Disconnect all providers
    """
    from integration.providers.registry import get_registry

    if not args:
        write_fn("❌ Usage: disconnect <provider_id> or disconnect all\n")
        return

    registry = get_registry()

    if args[0].lower() == "all":
        connected = registry.get_connected_providers()
        for pid in connected:
            registry.disconnect(pid)
        write_fn(f"🔌 Disconnected from {len(connected)} provider(s).\n")
        return

    provider_id = args[0].lower()
    info = registry.get_provider(provider_id)

    if not info:
        write_fn(f"❌ Unknown provider: {provider_id}\n")
        return

    registry.disconnect(provider_id)
    write_fn(f"🔌 Disconnected from {info.name}.\n")


def handle_credentials_command(args: List[str], write_fn: Callable) -> None:
    """
    Handle the 'credentials' terminal command.

    GUI-COMPATIBLE: All operations use inline arguments (no stdin prompts).

    Usage:
      credentials save <provider_id> --token TOKEN          Save API token
      credentials save <provider_id> --credentials '{...}'  Save JSON credentials
      credentials list                                      List saved providers
      credentials delete <provider_id>                      Delete saved credentials
      credentials show <provider_id>                        Show saved (masked)
      credentials verify <provider_id>                      Test saved credentials
    """
    from integration.credentials import get_credential_manager, get_required_fields
    import json

    cred_mgr = get_credential_manager()

    if not args:
        write_fn("\n🔐 CREDENTIALS MANAGER\n\n")
        write_fn("  Save API keys and credentials for cloud providers.\n")
        write_fn("  Credentials stored in ~/.frankenstein/credentials.json\n\n")
        write_fn("  COMMANDS:\n")
        write_fn("    credentials save <id> --token TOKEN\n")
        write_fn("    credentials save <id> --credentials '{\"key\":\"val\"}'\n")
        write_fn("    credentials list\n")
        write_fn("    credentials delete <id>\n")
        write_fn("    credentials show <id>\n")
        write_fn("    credentials verify <id>\n\n")
        write_fn("  EXAMPLES:\n")
        write_fn("    credentials save ibm_quantum --token \"crn:v1:abc123...\"\n")
        write_fn("    credentials save aws_braket --credentials '{\"aws_access_key_id\":\"AKIA...\",\"aws_secret_access_key\":\"wJal...\",\"region_name\":\"us-east-1\"}'\n")
        write_fn("    credentials verify ibm_quantum\n\n")
        write_fn("  After saving, just run 'connect <id>' — credentials load automatically.\n\n")
        return

    subcmd = args[0].lower()

    if subcmd == "save":
        if len(args) < 2:
            write_fn("❌ Usage: credentials save <provider_id> --token TOKEN\n")
            write_fn("         credentials save <provider_id> --credentials '{...}'\n")
            return

        provider_id = args[1].lower()
        credentials = None

        # Parse inline credential arguments
        i = 2
        while i < len(args):
            if args[i] == '--token' and i + 1 < len(args):
                credentials = {"token": args[i + 1]}
                i += 2
            elif args[i] == '--credentials' and i + 1 < len(args):
                try:
                    credentials = json.loads(args[i + 1])
                except json.JSONDecodeError:
                    write_fn(f"❌ Invalid JSON in --credentials argument\n")
                    write_fn(f"   Expected: --credentials '{{\"key\": \"value\"}}'\n")
                    return
                i += 2
            elif args[i].startswith('--') and i + 1 < len(args):
                key = args[i][2:]  # Remove --
                if credentials is None:
                    credentials = {}
                credentials[key] = args[i + 1]
                i += 2
            else:
                i += 1

        if credentials is None:
            write_fn(f"❌ No credentials provided.\n\n")
            write_fn(f"  Usage:\n")
            write_fn(f"    credentials save {provider_id} --token YOUR_TOKEN\n")
            write_fn(f"    credentials save {provider_id} --credentials '{{\"key\":\"val\"}}'\n\n")
            # Show provider-specific hints
            req = get_required_fields(provider_id)
            if req["fields"]:
                fields_str = ", ".join(req["fields"])
                write_fn(f"  Required for {provider_id}: {fields_str}\n")
                write_fn(f"  {req['help']}\n\n")
            return

        # Save credentials
        if cred_mgr.save_credentials(provider_id, credentials):
            write_fn(f"✅ Credentials saved for {provider_id}\n")
            write_fn(f"   Location: {cred_mgr.cred_file}\n")
            write_fn(f"\n💡 Now connect without inline credentials:\n")
            write_fn(f"   connect {provider_id}\n\n")
        else:
            write_fn(f"❌ Failed to save credentials for {provider_id}\n\n")

    elif subcmd == "list":
        providers = cred_mgr.list_saved_providers()
        if providers:
            write_fn("\n🔐 SAVED CREDENTIALS:\n\n")
            for provider_id in providers:
                write_fn(f"  ✅ {provider_id}\n")
            write_fn(f"\n  Total: {len(providers)} provider(s)\n")
            write_fn(f"  Storage: {cred_mgr.cred_file}\n\n")
        else:
            write_fn("\n🔐 No saved credentials.\n\n")
            write_fn("   Use 'credentials save <id> --token TOKEN' to save.\n\n")

    elif subcmd == "delete":
        if len(args) < 2:
            write_fn("❌ Usage: credentials delete <provider_id>\n")
            return

        provider_id = args[1].lower()
        if cred_mgr.delete_credentials(provider_id):
            write_fn(f"✅ Credentials deleted for {provider_id}\n")
        else:
            write_fn(f"❌ No saved credentials found for {provider_id}\n")

    elif subcmd == "show":
        if len(args) < 2:
            write_fn("❌ Usage: credentials show <provider_id>\n")
            return

        provider_id = args[1].lower()
        creds = cred_mgr.get_credentials(provider_id)

        if creds:
            write_fn(f"\n🔐 Credentials for {provider_id}:\n\n")
            for key, value in creds.items():
                # Mask sensitive values
                val_str = str(value)
                if any(s in key.lower() for s in ['secret', 'password', 'token', 'key']):
                    if len(val_str) > 8:
                        masked = val_str[:4] + "..." + val_str[-4:]
                    else:
                        masked = "***"
                    write_fn(f"  {key}: {masked}\n")
                else:
                    write_fn(f"  {key}: {val_str}\n")
            write_fn("\n")
        else:
            write_fn(f"❌ No saved credentials found for {provider_id}\n")

    elif subcmd == "verify":
        if len(args) < 2:
            write_fn("❌ Usage: credentials verify <provider_id>\n")
            return

        provider_id = args[1].lower()
        creds = cred_mgr.get_credentials(provider_id)

        if not creds:
            req = get_required_fields(provider_id)
            write_fn(f"❌ No saved credentials for {provider_id}\n\n")
            if req["fields"]:
                fields_str = ", ".join(req["fields"])
                write_fn(f"  Required: {fields_str}\n")
                write_fn(f"  {req['help']}\n\n")
                if len(req["fields"]) == 1 and req["fields"][0] == "token":
                    write_fn(f"  Save: credentials save {provider_id} --token YOUR_TOKEN\n\n")
                else:
                    cred_example = ", ".join(f'"{f}":"..."' for f in req["fields"])
                    write_fn(f"  Save: credentials save {provider_id} --credentials '{{{cred_example}}}'\n\n")
            else:
                write_fn(f"  {provider_id} does not require credentials.\n\n")
            return

        write_fn(f"🔍 Verifying credentials for {provider_id}...\n")

        from integration.providers.registry import get_registry, ProviderStatus
        registry = get_registry()

        # Check SDK first
        state = registry.get_state(provider_id)
        if not state.sdk_installed:
            info = registry.get_provider(provider_id)
            pkg = info.sdk_package if info else "unknown"
            write_fn(f"⚠️  Cannot verify — SDK not installed. Run: pip install {pkg}\n")
            return

        # Attempt connection with saved credentials
        state = registry.connect(provider_id, credentials=creds)

        if state.status == ProviderStatus.CONNECTED:
            write_fn(f"✅ Credentials verified for {provider_id} — connection successful\n")
            # Disconnect after verification
            registry.disconnect(provider_id)
        elif state.status == ProviderStatus.UNAVAILABLE:
            info = registry.get_provider(provider_id)
            pkg = info.sdk_package if info else "unknown"
            write_fn(f"⚠️  Cannot verify — SDK not installed. Run: pip install {pkg}\n")
        else:
            error = state.last_error or "Unknown error"
            write_fn(f"❌ Credentials invalid for {provider_id} — {error}\n")

    else:
        write_fn(f"❌ Unknown subcommand: {subcmd}\n")
        write_fn("   Usage: credentials [save|list|delete|show|verify]\n")

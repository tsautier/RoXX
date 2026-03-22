"""
RoXX Factory Reset - Reset configuration to defaults
Linux replacement for bin/resetfactory
"""

import sys
import shutil
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
import questionary
from questionary import Style

from roxx.utils.system import SystemManager

console = Console()

custom_style = Style([
    ('qmark', 'fg:#673ab7 bold'),
    ('question', 'bold'),
    ('answer', 'fg:#f44336 bold'),
])


def reset_factory():
    """Reset RoXX configuration to factory defaults"""
    
    # Check admin privileges
    if not SystemManager.is_admin():
        console.print("\n[bold red]⚠ Error:[/bold red] Administrator privileges required.")
        console.print("Please run as:", style="yellow")
        console.print("  • sudo python -m roxx.cli.reset", style="cyan")
        
        sys.exit(1)
    
    # Show warning
    console.clear()
    
    warning = Panel.fit(
        "[bold red]⚠ WARNING - Factory Reset[/bold red]\n\n"
        "[yellow]This will DELETE all RoXX configuration:[/yellow]\n"
        "  • Authentication settings (inWebo, TOTP, EntraID)\n"
        "  • User databases\n"
        "  • Certificates and keys\n"
        "  • FreeRADIUS configuration\n"
        "  • All custom settings\n\n"
        "[bold]This action CANNOT be undone![/bold]",
        border_style="red",
        title="[bold red]DANGER ZONE[/bold red]"
    )
    console.print(warning)
    console.print()
    
    # Confirm action
    if not questionary.confirm(
        "Are you ABSOLUTELY SURE you want to reset to factory defaults?",
        default=False,
        style=custom_style
    ).ask():
        console.print("\n[green]Reset cancelled. No changes made.[/green]\n")
        sys.exit(0)
    
    # Double confirmation
    confirm_text = questionary.text(
        'Type "RESET" (in capitals) to confirm:',
        style=custom_style
    ).ask()
    
    if confirm_text != "RESET":
        console.print("\n[yellow]Confirmation failed. Reset cancelled.[/yellow]\n")
        sys.exit(0)
    
    # Perform reset
    console.print("\n[bold yellow]Performing factory reset...[/bold yellow]\n")
    
    config_dir = SystemManager.get_config_dir()
    data_dir = SystemManager.get_data_dir()
    
    directories_to_reset = [
        (config_dir, "Configuration"),
        (data_dir, "Data"),
    ]
    
    errors = []
    
    for directory, name in directories_to_reset:
        try:
            if directory.exists():
                console.print(f"  • Removing {name}: {directory}")
                shutil.rmtree(directory)
                console.print(f"    [green]✓[/green] {name} removed")
            else:
                console.print(f"  • {name} not found: {directory}")
                console.print(f"    [dim]⊘ Already clean[/dim]")
        except Exception as e:
            errors.append(f"{name}: {e}")
            console.print(f"    [red]✗[/red] Error: {e}")
    
    console.print()
    
    # Summary
    if errors:
        console.print("[bold yellow]Reset completed with errors:[/bold yellow]")
        for error in errors:
            console.print(f"  [red]✗[/red] {error}")
        console.print("\n[yellow]Some files may require manual deletion.[/yellow]")
    else:
        console.print("[bold green]✓ Factory reset completed successfully![/bold green]")
    
    console.print("\n[bold]Next steps:[/bold]")
    console.print("  1. Run setup wizard: [cyan]python -m roxx.cli.setup[/cyan]")
    console.print("  2. Configure authentication providers")
    console.print("  3. Restart services")
    console.print()


def main():
    """Main entry point"""
    try:
        reset_factory()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Reset cancelled by user.[/yellow]\n")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
RoXX Admin Console - Modern TUI with Rich
Multi-OS compatible console interface
"""

import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich import box
import questionary
from questionary import Style

from roxx.core.services import ServiceManager, ServiceStatus
from roxx.utils.system import SystemManager
from roxx.utils.i18n import translate as _, set_locale, get_locale

# Custom style for questionary
custom_style = Style([
    ('qmark', 'fg:#673ab7 bold'),
    ('question', 'bold'),
    ('answer', 'fg:#f44336 bold'),
    ('pointer', 'fg:#673ab7 bold'),
    ('highlighted', 'fg:#673ab7 bold'),
    ('selected', 'fg:#cc5454'),
    ('separator', 'fg:#cc5454'),
    ('instruction', ''),
    ('text', ''),
])

console = Console()
service_mgr = ServiceManager()


def check_admin():
    """Check administrator privileges"""
    if not SystemManager.is_admin():
        console.print("\n[bold red]⚠ Warning:[/bold red] This program requires administrator privileges.")
        console.print("Please run as:", style="yellow")
        
        if SystemManager.get_os() == 'windows':
            console.print("  • Right-click → Run as administrator", style="cyan")
        else:
            console.print("  • sudo roxx-console", style="cyan")
        
        sys.exit(1)


def show_header():
    """Display console header"""
    console.clear()
    
    header = Panel.fit(
        f"[bold cyan]{_('app_title', 'RoXX Admin Console')}[/bold cyan]\n"
        f"[dim]v1.0-beta - Multi-OS Edition[/dim]\n"
        f"[yellow]OS:[/yellow] {SystemManager.get_os().title()} | "
        f"[yellow]Locale:[/yellow] {get_locale()}",
        border_style="cyan",
        box=box.DOUBLE
    )
    console.print(header)
    console.print()


def show_services():
    """Display status of all services"""
    show_header()
    
    table = Table(title="📊 Services Status", box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Service", style="cyan", width=20)
    table.add_column("Status", justify="center", width=15)
    table.add_column("Description", style="dim", width=40)
    
    descriptions = {
        'freeradius': 'RADIUS Authentication Server',
        'winbind': 'Samba Winbind Service',
        'smbd': 'Samba SMB Daemon',
        'nmbd': 'Samba NetBIOS Daemon',
    }
    
    with console.status("[bold green]Checking services...", spinner="dots"):
        statuses = service_mgr.get_all_services_status()
    
    for service, status in statuses.items():
        if status == ServiceStatus.RUNNING:
            status_text = "[green]● RUNNING[/green]"
        elif status == ServiceStatus.STOPPED:
            status_text = "[red]○ STOPPED[/red]"
        else:
            status_text = "[yellow]? UNKNOWN[/yellow]"
        
        table.add_row(
            service.upper(),
            status_text,
            descriptions.get(service, "")
        )
    
    console.print(table)
    console.print()


def control_service():
    """Service control menu"""
    show_header()
    
    # Service selection
    service = questionary.select(
        "Select a service to control:",
        choices=['freeradius', 'winbind', 'smbd', 'nmbd', '← Back'],
        style=custom_style
    ).ask()
    
    if service == '← Back' or not service:
        return
    
    # Action selection
    action = questionary.select(
        f"Action for {service.upper()}:",
        choices=['Start', 'Stop', 'Restart', '← Back'],
        style=custom_style
    ).ask()
    
    if action == '← Back' or not action:
        return
    
    # Execute action
    with console.status(f"[bold yellow]{action}ing {service}...", spinner="dots"):
        if action == 'Start':
            success = service_mgr.start(service)
        elif action == 'Stop':
            success = service_mgr.stop(service)
        elif action == 'Restart':
            success = service_mgr.restart(service)
        else:
            success = False
    
    if success:
        console.print(f"\n[green]✓[/green] {action} {service} successful!", style="bold green")
    else:
        console.print(f"\n[red]✗[/red] Failed to {action.lower()} {service}", style="bold red")
    
    input("\nPress Enter to continue...")


def show_system_info():
    """Display system information"""
    import psutil
    import platform
    
    show_header()
    
    table = Table(title="💻 System Information", box=box.ROUNDED)
    table.add_column("Property", style="cyan", width=25)
    table.add_column("Value", style="green")
    
    # System information
    table.add_row("Operating System", f"{platform.system()} {platform.release()}")
    table.add_row("Architecture", platform.machine())
    table.add_row("Python Version", platform.python_version())
    
    # CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    table.add_row("CPU Usage", f"{cpu_percent}%")
    table.add_row("CPU Count", str(psutil.cpu_count()))
    
    # Memory
    mem = psutil.virtual_memory()
    table.add_row("Memory Total", f"{mem.total / (1024**3):.2f} GB")
    table.add_row("Memory Used", f"{mem.used / (1024**3):.2f} GB ({mem.percent}%)")
    table.add_row("Memory Free", f"{mem.available / (1024**3):.2f} GB")
    
    # Disk
    disk = psutil.disk_usage('/')
    table.add_row("Disk Total", f"{disk.total / (1024**3):.2f} GB")
    table.add_row("Disk Used", f"{disk.used / (1024**3):.2f} GB ({disk.percent}%)")
    table.add_row("Disk Free", f"{disk.free / (1024**3):.2f} GB")
    
    console.print(table)
    console.print()
    input("\nPress Enter to continue...")


def show_configuration():
    """Configuration menu"""
    show_header()
    
    config_dir = SystemManager.get_config_dir()
    
    console.print(f"[bold]Configuration Directory:[/bold] {config_dir}\n")
    
    files = {
        'clients.conf': 'RADIUS Clients (NAS)',
        'users.roxx': 'Local Users',
        'freeradius_site.conf': 'FreeRADIUS Site Configuration',
    }
    
    choices = [f"{name} - {desc}" for name, desc in files.items()]
    choices.append('← Back')
    
    choice = questionary.select(
        "Select a configuration file to edit:",
        choices=choices,
        style=custom_style
    ).ask()
    
    if choice == '← Back' or not choice:
        return
    
    filename = choice.split(' - ')[0]
    filepath = config_dir / filename
    
    if not filepath.exists():
        console.print(f"\n[yellow]⚠[/yellow] File not found: {filepath}", style="yellow")
        input("\nPress Enter to continue...")
        return
    
    # Open with default editor
    import subprocess
    editor = 'notepad' if SystemManager.get_os() == 'windows' else 'nano'
    
    try:
        subprocess.run([editor, str(filepath)])
    except Exception as e:
        console.print(f"\n[red]✗[/red] Error opening editor: {e}", style="red")
        input("\nPress Enter to continue...")


def main_menu():
    """Main console menu"""
    while True:
        show_header()
        
        choice = questionary.select(
            "Select an option:",
            choices=[
                '📊 Services Status',
                '🎮 Control Services',
                '💻 System Information',
                '⚙️  Configuration',
                '🔐 Local PKI',
                '📝 View Logs',
                '🐛 Debug Mode',
                '🌐 Change Language',
                '🚪 Exit'
            ],
            style=custom_style
        ).ask()
        
        if not choice or choice == '🚪 Exit':
            console.print("\n[bold cyan]Goodbye![/bold cyan]\n")
            break
        elif choice == '📊 Services Status':
            show_services()
            input("\nPress Enter to continue...")
        elif choice == '🎮 Control Services':
            control_service()
        elif choice == '💻 System Information':
            show_system_info()
        elif choice == '⚙️  Configuration':
            show_configuration()
        elif choice == '🌐 Change Language':
            lang = questionary.select(
                "Select language:",
                choices=['EN - English', 'FR - Français', '← Back'],
                style=custom_style
            ).ask()
            if lang and lang != '← Back':
                set_locale(lang.split(' - ')[0])
        else:
            console.print("\n[yellow]This feature is not yet implemented.[/yellow]")
            input("\nPress Enter to continue...")


def main():
    """Main entry point"""
    try:
        check_admin()
        main_menu()
    except KeyboardInterrupt:
        console.print("\n\n[bold yellow]Interrupted by user[/bold yellow]\n")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}\n", style="red")
        sys.exit(1)


if __name__ == "__main__":
    main()

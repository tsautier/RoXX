"""
RoXX Admin Console - Modern TUI with Rich
Linux console interface
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
        
        console.print("  • sudo roxx-console", style="cyan")
        
        sys.exit(1)


def show_header():
    """Display console header"""
    console.clear()
    
    header = Panel.fit(
        f"[bold cyan]{_('app_title', 'RoXX Admin Console')}[/bold cyan]\n"
        f"[dim]v1.0-beta - Linux Edition[/dim]\n"
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
    table.add_row("Operating System", "Linux (RoXX)")
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
    editor = 'nano'
    
    try:
        subprocess.run([editor, str(filepath)])
    except Exception as e:
        console.print(f"\n[red]✗[/red] Error opening editor: {e}", style="red")
        input("\nPress Enter to continue...")


def manage_admins():
    """Manage Admin Accounts"""
    from roxx.core.auth.manager import AuthManager
    AuthManager.init()
    
    while True:
        show_header()
        
        # List admins
        admins = AuthManager.list_admins()
        table = Table(title="Admin Accounts", box=box.SIMPLE)
        table.add_column("Username", style="green")
        table.add_column("Source", style="cyan")
        table.add_column("Last Login", style="dim")
        table.add_column("MFA", style="yellow")
        
        for admin in admins:
            # Check MFA status safely
            mfa_status = "Enabled" if _check_admin_mfa(admin['username']) else "Disabled"
            table.add_row(
                admin['username'], 
                admin['auth_source'].upper(), 
                str(admin['last_login'] or 'Never'),
                mfa_status
            )
        console.print(table)
        console.print()
        
        action = questionary.select(
            "Admin Actions:",
            choices=[
                'Add New Admin',
                'Delete Admin',
                'Reset MFA for Admin',
                '← Back'
            ],
            style=custom_style
        ).ask()
        
        if not action or action == '← Back':
            return
            
        if action == 'Add New Admin':
            _add_admin()
        elif action == 'Delete Admin':
            _delete_admin(admins)
        elif action == 'Reset MFA for Admin':
            _reset_mfa(admins)

def _check_admin_mfa(username):
    """Helper to check if MFA is enabled"""
    from roxx.core.auth.db import AdminDatabase
    import sqlite3
    conn = AdminDatabase.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT mfa_secret FROM admins WHERE username = ?", (username,))
    res = cursor.fetchone()
    conn.close()
    return bool(res and res[0])

def _add_admin():
    """Add a new admin"""
    from roxx.core.auth.manager import AuthManager
    
    username = questionary.text("Username:", style=custom_style).ask()
    if not username: return
    
    source = questionary.select(
        "Auth Source:",
        choices=['local', 'ldap', 'saml'],
        style=custom_style
    ).ask()
    
    password = None
    if source == 'local':
        password = questionary.password("Password (min 12 chars):", style=custom_style).ask()
        if not password: return
        
    success, msg = AuthManager.create_admin(username, password, source)
    if success:
        console.print(f"\n[green]✓ {msg}[/green]")
    else:
        console.print(f"\n[red]✗ {msg}[/red]")
    input("\nPress Enter to continue...")

def _delete_admin(admins):
    """Delete an admin"""
    from roxx.core.auth.manager import AuthManager
    
    choices = [a['username'] for a in admins if a['username'] != 'admin']
    if not choices:
        console.print("[yellow]No deletable admins found.[/yellow]")
        input("\nPress Enter to continue...")
        return
        
    username = questionary.select(
        "Select admin to delete:",
        choices=choices + ['← Back'],
        style=custom_style
    ).ask()
    
    if not username or username == '← Back': return
    
    if questionary.confirm(f"Are you sure you want to delete {username}?", default=False).ask():
        success, msg = AuthManager.delete_admin(username)
        if success:
             console.print(f"\n[green]✓ {msg}[/green]")
        else:
             console.print(f"\n[red]✗ {msg}[/red]")
        input("\nPress Enter to continue...")

def _reset_mfa(admins):
    """Reset MFA for an admin"""
    from roxx.core.auth.manager import AuthManager
    
    username = questionary.select(
        "Select admin to reset MFA:",
        choices=[a['username'] for a in admins] + ['← Back'],
        style=custom_style
    ).ask()
    
    if not username or username == '← Back': return
    
    AuthManager.disable_mfa(username)
    console.print(f"\n[green]✓ MFA disabled for {username}. They can re-enroll on next login.[/green]")
    input("\nPress Enter to continue...")




def manage_pki():
    """Local PKI Management Menu"""
    show_header()
    
    config_dir = SystemManager.get_config_dir()
    certs_dir = config_dir / "certs"
    certs_dir.mkdir(parents=True, exist_ok=True)
    
    while True:
        show_header()
        
        # List existing certificates
        console.print(Panel(f"[bold]Certificates Directory:[/bold] {certs_dir}", style="cyan"))
        
        certs = list(certs_dir.glob("*.pem"))
        if certs:
            table = Table(box=box.SIMPLE)
            table.add_column("Filename", style="green")
            table.add_column("Size", style="dim")
            
            for cert in certs:
                table.add_row(cert.name, f"{cert.stat().st_size} bytes")
            console.print(table)
        else:
            console.print("[dim]No certificates found.[/dim]")
        
        console.print()
        
        action = questionary.select(
            "PKI Actions:",
            choices=[
                'Generate Self-Signed CA',
                'Generate Client Certificate',
                'View Certificate Details',
                '← Back'
            ],
            style=custom_style
        ).ask()
        
        if not action or action == '← Back':
            return
            
        if action == 'Generate Self-Signed CA':
            _generate_ca(certs_dir)
        elif action == 'Generate Client Certificate':
            _generate_client_cert(certs_dir)
        elif action == 'View Certificate Details':
            _view_cert_details(certs_dir)


def _generate_ca(certs_dir: Path):
    """Generate a self-signed CA"""
    if (certs_dir / "ca_cert.pem").exists():
        if not questionary.confirm("CA already exists. Overwrite?", default=False).ask():
            return

    console.print("\n[yellow]Generating Self-Signed CA...[/yellow]")
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import datetime

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, u"RoXX Local CA"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=3650)
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None), critical=True,
        ).sign(private_key, hashes.SHA256())

        # Save
        with open(certs_dir / "ca_key.pem", "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
            
        with open(certs_dir / "ca_cert.pem", "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
            
        console.print("[green]✓ CA generated successfully![/green]")
        input("\nPress Enter to continue...")
        
    except ImportError:
        console.print("[red]Error: cryptography module not found.[/red]")
        input("\nPress Enter to continue...")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        input("\nPress Enter to continue...")


def _generate_client_cert(certs_dir: Path):
    """Generate a client certificate signed by local CA"""
    ca_key_path = certs_dir / "ca_key.pem"
    ca_cert_path = certs_dir / "ca_cert.pem"
    
    if not ca_key_path.exists() or not ca_cert_path.exists():
        console.print("[red]Error: CA not found. Generate CA first.[/red]")
        input("\nPress Enter to continue...")
        return
        
    name = questionary.text("Client Name (CN):", style=custom_style).ask()
    if not name:
        return

    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import datetime

        # Load CA
        with open(ca_key_path, "rb") as f:
            ca_key = serialization.load_pem_private_key(f.read(), password=None)
        with open(ca_cert_path, "rb") as f:
            ca_cert = x509.load_pem_x509_certificate(f.read())

        # Generate Client Key
        client_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        
        # Create CSR
        csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, name),
        ])).sign(client_key, hashes.SHA256())
        
        # Sign Certificate
        cert = x509.CertificateBuilder().subject_name(
            csr.subject
        ).issuer_name(
            ca_cert.subject
        ).public_key(
            csr.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=365)
        ).sign(ca_key, hashes.SHA256())

        # Save
        base_name = name.replace(" ", "_").lower()
        with open(certs_dir / f"{base_name}_key.pem", "wb") as f:
            f.write(client_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
            
        with open(certs_dir / f"{base_name}_cert.pem", "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        console.print(f"[green]✓ Certificate for {name} generated![/green]")
        input("\nPress Enter to continue...")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        input("\nPress Enter to continue...")


def _view_cert_details(certs_dir: Path):
    """View details of a certificate"""
    certs = list(certs_dir.glob("*.pem"))
    if not certs:
        return
        
    choice = questionary.select(
        "Select certificate:",
        choices=[c.name for c in certs] + ['← Back'],
        style=custom_style
    ).ask()
    
    if not choice or choice == '← Back':
        return
        
    cert_path = certs_dir / choice
    try:
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        
        with open(cert_path, "rb") as f:
            cert_data = f.read()
            
        # Try loading as Cert
        try:
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            console.print(Panel(f"[bold]Subject:[/bold] {cert.subject}\n[bold]Issuer:[/bold] {cert.issuer}\n[bold]Serial:[/bold] {cert.serial_number}\n[bold]Valid Until:[/bold] {cert.not_valid_after}", title="Certificate Details"))
        except:
             console.print("[dim]Not a displayable certificate (maybe a key).[/dim]")
             
    except Exception as e:
        console.print(f"[red]Error reading cert: {e}[/red]")
    
    input("\nPress Enter to continue...")


def view_logs():
    """View System Logs"""
    show_header()
    
    log_dir = SystemManager.get_log_dir()
    if not log_dir.exists():
        console.print(f"[yellow]Log directory not found: {log_dir}[/yellow]")
        input("\nPress Enter to continue...")
        return

    logs = list(log_dir.glob("*.log"))
    if not logs:
        console.print("[dim]No log files found.[/dim]")
        input("\nPress Enter to continue...")
        return
        
    log_file = questionary.select(
        "Select log file to view:",
        choices=[l.name for l in logs] + ['← Back'],
        style=custom_style
    ).ask()
    
    if not log_file or log_file == '← Back':
        return
        
    path = log_dir / log_file
    
    try:
        # Read last 50 lines
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
             lines = f.readlines()
             last_lines = lines[-50:]
        
        console.clear()
        console.print(Panel("".join(last_lines), title=f"Log Viewer: {log_file} (Last 50 lines)", border_style="blue"))
    except Exception as e:
        console.print(f"[red]Error reading log: {e}[/red]")
        
    input("\nPress Enter to continue...")


def toggle_debug():
    """Toggle Debug Mode"""
    import json
    
    config_dir = SystemManager.get_config_dir()
    config_file = config_dir / "roxx_config.json"
    
    config = {}
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
        except:
            pass
            
    current_debug = config.get('debug', False)
    new_debug = not current_debug
    
    config['debug'] = new_debug
    
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
            
        status = "[green]ENABLED[/green]" if new_debug else "[red]DISABLED[/red]"
        console.print(f"\nDebug mode is now {status}")
        
    except Exception as e:
        console.print(f"\n[red]Error saving config: {e}[/red]")
        
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
                '👮 Manage Admins',
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
        elif choice == '👮 Manage Admins':
            manage_admins()
        elif choice == '🔐 Local PKI':
            manage_pki()
        elif choice == '📝 View Logs':
            view_logs()
        elif choice == '🐛 Debug Mode':
            toggle_debug()
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

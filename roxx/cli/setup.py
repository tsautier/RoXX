"""
RoXX Setup Assistant - Multi-OS Interactive Configuration
Replacement for bin/setup (1157 lines Bash)
"""

import sys
import os
from pathlib import Path
from typing import Optional, Dict, List

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box
import questionary
from questionary import Style

from roxx.utils.system import SystemManager
from roxx.utils.i18n import translate as _, set_locale, get_locale
from roxx.core.services import ServiceManager

console = Console()
service_mgr = ServiceManager()

# Custom style
custom_style = Style([
    ('qmark', 'fg:#673ab7 bold'),
    ('question', 'bold'),
    ('answer', 'fg:#f44336 bold'),
    ('pointer', 'fg:#673ab7 bold'),
    ('highlighted', 'fg:#673ab7 bold'),
])


class SetupAssistant:
    """RoXX Setup Assistant - Interactive configuration wizard"""
    
    def __init__(self):
        self.config_dir = SystemManager.get_config_dir()
        self.data_dir = SystemManager.get_data_dir()
        self.config = {}
    def show_welcome(self):
        """Display welcome screen"""
        console.clear()
        
        welcome = Panel.fit(
            "[bold cyan]RoXX Setup Assistant[/bold cyan]\n"
            f"[dim]v1.0-beta - Multi-OS Configuration Wizard[/dim]\n\n"
            f"[yellow]OS:[/yellow] {self.os_type.title()}\n"
            f"[yellow]Config:[/yellow] {self.config_dir}",
            border_style="cyan",
            box=box.DOUBLE
        )
        console.print(welcome)
        console.print()
        
        console.print("[bold]This wizard will help you configure RoXX:[/bold]")
        console.print("  • Language selection")
        console.print("  • FreeRADIUS configuration")
        console.print("  • Authentication providers (inWebo, TOTP, EntraID)")
        console.print("  • PKI setup")
        console.print("  • Service configuration")
        console.print()
        
        if not questionary.confirm("Continue with setup?", style=custom_style).ask():
            console.print("\n[yellow]Setup cancelled.[/yellow]")
            sys.exit(0)
    
    def select_language(self):
        """Language selection"""
        console.print("\n[bold cyan]Step 1: Language Selection[/bold cyan]")
        
        lang = questionary.select(
            "Select your preferred language:",
            choices=[
                'EN - English',
                'FR - Français'
            ],
            style=custom_style
        ).ask()
        
        locale = lang.split(' - ')[0]
        set_locale(locale)
        self.config['locale'] = locale
        
        # Save locale
        locale_file = self.config_dir / 'locale'
        locale_file.parent.mkdir(parents=True, exist_ok=True)
        locale_file.write_text(locale)
        
        console.print(f"[green]✓[/green] Language set to: {lang}")
    
    def configure_freeradius(self):
        """FreeRADIUS configuration"""
        console.print("\n[bold cyan]Step 2: FreeRADIUS Configuration[/bold cyan]")
        
        # Check if FreeRADIUS is installed
        freeradius_paths = [
            Path('/etc/freeradius/3.0'),
            Path('/etc/freeradius'),
            Path('/usr/local/etc/raddb'),
        ]
        
        freeradius_dir = None
        for path in freeradius_paths:
            if path.exists():
                freeradius_dir = path
                break
        
        if not freeradius_dir:
            console.print("[yellow]⚠[/yellow] FreeRADIUS not found. Please install it first.")
            if questionary.confirm("Skip FreeRADIUS configuration?", style=custom_style).ask():
                return
        else:
            console.print(f"[green]✓[/green] FreeRADIUS found: {freeradius_dir}")
            self.config['freeradius_dir'] = str(freeradius_dir)
    
    def configure_auth_providers(self):
        """Configure authentication providers"""
        console.print("\n[bold cyan]Step 3: Authentication Providers[/bold cyan]")
        
        providers = questionary.checkbox(
            "Select authentication providers to configure:",
            choices=[
                'inWebo Push',
                'TOTP (Time-based OTP)',
                'EntraID / Azure AD',
                'Local Users'
            ],
            style=custom_style
        ).ask()
        
        self.config['auth_providers'] = providers
        
        # Configure each provider
        if 'inWebo Push' in providers:
            self._configure_inwebo()
        
        if 'TOTP (Time-based OTP)' in providers:
            self._configure_totp()
        
        if 'EntraID / Azure AD' in providers:
            self._configure_entraid()
        
        if 'Local Users' in providers:
            self._configure_local_users()
    
    def _configure_inwebo(self):
        """Configure inWebo"""
        console.print("\n[bold]inWebo Configuration[/bold]")
        
        service_id = questionary.text(
            "inWebo Service ID:",
            default="10408",
            style=custom_style
        ).ask()
        
        cert_path = questionary.text(
            "Certificate path (.pem):",
            default=str(self.config_dir / "certs" / "iw_cert.pem"),
            style=custom_style
        ).ask()
        
        key_path = questionary.text(
            "Private key path (.pem):",
            default=str(self.config_dir / "certs" / "iw_key.pem"),
            style=custom_style
        ).ask()
        
        self.config['inwebo'] = {
            'service_id': service_id,
            'cert_path': cert_path,
            'key_path': key_path
        }
        
        console.print("[green]✓[/green] inWebo configured")
    
    def _configure_totp(self):
        """Configure TOTP"""
        console.print("\n[bold]TOTP Configuration[/bold]")
        
        secrets_file = questionary.text(
            "TOTP secrets file path:",
            default=str(self.config_dir / "totp_secrets.txt"),
            style=custom_style
        ).ask()
        
        self.config['totp'] = {
            'secrets_file': secrets_file
        }
        
        # Create empty secrets file if it doesn't exist
        secrets_path = Path(secrets_file)
        if not secrets_path.exists():
            secrets_path.parent.mkdir(parents=True, exist_ok=True)
            secrets_path.write_text("# TOTP Secrets\n# Format: username:secret_base32\n")
            console.print(f"[green]✓[/green] Created secrets file: {secrets_file}")
        
        console.print("[green]✓[/green] TOTP configured")
    
    def _configure_entraid(self):
        """Configure EntraID"""
        console.print("\n[bold]EntraID / Azure AD Configuration[/bold]")
        
        tenant_id = questionary.text(
            "Azure Tenant ID:",
            style=custom_style
        ).ask()
        
        client_id = questionary.text(
            "Application (Client) ID:",
            style=custom_style
        ).ask()
        
        domain = questionary.text(
            "Domain (e.g., company.onmicrosoft.com):",
            style=custom_style
        ).ask()
        
        self.config['entraid'] = {
            'tenant_id': tenant_id,
            'client_id': client_id,
            'domain': domain
        }
        
        console.print("[green]✓[/green] EntraID configured")
    
    def _configure_local_users(self):
        """Configure local users"""
        console.print("\n[bold]Local Users Configuration[/bold]")
        
        users_file = questionary.text(
            "Users file path:",
            default=str(self.config_dir / "users.roxx"),
            style=custom_style
        ).ask()
        
        self.config['local_users'] = {
            'users_file': users_file
        }
        
        # Create empty users file if it doesn't exist
        users_path = Path(users_file)
        if not users_path.exists():
            users_path.parent.mkdir(parents=True, exist_ok=True)
            users_path.write_text("# RoXX Local Users\n# Format: username Cleartext-Password := \"password\"\n")
            console.print(f"[green]✓[/green] Created users file: {users_file}")
        
        console.print("[green]✓[/green] Local users configured")
    
    def configure_pki(self):
        """PKI configuration"""
        console.print("\n[bold cyan]Step 4: PKI Configuration[/bold cyan]")
        
        pki_type = questionary.select(
            "Select PKI type:",
            choices=[
                'Local CA (self-signed)',
                'External CA (import certificates)',
                'Skip PKI configuration'
            ],
            style=custom_style
        ).ask()
        
        if pki_type == 'Skip PKI configuration':
            return
        
        self.config['pki_type'] = pki_type
        
        if pki_type == 'Local CA (self-signed)':
            self._setup_local_ca()
        elif pki_type == 'External CA (import certificates)':
            self._import_external_certs()
    
    def _setup_local_ca(self):
        """Setup local CA"""
        console.print("\n[bold]Local CA Setup[/bold]")
        
        ca_dir = self.config_dir / "certs"
        ca_dir.mkdir(parents=True, exist_ok=True)
        
        console.print("[yellow]ℹ[/yellow] This will create a self-signed CA for testing.")
        console.print("[yellow]⚠[/yellow] Not recommended for production!")
        
        if not questionary.confirm("Create local CA?", style=custom_style).ask():
            return
        
        # Get CA details
        country = questionary.text("Country Code (2 letters):", default="US", style=custom_style).ask()
        org = questionary.text("Organization:", default="RoXX", style=custom_style).ask()
        cn = questionary.text("Common Name:", default="RoXX CA", style=custom_style).ask()
        
        console.print("\n[yellow]Creating CA...[/yellow]")
        
        # Use cryptography library to create CA
        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization
            import datetime
            
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            
            # Create certificate
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, country),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, org),
                x509.NameAttribute(NameOID.COMMON_NAME, cn),
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
                x509.BasicConstraints(ca=True, path_length=None),
                critical=True,
            ).sign(private_key, hashes.SHA256())
            
            # Save certificate and key
            cert_file = ca_dir / "ca_cert.pem"
            key_file = ca_dir / "ca_key.pem"
            
            with open(cert_file, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
            
            with open(key_file, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            # Set permissions (Unix only)
            os.chmod(key_file, 0o600)
            
            console.print(f"[green]✓[/green] CA certificate: {cert_file}")
            console.print(f"[green]✓[/green] CA private key: {key_file}")
            
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to create CA: {e}")
    
    def _import_external_certs(self):
        """Import external certificates"""
        console.print("\n[bold]Import External Certificates[/bold]")
        
        cert_file = questionary.text(
            "Path to certificate file (.pem):",
            style=custom_style
        ).ask()
        
        key_file = questionary.text(
            "Path to private key file (.pem):",
            style=custom_style
        ).ask()
        
        # TODO: Copy files to config directory
        console.print("[yellow]ℹ[/yellow] Certificate import functionality coming soon.")
    
    def save_configuration(self):
        """Save configuration to file"""
        console.print("\n[bold cyan]Step 5: Saving Configuration[/bold cyan]")
        
        import json
        
        config_file = self.config_dir / "roxx_config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
        
        console.print(f"[green]✓[/green] Configuration saved: {config_file}")
    
    def show_summary(self):
        """Show configuration summary"""
        console.print("\n" + "=" * 60)
        console.print("[bold green]Setup Complete![/bold green]")
        console.print("=" * 60)
        
        console.print("\n[bold]Configuration Summary:[/bold]")
        console.print(f"  • Language: {self.config.get('locale', 'EN')}")
        console.print(f"  • Auth Providers: {', '.join(self.config.get('auth_providers', []))}")
        console.print(f"  • PKI Type: {self.config.get('pki_type', 'Not configured')}")
        console.print(f"  • Config Directory: {self.config_dir}")
        
        console.print("\n[bold]Next Steps:[/bold]")
        console.print("  1. Review configuration files")
        console.print("  2. Configure FreeRADIUS to use RoXX modules")
        console.print("  3. Test authentication")
        console.print("  4. Start services")
        
        console.print("\n[bold]Useful Commands:[/bold]")
        console.print("  • Launch console: [cyan]python -m roxx[/cyan]")
        console.print("  • Run tests: [cyan]pytest[/cyan]")
        console.print("  • View docs: [cyan]README.md[/cyan]")
        
        console.print()
    
    def run(self):
        """Run the setup wizard"""
        try:
            self.show_welcome()
            self.select_language()
            self.configure_freeradius()
            self.configure_auth_providers()
            self.configure_pki()
            self.save_configuration()
            self.show_summary()
            
        except KeyboardInterrupt:
            console.print("\n\n[yellow]Setup cancelled by user.[/yellow]")
            sys.exit(1)
        except Exception as e:
            console.print(f"\n[red]✗ Error:[/red] {e}")
            sys.exit(1)


def main():
    """Main entry point"""
    # Check admin privileges
    if not SystemManager.is_admin():
        console.print("\n[bold red]⚠ Warning:[/bold red] This program requires administrator privileges.")
        console.print("  • sudo python -m roxx.cli.setup", style="cyan")
        
        sys.exit(1)
    
    # Run setup
    assistant = SetupAssistant()
    assistant.run()


if __name__ == "__main__":
    main()

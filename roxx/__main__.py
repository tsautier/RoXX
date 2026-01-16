"""
RoXX Main Entry Point
Launches the admin console by default
"""

import sys


def main():
    """Main entry point for roxx command"""
    from roxx.cli.console import main as console_main
    
    try:
        # By default, launch the console
        console_main()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()

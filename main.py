#!/usr/bin/env python3
"""
x2telegram main entry point.

This script provides a command-line interface to the x2telegram application.
"""
import sys
import argparse
import logging
from datetime import datetime

from x2telegram.core import TweetProcessor
from x2telegram.db import Database
from x2telegram.utils import log_info, log_error
from x2telegram.config import DATABASE_PATH, OLLAMA_URL, OLLAMA_MODEL, AI_PROVIDER, NITTER_MIRRORS

def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )


def run_health_check():
    """Check connectivity to all external services."""
    import requests
    
    print("\n" + "=" * 50)
    print("x2telegram Health Check")
    print("=" * 50 + "\n")
    
    all_ok = True
    
    # Check Telegram Bot
    print("[Telegram Bot]")
    try:
        from x2telegram.services.telegram import TelegramService
        telegram = TelegramService()
        bot_info = telegram.get_bot_info()
        if bot_info:
            print(f"  ✓ Connected as @{bot_info.get('username', 'unknown')}")
        else:
            print("  ✗ Failed to connect (check TELEGRAM_BOT_TOKEN)")
            all_ok = False
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        all_ok = False
    
    # Check AI Provider
    print(f"\n[AI Provider: {AI_PROVIDER}]")
    if AI_PROVIDER.lower() == 'ollama':
        try:
            response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                if any(OLLAMA_MODEL in name for name in model_names):
                    print(f"  ✓ Ollama running at {OLLAMA_URL}")
                    print(f"  ✓ Model '{OLLAMA_MODEL}' available")
                else:
                    print(f"  ✓ Ollama running at {OLLAMA_URL}")
                    print(f"  ✗ Model '{OLLAMA_MODEL}' not found. Available: {', '.join(model_names[:5])}")
                    all_ok = False
            else:
                print(f"  ✗ Ollama returned status {response.status_code}")
                all_ok = False
        except requests.ConnectionError:
            print(f"  ✗ Cannot connect to Ollama at {OLLAMA_URL}")
            all_ok = False
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            all_ok = False
    elif AI_PROVIDER.lower() == 'claude':
        from x2telegram.config import CLAUDE_API_KEY
        if CLAUDE_API_KEY and CLAUDE_API_KEY != 'your-key':
            print("  ✓ Claude API key configured")
        else:
            print("  ✗ Claude API key not configured")
            all_ok = False
    
    # Check Nitter Mirrors
    print(f"\n[Nitter Mirrors] ({len(NITTER_MIRRORS)} configured)")
    working_mirrors = 0
    for mirror in NITTER_MIRRORS[:3]:  # Test first 3
        try:
            response = requests.get(mirror, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
            })
            if response.status_code == 200:
                print(f"  ✓ {mirror}")
                working_mirrors += 1
            else:
                print(f"  ✗ {mirror} (HTTP {response.status_code})")
        except Exception as e:
            print(f"  ✗ {mirror} ({str(e)[:30]})")
    
    if working_mirrors == 0:
        all_ok = False
    
    if len(NITTER_MIRRORS) > 3:
        print(f"  ... and {len(NITTER_MIRRORS) - 3} more mirrors")
    
    # Check Database
    print("\n[Database]")
    try:
        db = Database(DATABASE_PATH)
        if db.connect():
            followers = db.get_all_followers(enabled_only=False)
            print(f"  ✓ Connected to {DATABASE_PATH}")
            print(f"  ✓ {len(followers)} followers in database")
            db.close()
        else:
            print(f"  ✗ Cannot connect to database")
            all_ok = False
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        all_ok = False
    
    # Summary
    print("\n" + "=" * 50)
    if all_ok:
        print("✓ All services healthy!")
    else:
        print("✗ Some services have issues. Check above for details.")
    print("=" * 50 + "\n")
    
    return 0 if all_ok else 1

def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(description='Twitter/X to Telegram forwarding service')
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Command: run
    run_parser = subparsers.add_parser('run', help='Run the tweet processing job')
    
    # Command: add-follower
    add_parser = subparsers.add_parser('add-follower', help='Add a Twitter/X user to follow')
    add_parser.add_argument('username', help='Twitter/X username to follow')
    
    # Command: remove-follower
    remove_parser = subparsers.add_parser('remove-follower', help='Remove a followed Twitter/X user')
    remove_parser.add_argument('username', help='Twitter/X username to remove')
    
    # Command: list-followers
    list_parser = subparsers.add_parser('list-followers', help='List all followed Twitter/X users')
    list_parser.add_argument('--all', action='store_true', help='Include disabled followers')
    
    # Command: enable-follower
    enable_parser = subparsers.add_parser('enable-follower', help='Enable a followed Twitter/X user')
    enable_parser.add_argument('username', help='Twitter/X username to enable')
    
    # Command: disable-follower
    disable_parser = subparsers.add_parser('disable-follower', help='Disable a followed Twitter/X user')
    disable_parser.add_argument('username', help='Twitter/X username to disable')
    
    # Command: maintenance
    maintenance_parser = subparsers.add_parser('maintenance', help='Run database maintenance tasks')
    
    # Command: health-check
    health_parser = subparsers.add_parser('health-check', help='Check connectivity to external services')
    
    # Parse the arguments
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    # Default command if none specified
    if not args.command:
        parser.print_help()
        return 1
    
    # Create a database connection
    db = Database(DATABASE_PATH)
    if not db.connect():
        log_error("Failed to connect to database. Exiting.")
        return 1
    
    try:
        # Initialize database tables if needed
        db.create_tables()
        
        # Process the command
        if args.command == 'run':
            log_info("Starting tweet processing job")
            processor = TweetProcessor(DATABASE_PATH)
            success = processor.run()
            return 0 if success else 1
            
        elif args.command == 'add-follower':
            log_info(f"Adding follower: @{args.username}")
            follower = db.add_follower(args.username)
            if follower:
                print(f"Added follower: @{args.username} (ID: {follower.id})")
                return 0
            else:
                return 1
                
        elif args.command == 'remove-follower':
            log_info(f"Removing follower: @{args.username}")
            if db.remove_follower(args.username):
                print(f"Removed follower: @{args.username}")
                return 0
            else:
                return 1
                
        elif args.command == 'list-followers':
            enabled_only = not args.all
            followers = db.get_all_followers(enabled_only=enabled_only)
            
            if followers:
                print(f"{'ID':<6} {'Username':<20} {'Status':<10}")
                print("-" * 36)
                for follower in followers:
                    status = "Enabled" if follower.enabled else "Disabled"
                    print(f"{follower.id:<6} {'@' + follower.username:<20} {status:<10}")
            else:
                print("No followers found.")
            return 0
            
        elif args.command == 'enable-follower':
            log_info(f"Enabling follower: @{args.username}")
            if db.enable_follower(args.username, True):
                print(f"Enabled follower: @{args.username}")
                return 0
            else:
                return 1
                
        elif args.command == 'disable-follower':
            log_info(f"Disabling follower: @{args.username}")
            if db.enable_follower(args.username, False):
                print(f"Disabled follower: @{args.username}")
                return 0
            else:
                return 1
                
        elif args.command == 'maintenance':
            log_info("Running database maintenance")
            deleted = db.run_maintenance()
            print(f"Maintenance complete. Deleted {deleted} old tweets.")
            return 0
            
        elif args.command == 'health-check':
            return run_health_check()
            
    except Exception as e:
        log_error(f"Error: {str(e)}")
        return 1
        
    finally:
        # Close the database connection
        db.close()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

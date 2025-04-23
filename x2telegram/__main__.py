"""
Entry point module for x2telegram package.

Allows running the application using `python -m x2telegram`.
"""
from x2telegram.core.processor import TweetProcessor
from x2telegram.db.database import Database
from x2telegram.utils.helpers import log_info, log_error
from x2telegram.config.settings import DATABASE_PATH
import sys
import argparse
import logging
from datetime import datetime

def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )

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
    remove_parser = subparsers.add_parser('remove-follower', help='Remove a Twitter/X user from following')
    remove_parser.add_argument('username', help='Twitter/X username to unfollow')
    
    # Command: list-followers
    list_parser = subparsers.add_parser('list-followers', help='List all Twitter/X users being followed')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    if args.command is None:
        parser.print_help()
        return
    
    # Initialize database
    db = Database(DATABASE_PATH)
    
    try:
        if args.command == 'run':
            log_info(f"Starting tweet processing job at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            processor = TweetProcessor(db)
            processor.process_all_tweets()
            
        elif args.command == 'add-follower':
            db.add_follower(args.username)
            log_info(f"Added follower: {args.username}")
            
        elif args.command == 'remove-follower':
            db.remove_follower(args.username)
            log_info(f"Removed follower: {args.username}")
            
        elif args.command == 'list-followers':
            followers = db.get_followers()
            if followers:
                print("Current followers:")
                for follower in followers:
                    print(f" - {follower}")
            else:
                print("No followers configured.")
    except Exception as e:
        log_error(f"Error in command '{args.command}': {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
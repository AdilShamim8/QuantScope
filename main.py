"""
QuantScope Main Entry Point

This file is the starting point for the entire application.
It handles two modes:
  1. API Server Mode (--serve): Start FastAPI web server for the dashboard
  2. CLI Mode: Run analysis on command line with symbol list

Anyone using this app runs: python main.py --serve  or  python main.py --symbols AAPL MSFT
"""

import argparse
import sys
from config import settings


def main():
	"""
	Main entry point for QuantScope.
	
	What it does:
	  1. Parse command-line arguments (symbols, portfolio value, serve mode, etc.)
	  2. Validate configuration settings
	  3. Either start the web server OR run CLI analysis
	  4. Handle errors gracefully
	  
	Returns: None (exits with status code 0 on success, 1 on error)
	"""
	# STEP 1: Set up command-line argument parser
	# This defines what options a user can pass when running the script
	p = argparse.ArgumentParser(description="QuantScope")
	p.add_argument("--symbols", nargs="+", default=None)
	p.add_argument("--portfolio", type=float, default=10000.0)
	p.add_argument("--serve", action="store_true")
	p.add_argument("--host", default=settings.API_HOST)
	p.add_argument("--port", type=int, default=settings.API_PORT)
	args = p.parse_args()

	# STEP 2: Initialize logging and validate all configuration
	# This ensures settings are correct before running analysis or server
	settings.setup_logging()
	settings.validate()

	# STEP 3: Check if user wants to start the web server (--serve flag)
	# If yes, start FastAPI server and serve the dashboard
	# The server handles all web requests and API calls
	if args.serve:
		# Start the web server with FastAPI
		# This imports the app and runs it on the specified host:port
		import uvicorn
		from api.app import app
		uvicorn.run(app, host=args.host, port=args.port, workers=1)
		return

	# STEP 4: If not serving web, run CLI mode (command-line analysis)
	# Set default stock symbols if user didn't provide any
	default = ["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN", "META", "TSLA"]
	syms = args.symbols or default

	# STEP 5: Clean and validate the stock symbols
	# This removes duplicates and rejects invalid ticker formats
	from core.validator import clean_symbols
	ok, bad = clean_symbols(syms)
	if bad:
		print("Rejected: {}".format(bad))

	# STEP 6: Create and run the analysis pipeline
	# The pipeline fetches market data, calculates indicators, and generates insights
	from pipeline import Pipeline
	pipe = Pipeline(ok, args.portfolio)
	try:
		results = pipe.run()
		print(pipe.portfolio_summary)
		sys.exit(0 if results else 1)
	except KeyboardInterrupt:
		# User pressed Ctrl+C to stop the analysis
		sys.exit(130)
	except Exception as e:
		# Print any unexpected errors to the console
		print("Error: {}".format(e), file=sys.stderr)
		sys.exit(1)

# Only run main() if this file is executed directly (not imported as a module)
# This is the standard Python pattern for entry points
if __name__ == "__main__":
	main()
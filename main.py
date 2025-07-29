
# main.py

#Imports the argparse library for command-line argument parsing.
import argparse
import sys
#Imports the main simulation functions from sim_engine.py.
from sim_engine import run_week_simulation, run_season_simulation
#Imports HTML export and index page generation functions.
from html_generator import generate_index_page
from config import ENVIRONMENT, EXPORT_TEST_WEEK_FILE, EXPORT_FULL_SEASON_FILE

def main():
    #Creates an argument parser for CLI options.
    parser = argparse.ArgumentParser(description="Run WR Fantasy Projection Simulation")
    #Adds a CLI argument for simulation mode (week/test or full season).
    parser.add_argument("--mode", choices=["test", "season"], default="season", help="Which mode to run: 'test' or 'season'")
    #Adds a CLI argument for selecting the NFL week (used for single week mode).
    parser.add_argument("--week", type=int, default=1, help="Week number to test (only used if mode is 'test')")
    #Adds a CLI argument for an optional custom output filename.
    parser.add_argument("--output", type=str, default=None, help="Optional override output file name")
    parser.add_argument("--no-html", action="store_true", help="Skip HTML report generation")

    #Parses the command-line arguments and stores them in args.
    args = parser.parse_args()

    print(f"\n🌐 Environment: {ENVIRONMENT}")

    #Chooses between week-only or full-season sim based on CLI input and runs the corresponding function.
    try:
        if args.mode == "test":
            if not (1 <= args.week <= 18):
                print("\n⚠️  Invalid week number. Must be between 1 and 18.")
                sys.exit(1)

            print(f"\n🔍 Running test projection for Week {args.week}")
            output_file = args.output or EXPORT_TEST_WEEK_FILE
            run_week_simulation(args.week, output_file)

        else:
            print("\n📅 Running full season projection...")
            output_file = args.output or EXPORT_FULL_SEASON_FILE
            run_season_simulation(output_file=output_file)

        if not args.no_html:
            print("\n📊 Generating HTML summary...")
            #Generates the HTML index page for weekly visualizations.
            generate_index_page()

        print(f"\n✅ Output saved to: {output_file}")

    except Exception as e:
        print(f"\n❌ Error running simulation: {e}")
        raise

if __name__ == "__main__":
    main()

# Copyright Australian Conservation Foundation. All rights reserved.
import argparse

import scrape_EPBC
import process_table

parser = argparse.ArgumentParser()
dir_help = 'base directory to store spreadsheet and downloaded PDF files.'
parser.add_argument(
    "base_dir", type=str, help=dir_help)
parser.add_argument(
    "-c", "--chromedriver-path", type=str, required=False, default=None,
    help='path to Chromedriver')
parser.add_argument(
    "-s", "--show-chrome", default=False, action='store_true', required=False,
    help='show Chrome window')
parser.add_argument(
    "-l", "--last-page", type=int, choices=range(1, 168),
    metavar="[1-167]", default=10, required=False,
    help='The page [1-167] of the EPBC website to stop scraping at')

args = parser.parse_args()
headless = not args.show_chrome

scrape_EPBC.scrape_website(
    args.base_dir, cd_path=args.chromedriver_path,
    headless=headless, end_page=args.last_page)

# Copyright Australian Conservation Foundation. All rights reserved.
# Developed by Ewan Short 2021
# eshort0401@gmail.com, https://github.com/eshort0401
import argparse
import os

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
parser.add_argument(
    "-u", "--update-pub-db", default=True, required=False,
    action='store_true',
    help='Download the latest versions of the ASIC and ACNC registers.')
parser.add_argument(
    "-e", "--excel-link", required=False, action='store_true',
    help='add a column of excel hyperlinks to each combined PDF')

args = parser.parse_args()
headless = not args.show_chrome

base_dir = args.base_dir
if (base_dir[-1] not in ['/', '\\']):
    base_dir += '/'

cd_path = args.chromedriver_path
if cd_path is None:
    if os.name == 'nt':
        cd_path = 'C:/bin/chromedriver'
    else:
        cd_path = '/usr/bin/chromedriver'

print('Scraping to page {}.'.format(args.last_page))
scrape_EPBC.scrape_website(
    base_dir, cd_path=args.chromedriver_path,
    headless=headless, end_page=args.last_page)

process_table.process_table(base_dir, update_public_db=args.update_pub_db)
process_table.add_comb_paths(base_dir, excel_links=args.excel_link)

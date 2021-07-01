# Copyright Australian Conservation Foundation. All rights reserved.
# Developed by Ewan Short 2021
# eshort0401@gmail.com, https://github.com/eshort0401

from selenium import webdriver
import time
import os
import glob
import pandas as pd
import re
import numpy as np
from rapidfuzz import fuzz, process, utils
import subprocess

from shell_tools import run_powershell_cmd, run_common_cmd


def process_table(base_dir, update_public_db=False):
    table = get_new_rows(base_dir)
    table = format_title(base_dir, table)
    if update_public_db:
        get_company_databases(base_dir)
    table = lookup_ASIC_data(base_dir, table)
    update_revised_table(base_dir, table)


def get_new_rows(base_dir):
    print('Determining new rows.')
    table = pd.read_csv(
        base_dir + 'EPBC_notices.csv', dtype=str).drop_duplicates()
    try:
        f_table = pd.read_csv(
            base_dir + 'EPBC_database.csv', dtype=str)
    except:
        f_table = table.iloc[0:0]
    table = table.reset_index(drop=True)
    f_table = f_table.reset_index(drop=True)

    table['Title of referral'] = table['Title of referral'].apply(
        lambda x: re.sub(r'([0-9])\/([0-9])', r'\g<1>-\g<2>', x))

    label_list = [
        'Reference Number', 'Title of referral', 'Notification from EPBC Act',
        'Date of notice']
    shared = pd.merge(
        table, f_table[label_list].drop_duplicates(),
        how='left', indicator='Exist')
    shared['Exist'] = np.where(shared.Exist == 'both', True, False)
    exist = shared['Exist']
    table = table[np.logical_not(exist)]
    print('{} new entries to process.'.format(len(table)))
    return table


def format_title(base_dir, table):
    print('Formatting title.')
    num_slash = table['Title of referral'].apply(lambda x: x.count('/'))

    table['Title of referral'] = table['Title of referral'].apply(
        lambda x: re.sub(r'([0-9])\/([0-9])', r'\g<1>-\g<2>', x))

    fields = [
        'Approval Holder', 'Industry', 'Holder Address',
        'State', 'Description']
    for i in range(len(fields)):
        table[fields[i]] = ''
        table[fields[i]].loc[num_slash == 4] = table['Title of referral'].loc[
            num_slash == 4].apply(lambda x: x.split('/')[i])
        bad_title = 'Improperly formatted Title of referral - '
        bad_title += 'input this field manually.'
        table[fields[i]].loc[num_slash != 4] = bad_title

    return table


def get_company_databases(base_dir, cd_path=None):

    print('Downloading public company registers. Please wait.')
    run_common_cmd('rm {}ASIC_register.csv'.format(base_dir), base_dir)
    run_common_cmd('rm {}ACNC_register.xlsx'.format(base_dir), base_dir)

    if cd_path is None:
        if os.name == 'nt':
            cd_path = 'C:/bin/chromedriver'
        else:
            cd_path = '/usr/bin/chromedriver'

    url = 'https://data.gov.au/data/dataset/'
    url += '7b8656f9-606d-4337-af29-66b89b2eeefb/resource/'
    url += 'cb7e4eb5-ed46-4c6c-97a0-4532f4479b7d/download/company_202106.zip'

    if os.name == 'nt':

        options = webdriver.ChromeOptions()

        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--incognito')
        options.add_argument("--start-maximized")

        base_dir_sys = base_dir.replace('/', '\\')

        options.add_experimental_option(
            "prefs", {
                "plugins.plugins_list": [{"enabled": False,
                                          "name": "Chrome PDF Viewer"}],
                "download.default_directory": base_dir_sys,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True,
                "plugins.always_open_pdf_externally": True,
                "profile.default_content_setting_values.automatic_downloads": 1})

        driver = webdriver.Chrome(cd_path, options=options)
        driver.get(url)
        time.sleep(15)
    else:
        shell_cmd = 'wget -P {} {}'.format(base_dir, url)
        subprocess.run(
            shell_cmd, shell=True, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)

    if os.name == 'nt':
        shell_cmd = 'expand-archive {}company_*.zip {}'.format(
            base_dir, base_dir)
        run_powershell_cmd(shell_cmd, base_dir)
        time.sleep(10)
        csv_path = glob.glob(base_dir + 'COMPANY_*.csv')[0]
        shell_cmd = 'ren ' + csv_path + ' ASIC_register.csv'
        run_powershell_cmd(shell_cmd, base_dir)
    else:
        subprocess.run(
            'unzip {}company_*.zip -d {}'.format(base_dir, base_dir),
            shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(
            'mv {}COMPANY_*.csv {}ASIC_register.csv'.format(base_dir, base_dir),
            shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    run_common_cmd('rm {}company_*.zip'.format(base_dir), base_dir)

    url = 'https://data.gov.au/data/dataset/'
    url += 'b050b242-4487-4306-abf5-07ca073e5594/resource/'
    url += 'eb1e6be4-5b13-4feb-b28e-388bf7c26f93/download/datadotgov_main.xlsx'

    if os.name == 'nt':
        driver.get(url)
        time.sleep(5)
    else:
        shell_cmd = 'wget -P {} {}'.format(base_dir, url)
        subprocess.run(
            shell_cmd, shell=True, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)

    if os.name == 'nt':
        shell_cmd = 'ren {}'.format(base_dir)
        shell_cmd += 'datadotgov_main.xlsx ACNC_register.xlsx'
        run_powershell_cmd(shell_cmd, base_dir)
        driver.quit()
    else:
        shell_cmd = 'mv {}datadotgov_main.xlsx {}ACNC_register.xlsx'
        subprocess.run(
            shell_cmd.format(base_dir, base_dir), shell=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)



def lookup_ASIC_data(base_dir, table):
    ASIC_register = pd.read_csv(
        base_dir + 'ASIC_register.csv', sep='\t',
        encoding="ISO-8859-1", dtype=str)

    ASIC_register['Company Name'] = ASIC_register['Company Name'].apply(
        lambda x: re.sub(r'\s+$', '', x))
    ASIC_comp_name = ASIC_register['Company Name']
    ASIC_comp_name = ASIC_comp_name.apply(
        lambda x:
        x.lower().replace('proprietary', 'pty').replace('limited', 'ltd'))
    ASIC_comp_name = ASIC_comp_name.values

    holder_name = table['Approval Holder'].apply(
        lambda x:
        x.lower().replace('proprietary', 'pty').replace('limited', 'ltd'))
    holder_name = holder_name.values

    ASIC_types = {
        'APTY': 'Australian Proprietary Company',
        'APUB': 'Australian Public Company',
        'ASSN': 'Association',
        'BUSN': 'Business Name',
        'CHAR': 'Charity',
        'COMP': 'Community Purpose',
        'COOP': 'Co-Operative Society',
        'FNOS': 'Foreign Company (Overseas)',
        'LTDP': 'Limited Partnership',
        'MISM': 'Managed Investment Scheme',
        'NONC': 'Non Company',
        'NRET': 'Non Registered Entity',
        'RACN': 'Registered Australian Body',
        'REBD': 'Religious Body',
        'RSVN': 'Name Reservation',
        'SOLS': 'Solicitor Corporation',
        'TRST': 'Trust'}

    [com_type, ABN, ACN, ASIC_name] = [
        ['Fill manually.' for j in range(len(table))] for i in range(4)]

    print('Preprocessing text match tokens. Please wait.')
    processed_holder_names = [
        utils.default_process(holder) for holder in holder_name]
    processed_companies = [
        utils.default_process(company) for company in ASIC_comp_name]

    print('Performing fuzzy text match on ASIC database. Please wait')
    for (i, processed_query) in enumerate(processed_holder_names):
        ratio = process.extractOne(
            processed_query,
            processed_companies,
            scorer=fuzz.token_sort_ratio,
            processor=None,
            score_cutoff=90)
        if ratio:
            if ratio[1] >= 95:
                com_type[i] = ASIC_types[
                    ASIC_register['Type'].values[ratio[2]]]
                [ASIC_name[i], ABN[i], ACN[i]] = [
                    ASIC_register[col].values[ratio[2]]
                    for col in ['Company Name', 'ABN', 'ACN']]
            elif ratio[1] >= 90:
                com_type[i] = ASIC_types[
                    ASIC_register['Type'].values[ratio[2]]]
                [ASIC_name[i], ABN[i], ACN[i]] = [
                    ASIC_register[col].values[ratio[2]]
                    for col in ['Company Name', 'ABN', 'ACN']]
                [com_type[i], ASIC_name[i], ABN[i], ACN[i]] = [
                    col + ' (Confirm manually.)'
                    for col in [com_type[i], ASIC_name[i], ABN[i], ACN[i]]]

    table.insert(7, 'Registered Name', ASIC_name)
    table.insert(8, 'Type', com_type)
    table.insert(9, 'ABN', ABN)
    table.insert(10, 'ACN', ACN)
    table.ABN.loc[table['ABN'] == '0'] = 'Not Applicable'

    return table


def add_comb_paths(base_dir, excel_links=False, files_dir=None):
    print('Adding paths to combined PDF files.')
    table = pd.read_csv(base_dir + 'EPBC_database.csv', dtype=str)
    folder_names = table['Download Folder'].values
    if files_dir is None:
        files_dir = base_dir
    comb_file_paths = files_dir + 'files/' + folder_names
    comb_file_paths += '/' + folder_names + '_combined.pdf'
    cond = (table['Download Folder'].values == 'Not Applicable')
    comb_file_paths[cond] = 'Not Applicable'
    table['Combined PDF Path'] = comb_file_paths

    if excel_links:
        excel_links = '=HYPERLINK("file:' + comb_file_paths + '", '
        excel_links += '"Link to File")'
        excel_links[cond] = 'Not Applicable'
        table['Excel Link'] = excel_links
    table.to_csv(base_dir + 'EPBC_database_links.csv', index=False)

    return table


def update_revised_table(base_dir, table):
    try:
        f_table = pd.read_csv(
            base_dir + 'EPBC_database.csv', dtype=str)
    except:
        f_table = table.iloc[0:0]
    table['Date of notice'] = pd.to_datetime(
        table['Date of notice'], dayfirst=True)
    f_table['Date of notice'] = pd.to_datetime(
        f_table['Date of notice'], dayfirst=True)
    f_table = f_table.append(table, ignore_index=True)
    f_table = f_table.sort_values(by='Date of notice', axis=0, ascending=False)
    f_table = f_table.reset_index(drop=True)
    f_table['Date of notice'] = f_table['Date of notice'].apply(
        lambda x: x.strftime('%d/%m/%Y'))
    f_table.to_csv(
        base_dir + 'EPBC_database.csv', index=False)

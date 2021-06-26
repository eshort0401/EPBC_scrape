# Copyright Australian Conservation Foundation. All rights reserved.
# Developed by Ewan Short 2021
# eshort0401@gmail.com, https://github.com/eshort0401

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
import time
import subprocess
import re
import os
import string

from shell_tools import run_powershell_cmd, run_common_cmd


def scrape_website(base_dir, cd_path=None, headless=True, end_page=50):

    if not base_dir:
        if os.name == 'nt':
            base_dir = 'C:/Users/{}'.format(os.getlogin())
            base_dir += '/Documents/EPBC_scrape/'
        else:
            base_dir = '/home/student.unimelb.edu.au/shorte1/Documents/'
            base_dir += 'EPBC_scrape/'
    if not cd_path:
        if os.name == 'nt':
            cd_path = 'C:/bin/chromedriver'
        else:
            cd_path = '/usr/bin/chromedriver'

    url = "http://epbcnotices.environment.gov.au/publicnoticesreferrals"
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--incognito')
    options.add_argument("--start-maximized")

    sub_dir = 'files'
    files_dir = base_dir + sub_dir
    if os.name == 'nt':
        files_dir_sys = files_dir.replace('/', '\\')
    else:
        files_dir_sys = files_dir

    options.add_experimental_option(
        "prefs", {
            "plugins.plugins_list": [{"enabled": False,
                                      "name": "Chrome PDF Viewer"}],
            "download.default_directory": files_dir_sys,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "plugins.always_open_pdf_externally": True,
            "profile.default_content_setting_values.automatic_downloads": 1})

    driver = webdriver.Chrome(cd_path, options=options)
    driver.get(url)
    time.sleep(4)

    run_common_cmd('mkdir ' + files_dir, base_dir)
    for i in range(1, end_page+1):

        loading = True
        attempts = 0
        while loading:
            if attempts > 30:
                raise RuntimeError('Could not load website')
            try:
                time.sleep(2)
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, features='lxml')
                table = pd.read_html(soup.prettify())[0]
                if len(table) == 30:
                    loading = False
            except:
                attempts += 1

        table = clean_columns(table)
        table['PDF Attachments'] = ['TBD']*30
        table['Non PDF Attachments'] = ['TBD']*30
        table['Download'] = ['TBD']*30
        table['Download Folder'] = ['TBD']*30
        table['PDFs Combined'] = ['TBD']*30

        table['Date of notice'] = pd.to_datetime(
            table['Date of notice'], dayfirst=True)
        table.drop(labels='Actions', axis=1, inplace=True)

        try:
            stored_table = pd.read_csv(base_dir + '/EPBC_notices.csv')
            stored_table['Date of notice'] = pd.to_datetime(
                stored_table['Date of notice'], dayfirst=True)
            label_list = [
                'PDF Attachments', 'Non PDF Attachments',
                'Download', 'Download Folder', 'PDFs Combined']
            shared = pd.merge(
                table.drop(labels=label_list, axis=1),
                stored_table.drop(labels=label_list, axis=1).drop_duplicates(),
                how='left', indicator='Exist')
            shared['Exist'] = np.where(shared.Exist == 'both', True, False)
            exist = shared['Exist']
            del shared
        except:
            stored_table = table.iloc[0:0]
            stored_table['Date of notice'] = pd.to_datetime(
                stored_table['Date of notice'], dayfirst=True)
            exist = [False]*30
            exist = pd.Series(exist, name='Exist')

        if np.any(~exist):
            scrape_page(
                driver, i, table, stored_table, exist, base_dir, files_dir)

        try:
            next_button = driver.find_elements_by_xpath(
                '//a[@href="#" and @data-page="' + str(i+1) + '"]'
            )[1]
            ActionChains(driver).move_to_element(next_button).perform()
            next_button.click()
        except:
            print('Quitting.')

        del table, stored_table

    driver.quit()


def clean_columns(table):
    name_dict = {}
    clean_str = '  . Activate to sort in descending order'
    for col in range(len(table.columns)):
        name_dict[table.columns[col]] = table.columns[col].replace(
            clean_str, '')
    return table.rename(name_dict, axis='columns')


def get_first_letter(string):
    words = string.split()
    letters = [word[0] for word in words]
    return''.join(letters)


def scrape_iframe_page(
        driver, files_dir, table, row_number, page_number,
        folder_name, num_files, file_names, file_links):

    table.at[row_number, 'PDF Attachments'] = 'Yes'
    num_files.append(len(file_links))

    table.at[row_number, 'Download Folder'] = folder_name
    run_common_cmd('rm ' + files_dir + '/folder_count.txt', files_dir)

    unique_file_links = []
    unique_file_links_html = []
    table.at[row_number, 'Non PDF Attachments'] = 'No'
    for k in range(len(file_links)):
        link_text = file_links[k].get_attribute('innerHTML')
        if re.search('.pdf', link_text, re.IGNORECASE):
            if link_text not in unique_file_links_html:
                unique_file_links.append(file_links[k])
                unique_file_links_html.append(
                    file_links[k].get_attribute('innerHTML'))
        else:
            print('Non pdf files found on page ' + str(page_number)
                  + ', row ' + str(row_number+1) + '. Check manually.')
            table.at[row_number, 'Non PDF Attachments'] = 'Yes'
    file_links = unique_file_links

    successful = False
    attempts = 0
    table.at[row_number, 'Download'] = 'Success'
    while not successful:
        if attempts > 0:
            print('Download on page ' + str(page_number)
                  + ', row ' + str(row_number+1)
                  + ' timed out too many times.')
            table.at[row_number, 'Download'] = 'Fail'
            break
        try:
            for j in range(len(file_links)):
                file_links[j].click()
                time.sleep(0.25)

            file_count = 0
            iterations = 0
            while file_count < len(file_links):
                if iterations > 480:
                    attempts += 1
                    raise RuntimeError('Download timed out.')
                time.sleep(1)
                if os.name == 'nt':
                    shell_cmd = 'gci -path {}/*.pdf | '.format(files_dir)
                    shell_cmd += 'measure-object -line | '
                    shell_cmd += 'select-object -expand Lines '
                    shell_cmd += '> {}/num_files.txt'.format(files_dir)
                    run_powershell_cmd(shell_cmd, files_dir)
                    file_count = int(
                        np.loadtxt(
                            files_dir + '/num_files.txt',
                            encoding='utf16'))
                else:
                    shell_cmd = 'find ' + files_dir + '/*.PDF '
                    shell_cmd += '''-maxdepth 1 -exec sh -c 'mv "$1" "${1%.PDF}.pdf"' _ {} \;'''
                    subprocess.run(
                        shell_cmd, shell=True, stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)
                    shell_cmd = 'find ' + files_dir + '/*.pdf '
                    shell_cmd += '-type f -print | wc -l > '
                    shell_cmd += files_dir + '/num_files.txt'
                    subprocess.run(
                        shell_cmd, shell=True, stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)
                    file_count = int(np.loadtxt(
                        files_dir + '/num_files.txt'))

                iterations += 1
                time.sleep(.5)
                print('Downloading files. Please Wait.')

            run_common_cmd('rm ' + files_dir + '/num_files.txt', files_dir)
            successful = True
            time.sleep(1)
        except:
            attempts += 1
            time.sleep(1)
            print('Download failed.')


def scrape_page(
        driver, page_number, table, stored_table,
        exist, base_dir, files_dir, update_mode=False):

    xpath = '//a[@class="btn btn-default btn-xs" '
    xpath += 'and @href="#" and @data-toggle="dropdown"]'
    details_buttons = driver.find_elements_by_xpath(xpath)

    xpath = '//a[@class="details-link launch-modal" '
    xpath += 'and @href="#" and @title="View Details"]'
    details_links = driver.find_elements_by_xpath(xpath)

    try:
        next_button = driver.find_elements_by_xpath(
            '//a[@href="#" and @data-page="' + str(page_number+1) + '"]')[1]
    except:
        print('Last page reached.')
        next_button = driver.find_elements_by_xpath(
            '//a[@href="#" and @data-page="' + str(page_number) + '"]')[0]

    for i in range(30):
        if exist[i]:
            continue
        print('Scraping page {}, row {}.'.format(page_number, i+1))
        run_common_cmd('rm ' + files_dir + '/*.pdf', base_dir)

        ref_num = table['Reference Number'].iloc[i].replace('/', '')
        date = table['Date of notice'].iloc[i].strftime('%d%m%Y')
        org = table['Title of referral'].iloc[i]
        org = org.split('/')[0]
        org = org.translate(str.maketrans('', '', string.punctuation))
        org = get_first_letter(org)
        ref_type = table['Notification from EPBC Act'].iloc[i]
        ref_type = ref_type.replace('/', ' ').replace('-', ' ')
        ref_type = ref_type.replace('  ', ' ')
        ref_type = ref_type.translate(
            str.maketrans('', '', string.punctuation))
        ref_type = get_first_letter(ref_type)

        folder_name = ref_num + '_' + date + '_' + org + '_' + ref_type
        folder_name = folder_name.lower()
        folder_path = files_dir + '/' + folder_name

        if i < 29:
            # Move to element i+1, as i may be blocked by Chrome download bar!
            ActionChains(driver).move_to_element(
                details_buttons[i+1]).perform()
            details_buttons[i].click()
            time.sleep(.5)
        else:
            # Move to navigation bar, as i may be blocked by download bar!
            ActionChains(driver).move_to_element(next_button).perform()
            details_buttons[i].click()
            time.sleep(.5)

        ActionChains(driver).move_to_element(details_links[i]).perform()
        details_links[i].click()
        time.sleep(1.5)

        iframe = driver.find_elements_by_xpath(
            '//section[@class="modal fade modal-form modal-form-details in"]'
            + '/div/div/div/iframe')
        driver.switch_to.frame(iframe[0])

        file_links = driver.find_elements_by_xpath(
            "//a[contains(@href, '/_entity/annotation/')]")

        [num_files, file_names] = [[], []]
        iframe_page_num = 1
        more_iframe_pages = True
        if not file_links:
            num_files.append(0)
            file_names.append('')
            table.at[i, 'PDF Attachments'] = 'No'
            table.at[i, 'Non PDF Attachments'] = 'No'
            table.at[i, 'Download'] = 'Not Applicable'
            table.at[i, 'Download Folder'] = 'Not Applicable'
            table.at[i, 'PDFs Combined'] = 'Not Applicable'
        else:
            while more_iframe_pages:
                scrape_iframe_page(
                    driver, files_dir, table, i, page_number, folder_name,
                    num_files, file_names, file_links)
                iframe_next_buttons = driver.find_elements_by_xpath(
                    '//a[@href="#" and @data-page="'
                    + str(iframe_page_num+1) + '"]')
                if len(iframe_next_buttons) > 1:
                    # ActionChains(driver).move_to_element(
                    #     iframe_next_buttons[0]).perform()
                    iframe_next_buttons[0].click()
                    time.sleep(1.5)
                    print('Multiple iframe pages.')
                    print('Downloading from next iframe page.')
                    file_links = driver.find_elements_by_xpath(
                        "//a[contains(@href, '/_entity/annotation/')]")
                    iframe_page_num += 1
                elif len(iframe_next_buttons) <= 1:
                    more_iframe_pages = False

            # After files downloaded, move them to appropriate folder
            run_common_cmd('mkdir ' + folder_path, base_dir)

            if os.name == 'nt':
                shell_cmd = 'move-item -path {}/*.pdf '.format(files_dir)
                shell_cmd += '-destination {}'.format(folder_path)
                run_powershell_cmd(shell_cmd, files_dir)

                shell_cmd = 'for %s in ({}/*.pdf) '.format(folder_path)
                shell_cmd += 'do ECHO "%s" '
                shell_cmd += '>> {}/filename.lst'.format(folder_path)
                subprocess.run(
                    shell_cmd.replace('/', '\\'), shell=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                print('Creating combined PDF file.')
                print('This may take a few minutes.')
                shell_cmd = 'gswin64c -dBATCH -dNOPAUSE -q -sDEVICE=pdfwrite '
                shell_cmd += '-sOutputFile=' + folder_path + '/' + folder_name
                shell_cmd += '_combined.pdf '
                shell_cmd += '@{}/filename.lst'.format(folder_path)
                try:
                    combined_code = subprocess.run(
                        shell_cmd.replace('/', '\\'), shell=True,
                        timeout=600).returncode
                except:
                    combined_code = 1
                if combined_code == 0:
                    table.at[i, 'PDFs Combined'] = 'Yes'
                else:
                    table.at[i, 'PDFs Combined'] = 'No'

            else:
                shell_cmd = 'mv ' + files_dir + '/*.pdf ' + folder_path
                subprocess.run(
                    shell_cmd, shell=True, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL)

                # Record the filenames
                shell_cmd = 'find ' + folder_path
                shell_cmd += '/*.pdf -maxdepth 1 -type f '
                shell_cmd += '-printf "%f\n" > '
                shell_cmd += folder_path + '/file_names.txt'
                subprocess.run(
                    shell_cmd, shell=True, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL)
                with open(folder_path + '/file_names.txt') as f:
                    lines = f.readlines()
                file_names.append(', '.join(lines).replace('\n', ''))
                subprocess.run(
                    'rm ' + folder_path + '/file_names.txt', shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL)

                print('Creating combined PDF file.')
                print('This may take a few minutes.')

                shell_cmd = 'gs -dBATCH -dNOPAUSE -q -sDEVICE=pdfwrite '
                shell_cmd += '-sOutputFile=' + folder_path
                shell_cmd += '/' + folder_name
                shell_cmd += '_combined.pdf ' + folder_path + '/*.pdf'

                try:
                    combined_code = subprocess.run(
                        shell_cmd, shell=True, timeout=600).returncode
                except:
                    combined_code = 1

                if combined_code == 0:
                    table.at[i, 'PDFs Combined'] = 'Yes'
                else:
                    table.at[i, 'PDFs Combined'] = 'No'

        driver.switch_to.default_content()
        xpath = '//section[@class="modal fade modal-form '
        xpath += 'modal-form-details in"]/div/div/div/button'
        close_button = driver.find_elements_by_xpath(xpath)
        close_button[0].click()
        time.sleep(.5)

        # Append the downloaded row to the stored table and save
        row = table.iloc[i]
        stored_table = stored_table.append(row, ignore_index=True)
        stored_table = stored_table.sort_values(
            by='Date of notice', axis=0,
            ascending=False)
        stored_table = stored_table.reset_index(drop=True)
        stored_table['Date of notice'] = stored_table['Date of notice'].apply(
            lambda x: x.strftime('%d/%m/%Y'))
        stored_table.to_csv(
            base_dir + '/EPBC_notices.csv', index=False, header=True)
        stored_table['Date of notice'] = pd.to_datetime(
            stored_table['Date of notice'], dayfirst=True)

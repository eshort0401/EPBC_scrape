import numpy as np # Handles maths
import pandas as pd # Good for tables of data
from selenium.webdriver.common.action_chains import ActionChains
import time
import subprocess
import re
import string

def scrape_iframe_page(
        driver, files_dir, table, row_number, page_number,
        folder_name, num_files, file_names, file_links):

    table.at[row_number, 'Attachments'] = 'Yes'
    num_files.append(len(file_links))

    table.at[row_number, 'Download Folder'] = folder_name
    subprocess.run('rm ' + files_dir + '/folder_count.txt', shell=True)
    # Remove duplicate links - otherwise download code below breaks
    # when the same file downloads and overwrites itself, resulting
    # in file_count == len(file_links) never being satisfied
    unique_file_links = []
    unique_file_links_html = []
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

            # Wait for files to download
            file_count = 0
            iterations = 0
            while file_count < len(file_links):
                if iterations > 240:
                    import pdb; pdb.set_trace()
                    attempts += 1
                    raise RuntimeError('Download timed out.')
                time.sleep(1)
                shell_cmd = '''find ''' + files_dir + '/*.PDF '
                shell_cmd += '''-maxdepth 1 -exec sh -c 'mv "$1" "${1%.PDF}.pdf"' _ {} \;'''
                subprocess.run(shell_cmd, shell=True)
                shell_cmd = 'find ' + files_dir + '/*.pdf '
                shell_cmd += '-type f -print | wc -l > '
                shell_cmd += files_dir + '/num_files.txt'
                subprocess.run(shell_cmd, shell=True)
                file_count = int(np.loadtxt(
                    files_dir + '/num_files.txt'))
                iterations += 1
                time.sleep(.5)
                print('Still Downloading. Please Wait.')
            subprocess.run('rm ' + files_dir + '/num_files.txt', shell=True)
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

    # Iterate over the 30 entries in the table on current page checking for files
    for i in range(30):
        if exist[i]:
            continue
        if i < 29:
            # Move to element i+1, as i may be blocked by Chrome download bar!
            ActionChains(driver).move_to_element(details_buttons[i+1]).perform()
            details_buttons[i].click()
            time.sleep(.5)
        else:
            # Move to navigation bar, as i may be blocked by Chrome download bar!
            ActionChains(driver).move_to_element(next_button).perform()
            details_buttons[i].click()
            time.sleep(.5)

        ActionChains(driver).move_to_element(details_links[i]).perform()
        details_links[i].click()
        time.sleep(1.5)

        iframe = driver.find_elements_by_xpath(
            '//section[@class="modal fade modal-form modal-form-details in"]'
            + '/div/div/div/iframe')

        # NOTE need to check if bash shells exist on windows 10.
        subprocess.run('rm ' + files_dir +'/*.pdf', shell=True)
        ref_num = table['Reference Number'].iloc[i].replace('/','')
        date = table['Date of notice'].iloc[i].strftime('%d%m%Y')
        org = table['Title of referral'].iloc[i].split('/')[0]
        org = org.translate(str.maketrans('', '', string.punctuation))
        org = org.replace(' ', '_')
        ref_type = table['Notification from EPBC Act'].iloc[i]
        ref_type = ref_type.translate(
            str.maketrans('', '', string.punctuation))
        ref_type = ref_type.replace(' ', '_')

        folder_name = ref_num + '_' + date + '_' + org + '_' + ref_type
        folder_name = folder_name.lower()
        folder_path = files_dir + '/' + folder_name

        driver.switch_to.frame(iframe[0])
        file_links = driver.find_elements_by_xpath(
            "//a[contains(@href, '/_entity/annotation/')]")
        if len(file_links) >= 17:
            import pdb; pdb.set_trace()
        [num_files, file_names] = [[], []]
        iframe_page_num = 0
        if not file_links:
            num_files.append(0)
            file_names.append('')
            table.at[i, 'Attachments'] = 'No'
            table.at[i, 'Download'] = 'NA'
            table.at[i, 'Download Folder'] = 'NA'
        else:
            scrape_iframe_page(
                driver, files_dir, table, i, page_number, folder_name,
                num_files, file_names, file_links)
            iframe_next_button = driver.find_elements_by_xpath(
                '//a[@href="#" and @data-page="'
                + str(iframe_page_num) + '"]')[0]



        # After files downloaded, move them to appropriate folder
        subprocess.run(['mkdir', folder_path])
        shell_cmd = 'mv ' + files_dir + '/*.pdf ' + folder_path
        subprocess.run(shell_cmd, shell=True)

        # Record the filenames
        shell_cmd = 'find ' + folder_path + '/*.pdf -maxdepth 1 -type f '
        shell_cmd += '-printf "%f\n" > ' + folder_path + '/file_names.txt'
        subprocess.run(shell_cmd, shell=True)
        with open(folder_path + '/file_names.txt') as f:
            lines = f.readlines()
        file_names.append(', '.join(lines).replace('\n',''))
        subprocess.run('rm ' + folder_path + '/file_names.txt', shell=True)

        shell_cmd = 'pdfunite ' + folder_path + '/*.pdf ' + folder_path
        shell_cmd += '/' + folder_name + '_combined.pdf'
        subprocess.run(shell_cmd, shell=True)

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
            by='Date of notice', axis = 0,
            ascending=False)
        stored_table = stored_table.reset_index(drop=True)
        stored_table['Date of notice'] = stored_table['Date of notice'].apply(
            lambda x: x.strftime('%d/%m/%Y'))
        stored_table.to_csv(
            base_dir + '/EPBC_notices_test.csv', index=False, header=True)
        stored_table['Date of notice'] = pd.to_datetime(
            stored_table['Date of notice'], dayfirst=True)

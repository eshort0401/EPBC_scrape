from selenium import webdriver
import time
import os
import glob

from shell_tools import run_powershell_cmd, run_common_cmd


def get_company_databases(base_dir, cd_path=None):

    if cd_path is None:
        if os.name == 'nt':
            cd_path = 'C:/bin/chromedriver'
        else:
            cd_path = '/usr/bin/chromedriver'

    url = 'https://data.gov.au/data/dataset/'
    url += '7b8656f9-606d-4337-af29-66b89b2eeefb/resource/'
    url += 'cb7e4eb5-ed46-4c6c-97a0-4532f4479b7d/download/company_202106.zip'

    options = webdriver.ChromeOptions()

    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--incognito')
    options.add_argument("--start-maximized")

    if os.name == 'nt':
        base_dir_sys = base_dir.replace('/', '\\')
    else:
        base_dir_sys = base_dir

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
    time.sleep(10)

    if os.name == 'nt':
        shell_cmd = 'expand-archive {}company_*.zip {}'.format(
            base_dir, base_dir)
        run_powershell_cmd(shell_cmd, base_dir)
        time.sleep(1)
        csv_path = glob.glob(base_dir + 'company_*.csv')[0]
        shell_cmd = 'ren ' + csv_path + ' ASIC_register.csv'
        run_powershell_cmd(shell_cmd, base_dir)

    run_common_cmd('rm {}company_*.zip'.format(base_dir), base_dir)

    url = 'https://data.gov.au/data/dataset/'
    url += 'b050b242-4487-4306-abf5-07ca073e5594/resource/'
    url += 'eb1e6be4-5b13-4feb-b28e-388bf7c26f93/download/datadotgov_main.xlsx'

    driver.get(url)
    time.sleep(5)

    if os.name == 'nt':
        shell_cmd = 'ren {}'.format(base_dir)
        shell_cmd += 'datadotgov_main.xlsx ACNC_register.xlsx'
        run_powershell_cmd(shell_cmd, base_dir)

    driver.quit()

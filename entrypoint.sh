#!/bin/bash --login
set -euo pipefail
conda activate epbc_docker
# Run scrape_EPBCscript. The final argument gives the last page to scrape to.
if test -r /EPBC_files/page_number.txt; then
    PAGE_NUM=$(cat /EPBC_files/page_number.txt)
else
    PAGE_NUM="1"
    echo "1" > /EPBC_files/page_number.txt
fi
python /EPBC_src/scrape_EPBC_script.py /EPBC_files/ -l $PAGE_NUM
# Set file permissions to read, write, execute for everyone.
chmod a=rwx /EPBC_files/ASIC_register.csv
chmod a=rwx /EPBC_files/ACNC_register.xlsx
chmod a=rwx /EPBC_files/EPBC_notices.csv
chmod a=rwx /EPBC_files/EPBC_database.csv
chmod a=rwx /EPBC_files/EPBC_database_links.csv
chmod a=rwx /EPBC_files/files
/bin/bash

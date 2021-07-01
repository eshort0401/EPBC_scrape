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

if test -r /EPBC_files/host_file_path.txt; then
    HOST_PATH=$(cat /EPBC_files/host_file_path.txt)
else
    HOST_PATH="/EPBC_files/"
    echo "/EPBC_files/" > /EPBC_files/host_file_path.txt
fi

python /EPBC_src/scrape_EPBC_script.py /EPBC_files/ -l $PAGE_NUM -e -f $HOST_PATH
# Set file permissions to read, write, execute for everyone.
chmod a=rwx /EPBC_files/ASIC_register.csv
chmod a=rwx /EPBC_files/ACNC_register.xlsx
chmod a=rwx /EPBC_files/EPBC_notices.csv
chmod a=rwx /EPBC_files/EPBC_database.csv
chmod a=rwx /EPBC_files/EPBC_database_links.csv
chmod a=rwx /EPBC_files/files
chmod a=rwx /EPBC_files/host_file_path.txt
chmod a=rwx /EPBC_files/page_number.txt

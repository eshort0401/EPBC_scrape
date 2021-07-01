Copyright Australian Conservation Foundation (ACF). All rights reserved.<br>
Concept by Kim Garratt, Annica Schoor and the ACF 2021.<br>
Software developed by Ewan Short 2021. <br>
<eshort0401@gmail.com>, <https://github.com/eshort0401> <br>

# Introduction
This repository contains python software for downloading and processing data
from the Australian Environment Protection and Biodiversity Conservation Act (EPBC)
[public notices website](http://epbcnotices.environment.gov.au/publicnoticesreferrals/).
The software does the following.
1. Download the tabulated data from the website and save it on local disk
as `EPBC_notices.csv`.
1. Download any PDF files attached to each public notice and organise them into folders on local disk.
Folder names are chosen by referral number, date, referral holder
and referral type.
1. Combine the PDFs associated with each referral into a single PDF.
1. Reformat the data in `EPBC_notices.csv`, and lookup relevant data from the
PDF files to create a comprehensive database `EPBC_database.csv`.
    1. Reformat the "Title of referral" field.
    1. Look up data on each referral holder from the ASIC company register, such as ABN.
1. Create a column in the database specifying the paths of the downloaded and combined PDF files,
and a column of clickable links to these files which work in Microsoft Excel or LibreOffice Calc.
The amended database is saved as `EPBC_database_links.csv`.

## Known Issues
1. When downloading the entire database at once, or scraping many pages at once,
the `scrape_EPBC_script.py` may occasionally hang as it attempts to download
files. When this happens, the script should automatically skip the frozen download, but occasionally
it will continue to hang. I suspect this may be because the EPBC website itself
has been updated while the script is running, and this is confusing chromedriver.
This can be fixed by simply stopping the script (e.g. `ctl + c`) and restarting it.
It should also be easy to simply hard code a restart of the script when it hangs,
but haven't had time to do this yet!
2. Sometimes downloading the ASIC company register from `data.gov.au` is very slow.
This is not an issue with the script, as it also occurs when using a browser: I assume it
is just that `data.gov.au` sometimes gets very high traffic, particularly at the start
of each month when a new register is released. Note the script uses the June 2021 register:
this can be changed by modifying the url specified in the `get_company_databases` function
defined in `process_table.py`.

# Docker Setup
`EPBC_scrape` may be run through [Docker](https://www.docker.com/). Docker is a convenient
tool for isolating the configuration needed to run a piece of software from the rest of your
system. Note that the running the `EPBC_scrape` code through Docker is currently only supported for
UNIX systems, as the Docker containers are themselves UNIX based. (In principle it
is possible to also run these containers from Docker on Windows using WSL2,
but this is not yet working.)

If not using Docker, skip to the Normal Setup section below.

## Installation
1. Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop).
2. Download or clone the `EPBC_scrape` repository.
3. Open the terminal and navigate to the repository directory  by typing

    ```
    cd <parent_dir>/EPBC_scrape
    ```

    where `<parent_dir>` is the full path to the directory containing the
    `EPBC_scrape` folder.
4. Type the following command into the terminal to build the Docker
image.

    ```
    docker build -t epbc:1.0 --build-arg USER_ID=$(id -u) --build-arg GROUP_ID=$(id -g) .
    ```

    1. Note that `$(id -u)` and `$(id -g)` will tell `EPBC_scrape` to  
    create new files using the current user's user and group ID numbers: these
    can be changed to other user ID numbers if required.
    1. By default, `EPBC_scrape`
    will give read, write and execute rights for created files to everyone.
    These permissions can be changed by altering the `chmod ...` lines in
    `entrypoint.sh`.
    1. The lines `RUN apt-get update` and `RUN apt update` are likely slowing down
    image build times, and making the image larger than it needs to be. These lines
    can probably be removed, or replaced with more efficient methods of ensuring
    the container has access to the UNIX repositories it needs.   
5. Perform a test run of the software by calling

    ```
    docker run -it --rm --mount "type=bind,src=<files_dir>,dst=/EPBC_files" epbc:1.0
    ```

    replacing `<files_dir>` with the full path to the location you wish to download
    the EPBC Website data to. This should download the first page of the EPBC website to the directory
    specified by `<files_dir>`.

## Operation
1. Ensure you have completed the installation steps above.
1. In the `<files_dir>` folder you specified during the test run above, you should see
a file named `page_number.txt`.
    1. If you open this file it should contain just the number
    "1". This is the page number of the EPBC website the scraper will stop checking for new entries.
    To scrape the first X pages of the EPBC website, where 1 < X <= 167, change this number to X then run the same
    `docker run ...` command given above.
    1. Example usage might be to first run the container to scrape the full database
    by setting the contents of `page_number.txt` to 167 and running `docker run ...`,
    then setting the contents of `page_number.txt` to 10 and running `docker run ...`
    periodically to just check the most recent pages of the EPBC website for new data.
1. In the `<files_dir>` folder you specified during the test run above, you
should see a file named `host_file_path.txt`.
    1. Open it, and you should see the text
    `/EPBC_files/`. This is the path used to create the path and link columns in the
    `EPBC_database_links.csv` table.
    1. The test run initialises this to
    `/EPBC_files/`, which is the location of the files in the
    UNIX Docker container.
    1. If you change this text to match `<files_dir>`, then the
    next time you run the container the paths and links in `EPBC_database_links.csv`
    should update to those on the host machine, not those of the container.   

# Normal Setup
EPBC_scrape can also be run without Docker, but additional dependencies must be
downloaded and installed.

## Supported Systems
- Unix systems (i.e. Linux and Mac).
- Windows 10. (Currently, operating system calls on Windows use the Windows Powershell,
which only ships by default with Windows 10. Future versions may support
older versions of Windows.)

## Installation
1. Click the green "Code" button above, then "Download ZIP". (Advanced users should use GIT.)
    1. Extract the ZIP file. You should end up with a folder called `EPBC_scrape`.
    On windows, the recommended location for this directory is
    `C:\Users\<username>\Documents\EPBC_scrape`, replacing `<username>` with your own Windows user name.
    1. If you have been provided with copies of the `files` directory,
    `EPBC_notices.csv` and `EPBC_database.csv` files, put them into the `EPBC_scrape` folder.
    This will save you having to download and process the database from scratch,
    which takes ~20 hours for the full database!  
1. Download the [miniconda](https://docs.conda.io/en/latest/miniconda.html) or
[Anaconda](https://www.anaconda.com/products/individual-b) installer.
    1. You most likely want the most recent, 64 bit version for your system.
    1. Run the installer. All the default installation settings are most likely fine.
    1. Anaconda/miniconda includes python itself, and makes it *much* easier to
  manage open source python packages.
1. Open the terminal (UNIX) or the Anaconda Powershell Prompt (Windows 10) and navigate
to the `EPBC_scrape` directory by typing `cd <base_dir>`, where `<base_dir>` is
the full path to the `EPBC_scrape` folder. Then type

    ```
    conda env create -f epbc.yml
    conda activate epbc
    jupyter contrib nbextension install --user
    ```

    This will download other necessary python packages, and put them into an
    conda environment called `epbc`. Environments make it possible to run
    different versions of python with different combinations of packages on the same system.
1. Download the latest version of Chrome for your system.
    1. Open Chrome, go to settings, and disable the “ask permission for download” option.
    1. Go to settings, privacy and security, additional permissions, and disable “ask for permission...”
    1. Disable auto-updates of Chrome (if possible).
1. Download [chromedriver](https://chromedriver.chromium.org/downloads). This is the Chrome API we used to run Chrome "hands-free".
    1. The base version numbers for Chrome and chromedriver need to match. For now,
    just download the latest versions of each.
    1. Extract the ZIP file, and save the resulting file into `C:/bin` (Windows 10)
    or `/usr/bin` (UNIX). On Windows, you may need to create the directory `C:/bin`
    if it doesn't already exist.
    1. On Windows, go to advanced settings in control panel, and add `C:/bin`
    to your `PATH` variable. You can also find this settings window by searching
    "env" in start search bar. This tells Windows where to find chromedriver.
    1. On UNIX systems, `/usr/bin` should already be in the `PATH` variable.
1. On Windows, download the [ghostscript](https://www.ghostscript.com/download/gsdnld.html) installer.
This is what combines the PDF files. Note ghostscript is included by default
on UNIX systems.    
    1. You most likely want the latest 64 bit version for your system.
    1. Run the ghostscript installer.
    1. On Windows, add the location of `gswin64c.exe` to the `PATH` environment variable as before. The
    default installation location is `C:\Program Files\gs\gs9.54.0\bin`.

# Operation
1. Open the terminal (UNIX) or Anaconda Powershell Prompt (Windows 10).
1. Activate the conda environment by typing

    ```
    conda activate epbc
    ```

    This tells the shell to use the python configuration defined above.
1. To update the `files` directory, `EPBC_notices.csv` and `EPBC_database.csv` files,
type

    ```
    python <base_dir>\scrape_EPBC_script.py <base_dir> -e
    ```

    where `<base_dir>` is the full path to the `EPBC_scrape` directory, i.e.
    the directory containing the python scripts, and current versions of the `files` directory,
    `EPBC_notices.csv` and `EPBC_database.csv` files (e.g.
    `C:\Users\kgarr\Documents\EPBC_scrape`.)
    1. This script will also create `EPBC_database_links.csv`, which includes
    additional columns containing the full
    paths to each combined PDF file, and a column of Excel hyperlinks which can
    be clicked on in Excel to open the files. The Excel hyperlink column can be omitted by
    dropping the `-e` option from the above.
    1. By default, this script will check the first 10 pages of the EPBC website for new
    public notices. You can specify a different final page by using the `-l`
    (long version `--last-page`) option. For example

        ```
        python <base_dir>\scrape_EPBC_script.py <base_dir> -l 100
        ```

        will check the first 100 pages for new notices. To download and process
        the entire database from scratch, call

        ```
        python <base_dir>\scrape_EPBC_script.py <base_dir> -l 167
        ```

        which should take ~20 hours on a modern system.

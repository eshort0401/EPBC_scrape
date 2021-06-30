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

# Installation

## Supported Systems
- Unix systems (i.e. Linux and Mac).
- Windows 10. (Currently, operating system calls on Windows use the Windows Powershell,
which only ships by default with Windows 10. Future versions will support
older versions of Windows.)

## Docker Setup
`EPBC_scrape` may be run through [Docker](https://www.docker.com/), a convenient
tool for isolating the configuration needed to run the software from the rest of your
system.
1. Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop)
for your system.
2. Download or clone the EPBC_scrape repository.
3. Open the terminal (UNIX) or Powershell (Windows) and navigate to the
repository directory  by typing

    ```
    cd <parent_dir>/EPBC_scrape
    ```

4. Type the following command into the terminal/Powershell to build the Docker
image.

    ```
    docker build -t epbc:1.0 --build-arg USER_ID=<user_id> --build-arg GROUP_ID=<group_id> .
    ```

    The full stop at the end of the command is essential. Replace `<user_id>`
    and `<group_id>` with your required user and group ID numbers.
    For instance, if building on a UNIX machine, use   
    `$(id -u)` and `$(id -g)` for the active user's user and group ID numbers respectively.
    On Windows

## Native Setup
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

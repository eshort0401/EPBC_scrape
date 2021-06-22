Copyright Australian Conservation Foundation (ACF). All rights reserved.
Developed by Ewan Short 2021
eshort0401@gmail.com

# Supported Systems
Unix based systems (Linux and Mac)
Windows 10. Currently operating system calls on Windows use the powershell,
which only ships by default with Windows 10. Future versions will support
older versions of Windows.

# Operation
To download the database, first open the terminal (UNIX) or powershell
(Windows 10). Activate your conda environment by typing
```
conda activate <env name>
```

# Windows

# ECBP Scraper
Note that selenium chromedriver must be of same version as chrome for code to
work.

## Requirements
chromedriver (https://chromedriver.chromium.org/downloads)
chrome
Note versions of chrome and chromedriver must match.


# Installation Notes

Install miniconda (https://docs.conda.io/en/latest/miniconda.html) or Anaconda (https://www.anaconda.com/products/individual-b).

Open Anaconda/miniconda Windows powershell from the start menu.

```
conda create -n acf
conda activate acf
conda install jupyter
conda install -c conda-forge jupyter_contrib_nbextensions
jupyter contrib nbextension install --user
conda install matplotlib, numpy, pandas, selenium, bs4, rapidfuzz
```

Create a folder called bin in C:
Download chrome
Open chrome, go to settings, and disable the “ask permission for download” option.
Go to settings, privacy and security, additional permissions, disable “ask for permission etc”.
Download chromedriver (https://chromedriver.chromium.org/downloads), extract,
and save the resulting file to C:/bin. You can create the directory C:/bin if it doesn't already exist.
Go to advanced settings in control panel, and add C:/bin to your path variable. Can also find this settings window by searching env in start seach bar.

Download ghostscript 64 bit for windows (https://www.ghostscript.com/download/gsdnld.html).
Install ghostscript.
Add the location of gswin64c.exe to the `PATH` environment variable. Default installation location is `C:\Program Files\gs\gs9.54.0\bin`.

Copyright Ewan Short. All rights reserved.

# ECBP Scraper
Note that selenium chromedriver must be of same version as chrome for code to
work.

## Requirements
chromedriver (https://chromedriver.chromium.org/downloads)
chrome
Note versions of chrome and chromedriver must match.


# Windows Installation Notes

Install miniconda (https://docs.conda.io/en/latest/miniconda.html) or Anaconda (https://www.anaconda.com/products/individual-b).

Open Anaconda/miniconda Windows powershell from the start menu.

```
conda create -n acf
conda activate acf
conda install pip
conda install jupyter
conda install -c conda-forge jupyter_contrib_nbextensions
jupyter contrib nbextension install --user
conda install matplotlib, numpy, pandas, selenium, bs4
```

Create a folder called bin in C:
Download chrome
Open chrome, go to settings, and disable the “ask permission for download” option.
Go to settings, privacy and security, additional permissions, disable “ask for permission etc”.
Download chromedriver (https://chromedriver.chromium.org/downloads), extract, and save the resulting file to C:/bin.
Go to advanced settings in control panel, and add C:/bin to your path variable. Can also find this settings window by searching env in start seach bar.

Download ghostscript 64 bit for windows (https://www.ghostscript.com/download/gsdnld.html).
Install ghostscript.
Add the location of gswin64c.exe to the `PATH` environment variable. Default installation location is `C:\Program Files\gs\gs9.54.0\bin`.

Now for pymscrape.
`conda install pypdf2, pillow, opencv, scikit-learn, scikit-image, colormath`
For the last package we need to call pip from our conda environment
`path-to-pip-in-env/pip PyMuPDF`
For windows default will be
`C:\Users\<username>\miniconda3\envs\<environment name>\Scripts\pip PyMuPDF`
Similarly install bezier, but need to add additional options to disable binary speedups, which don’t work on windows. Open powershell prompt and type
```
$BEZIER_NO_EXTENSION=$true
python -m C:\Users\<username>\miniconda3\envs\<environment name>\Scripts\pip3 install --upgrade bezier --no-binary=bezier
```

Download the QGIS Standalone Installer Version 3.18 64 bit (https://www.qgis.org/en/site/forusers/download.html#).
Install QGIS. 

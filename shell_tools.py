# Copyright Australian Conservation Foundation. All rights reserved.
# Developed by Ewan Short 2021
# eshort0401@gmail.com, https://github.com/eshort0401

import subprocess
import os


def run_powershell_cmd(shell_cmd, power_script_dir):
    with open(power_script_dir + "/tmp.ps1", "w") as f:
        f.write(shell_cmd)
    return subprocess.run(
        'powershell.exe {}/tmp.ps1'.format(power_script_dir),
        shell=True, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)


def run_common_cmd(shell_cmd, power_script_dir):
    if os.name == 'nt':
        with open(power_script_dir + "/tmp.ps1", "w") as f:
            f.write(shell_cmd)
        return subprocess.run(
            'powershell.exe {}/tmp.ps1'.format(power_script_dir),
            shell=True, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
    else:
        return subprocess.run(
            shell_cmd, shell=True, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)

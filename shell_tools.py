import subprocess
import os

def run_powershell_cmd(shell_cmd, power_script_dir):
    with open(power_script_dir + "\\tmp.ps1", "w") as f:
        f.write(shell_cmd)
    return subprocess.run(
        'powershell.exe {}\\test.ps1'.format(power_script_dir),
        shell=True)

def run_bash_cmd(shell_cmd, power_script_dir):
    if os.name == 'nt':
        with open(power_script_dir + "\\tmp.ps1", "w") as f:
            f.write(shell_cmd)
        return subprocess.run(
            'powershell.exe {}\\test.ps1'.format(power_script_dir),
            shell=True)
    else:
        return subprocess.run(shell_cmd, shell=True)

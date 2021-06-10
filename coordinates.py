# Copyright Ewan Short. All rights reserved.
import numpy as np
import tkinter as tk
import matplotlib.pyplot as plt
import subprocess
import copy

def evaluate_paraboloid(x, y, A, coeff):
    c = copy.deepcopy(coeff)
    x = np.array(x)
    y = np.array(y)
    for i in range(len(x.shape)):
        c = np.expand_dims(c, axis=1)
    return (c*A(x,y)).sum(axis=0)

def scale_points(im1, points):
    approx_lon = tk.simpledialog.askstring(
        'Enter Approx. Lon.',
        'Enter approx. lon. of top left map corner in dec. degrees '
        + '(e.g. 150.12345678): ')
    approx_lon = float(approx_lon)

    approx_lat = tk.simpledialog.askstring(
        'Enter Approx. Lat.',
        'Enter approx. lat. of top left map corner in signed dec. degrees '
        + '(e.g. -25.12345678): ')
    approx_lat = float(approx_lat)

    approx_spread = tk.simpledialog.askstring(
        'Enter Approx. Width',
        'Enter approx. width of map in dec. degrees (e.g. 0.05): ')
    approx_spread = float(approx_spread)

    scaled_points = [
        (
            approx_spread*x[0]/im1.shape[0] + approx_lon,
            -approx_spread*x[1]/im1.shape[1] + approx_lat)
        for x in points]
    return scaled_points, approx_lon, approx_lat, approx_spread

def save_reference_image(path, im1, points, names):
    fig, ax = plt.subplots(1, figsize=(20,20))
    ax.imshow(im1)
    for i in range(len(points)):
        ax.plot(points[i][0], points[i][1], '.r', markersize=10)
        ax.text(
            points[i][0]+20, points[i][1]+12, names[i], color='r',
            fontsize=16)
        plt.tick_params(
            which='both', bottom=False, top=False, left=False, right=False,
            labelbottom=False, labelleft=False)
    fig.savefig(path)

def create_JSON_dirs(base_dir, sub_dir):
    subprocess.run('rm -r ' + base_dir + sub_dir + '/JSON/raw', shell=True)
    subprocess.run('mkdir -p ' + base_dir + sub_dir + '/JSON/raw', shell=True)
    subprocess.run('mkdir -p ' + base_dir + sub_dir + '/JSON/edited', shell=True)

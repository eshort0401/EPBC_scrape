import gui
from scrape_svg import convert_transform, gen_poly_coords

import numpy as np
from skimage import data, segmentation, feature, future
from skimage.io import imread
from skimage.morphology import remove_small_objects
from scipy import ndimage as ndi
from skimage import feature
from skimage.filters import median
from sklearn.ensemble import RandomForestClassifier
import simplekml
from functools import partial
import fitz
from bs4 import BeautifulSoup
import subprocess
import matplotlib.pyplot as plt
import cv2 as cv

import tkinter as tk

def scrape_bmp(
        master, file_path, page_num, base_dir, sub_dir, leg_names, im_leg,
        LON, LAT, pb_tl, pb_br):

    dir = base_dir + sub_dir

    pdf_file = fitz.open(file_path)
    page = pdf_file[page_num]
    p_width = page.mediabox_size[0]
    p_height = page.mediabox_size[1]

    svg = page.get_svg_image(text_as_path=False)
    small_soup = BeautifulSoup(svg, features='lxml')

    [s.decompose() for s in small_soup('path')]
    [s.decompose() for s in small_soup('text')]

    for s in small_soup('image'):
        transform = convert_transform(s.parent.parent['transform'])
        img_width = abs(float(s['width'])*transform[0,0])
        img_height = abs(float(s['height'])*transform[1,1])
        if img_width > 0.6*p_width:
            continue
        elif img_height > 0.6*p_height:
            continue
        s.decompose()

    fname = dir + '/' + str(page_num) + '/no_overlays.svg'
    f = open(fname, 'w')
    f.write(small_soup.svg.prettify())
    f.close()

    cmd = (
        'inkscape {} --export-filename={} '
        + '--export-background=FFFFFFFF --export-area=0:0:{}:{}')
    cmd = cmd.format(
        fname, dir + '/' + str(page_num) + '/no_overlays.png',
        np.ceil(p_width).astype(int), np.ceil(p_height).astype(int))
    subprocess.run(cmd, shell=True)

    im2 = imread(dir + '/' + str(page_num) + '/no_overlays.png')

    training_win = tk.Toplevel(master)
    training_win.geometry(
        str(round(1.1*im2.shape[1])) + 'x' + str(round(1.1*im2.shape[0])))
    training_app = gui.Define_Training_Regions(
        training_win, im2, sorted(list(set(leg_names))), legend=im_leg)
    master.wait_window(training_win)

    training_labels = np.zeros(im2.shape[:2])
    for i in range(len(training_app.boxes)):
        for box in training_app.boxes[i]:
            training_labels[box[1]:box[3], box[0]:box[2]] = i+1

    sigma_min = 1
    sigma_max = 2
    features_func = partial(feature.multiscale_basic_features,
                            intensity=True, edges=False, texture=True,
                            sigma_min=sigma_min, sigma_max=sigma_max,
                            multichannel=True)
    features = features_func(im2)
    clf = RandomForestClassifier(n_estimators=50, n_jobs=-1,
                                 max_depth=10, max_samples=0.05)
    clf = future.fit_segmenter(training_labels, features, clf)
    result = future.predict_segmenter(features, clf)

    fig, ax = plt.subplots(2, 1, sharex=True, sharey=True, figsize=(20, 40))
    gray = cv.cvtColor(im2, cv.COLOR_BGR2GRAY)
    ax[0].imshow(segmentation.mark_boundaries(gray, result, mode='thick'))
    ax[0].contour(training_labels)
    ax[0].set_title('Image, mask and segmentation boundaries')

    poly_box = np.zeros(im2.shape[:2])
    poly_box[pb_tl[1]:pb_br[1], pb_tl[0]:pb_br[0]]=1
    poly_box = poly_box.astype(bool)
    poly_box = np.logical_not(poly_box)
    result[poly_box] = 1

    ax[1].imshow(result, cmap='Pastel1')
    ax[1].set_title('Segmentation')
    fig.tight_layout()
    plt.savefig(dir + '/' + str(page_num) + '/segmentation.png')

    choose_win = tk.Toplevel(master)
    choose_app = gui.Choose_Kept_Categories(
        choose_win, training_app.names)
    master.wait_window(choose_win)

    result = median(result, selem=np.ones([2,2]))

    inds = (np.where([v.get() for v in choose_app.v])[0]+1).tolist()
    poly_colours = []
    line_colours = []
    alpha='80'
    for i in inds:
        try:
            cp = im2[result==i].mean(axis=0)/255
            cp = to_hex(cp, keep_alpha=True)[1:]
            cp = cp[6:]+cp[4:6]+cp[2:4]+cp[0:2]
            line_colours.append(cp)
            cp_fill = copy.deepcopy(cp)
            cp_fill = alpha + cp_fill[2:]
            poly_colours.append(cp_fill)
        except:
            line_colours.append('ff000000')
            poly_colours.append('80000000')

    kml = simplekml.Kml()
    kml.document.name = str(page_num) + '_image'

    styles = []
    for i in range(len(inds)):
        sty = simplekml.Style()
        sty.linestyle.width = 2
        sty.linestyle.color = line_colours[i]
        sty.polystyle.color = poly_colours[i]
        styles.append(sty)

    for i in range(len(inds)):
    #     filled = ndi.binary_fill_holes(result==inds[i])
        filled = (result==inds[i])
        obj_size_ratio = 5e-10
        min_size = int(obj_size_ratio*im2.shape[0]*im2.shape[1])
        filled = remove_small_objects(filled, min_size = min_size)
    #     filled = ndi.binary_fill_holes(filled)

        label_objects, nb_labels = ndi.label(filled)
        label_objects = label_objects.astype(np.uint8)

        obj_contours, hierarchy = cv.findContours(
            label_objects, cv.RETR_CCOMP, cv.CHAIN_APPROX_TC89_L1
        )

        smooth_obj_contours = []
        for cnt in obj_contours:
            epsilon = 0.0001*cv.arcLength(cnt,True)
            smooth_obj_contours.append(
                cv.approxPolyDP(cnt,epsilon,True)
            )

        poly_coords = gen_poly_coords(smooth_obj_contours, LON, LAT)

        if poly_coords:
            fol = kml.newfolder(name=training_app.names[inds[i]-1])
            parents = np.argwhere(hierarchy[0][:,3]==-1).flatten()
            for j in range(len(parents)):
                poly = fol.newpolygon(
                    name = training_app.names[inds[i]-1] + ' ' + str(j+1),
                    outerboundaryis = (
                        poly_coords[parents[j]]
                        + [poly_coords[parents[j]][0]]
                    ),
                    altitudemode='relativetoground',
                )
                children = np.argwhere(
                    hierarchy[0][:,3]==parents[j]
                ).flatten()
                if len(children) > 0:
                    inner_boundaries = []
                    for k in range(len(children)):
                        if len(poly_coords[children[k]]) > 3:
                            inner_boundaries.append(
                                poly_coords[children[k]]
                                + [poly_coords[children[k]][0]]
                            )
                    poly.innerboundaryis = inner_boundaries
                poly.style = styles[i]
    kml.save(dir + '/' + str(page_num) + '/image.kml')

    subprocess.run(
        'cp ' + base_dir + '/reference.qgs ' + base_dir
        + sub_dir + '/reference.qgs', shell=True
    )

    cmd=(
        'qgis --project ' + dir + '/reference.qgs '
        + dir + '/' + str(page_num)
        + '/image.kml --extent {},{},{},{}'
    ).format(np.min(LON), np.min(LAT), np.max(LON), np.max(LAT))

    subprocess.run(cmd, shell=True)

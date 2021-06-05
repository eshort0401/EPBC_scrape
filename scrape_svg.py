import re
import numpy as np
from scipy.spatial.distance import cdist
import cv2 as cv
import copy
import bezier
from bs4 import BeautifulSoup
import tkinter as tk
import subprocess
import fitz
import pylab

import gui

from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie2000

from matplotlib.colors import to_hex
from matplotlib.colors import to_rgb

import simplekml

def hex_to_kml_hex(hex_col, with_hash=True, alpha='ff'):
    if with_hash:
        kml_hex = hex_col[1:]
    kml_hex = alpha + kml_hex[6:] + kml_hex[4:6] + kml_hex[2:4] + kml_hex[0:2]
    return kml_hex


def gen_poly_coords(coords, LON, LAT):
    poly_coords = [
        [
            (
                LON[coords[i][j][0][1], coords[i][j][0][0]],
                LAT[coords[i][j][0][1], coords[i][j][0][0]], 1.0)
            for j in range(len(coords[i]))]
        for i in range(len(coords))]
    return poly_coords


def scrape_svg(
        file_path, page_num, im1, base_dir, sub_dir,
        master, LON, LAT, zoom_factor):

    thresh = 1e-20
    min_path = 2
    tol = 5e-4
    min_leg_path = 3

    dir = base_dir + sub_dir

    subprocess.run(
        'mkdir ' + dir + '/' + str(page_num), shell=True)

    pdf_file = fitz.open(file_path)
    page = pdf_file[page_num]

    p_width = page.mediabox_size[0]
    p_height = page.mediabox_size[1]
    p_area = p_width*p_height
    blocks = page.getTextBlocks()

    leg_txt_box_ind = np.argmax(
        [('legend' in block[4].lower()) for block in blocks]
    )
    [x1, y1, x2, y2] = np.array(blocks[leg_txt_box_ind][:4])*zoom_factor

    svg = page.get_svg_image(text_as_path=False)
    svg_tap = page.get_svg_image(text_as_path=True)

    soup = BeautifulSoup(svg, features='lxml')
    soup_tap = BeautifulSoup(svg_tap, features='lxml')

    f = open(
        dir + '/' + str(page_num) + '/full_image.svg', 'w')
    f.write(soup_tap.svg.prettify())
    f.close()

    choose_legend_win = tk.Toplevel(master)
    choose_legend_win.attributes('-zoomed', True)
    leg_app = gui.Get_Legend_Box(
        choose_legend_win, im1,
        'Right click to select top left and bottom '
        + 'right corners of legend box.'
    )
    master.wait_window(choose_legend_win)

    lb_tl = np.array(leg_app.p1).astype(int)
    lb_br = np.array(leg_app.p2).astype(int)

    im_leg = im1[lb_tl[1]:lb_br[1], lb_tl[0]:lb_br[0], :]

    choose_content_win = tk.Toplevel(master)
    choose_content_win.attributes('-zoomed', True)
    content_app = gui.Get_Legend_Box(
        choose_content_win, im1,
        'Right click to select top left and bottom right corners of '
        + 'region containing items of interest.'
    )
    master.wait_window(choose_content_win)

    pb_tl = np.array(content_app.p1).astype(int)
    pb_br = np.array(content_app.p2).astype(int)

    paths = soup.svg.find_all('path')
    long_paths = [
        p for p in paths
        if len(re.split('l|c|v|h', p['d'].lower())) >= min_path]
    long_clippaths = [
        p for p in paths
        if len(re.split('l|c|v|h', p['d'].lower())) >= min_path]

    long_paths = [
        p for p in long_paths if 'stroke' in p.attrs.keys()
        or 'fill' in p.attrs.keys()]
    long_clippaths = [
        p for p in long_clippaths if (
            ('stroke' not in p.attrs.keys())
            and ('fill' not in p.attrs.keys()))]

    use_paths = soup_tap('use')
    use_paths = [
        p for p in use_paths if (
            'stroke' in p.attrs.keys()
            or 'fill' in p.attrs.keys())
        and 'xlink:href' in p.attrs.keys()]

    svg_coords, svg_stroke, svg_fill = convert_path_coords(
        long_paths, im1.shape, thresh)
    cp_coords, cp_stroke, cp_fill = convert_path_coords(
        long_clippaths, im1.shape, thresh)
    use_coords, use_stroke, use_fill, use_paths = convert_use_coords(
        use_paths, soup_tap, im1.shape, thresh)

    svg_coords, svg_stroke, svg_fill = remove_duplicates(
        svg_coords, svg_stroke, svg_fill)
    svg_coords, svg_stroke, svg_fill = join_coords(
        svg_coords, svg_stroke, svg_fill)
    # cp_coords, cp_stroke, cp_fill = join_coords(
    #     cp_coords, cp_stroke, cp_fill)

    svg_coords, svg_stroke, svg_fill = check_areas(
        svg_coords, svg_stroke, svg_fill, thresh=5)
    cp_coords, cp_stroke, cp_fill = check_areas(
        cp_coords, cp_stroke, cp_fill, thresh=5)

    [svg_in_poly_box, cp_in_poly_box, use_in_poly_box] = [
        [
            np.all(pb_tl[0]-2 <= c[:, 0, 0])
            * np.all(c[:, 0, 0] <= pb_br[0] + 2)
            * np.all(pb_tl[1] - 2 <= c[:, 0, 1])
            * np.all(c[:, 0, 1] < pb_br[1] + 2)
            for c in cds]
        for cds in [svg_coords, cp_coords, use_coords]]

    [use_in_leg_box, cp_in_leg_box, svg_in_leg_box] = [
        [
            np.all(lb_tl[0]-2 <= c[:, 0, 0])
            * np.all(c[:, 0, 0] <= lb_br[0] + 2)
            * np.all(lb_tl[1] - 2 <= c[:, 0, 1])
            * np.all(c[:, 0, 1] < lb_br[1] + 2)
            for c in coords]
        for coords in [use_coords, cp_coords, svg_coords]]

    [use_obj_coords, use_obj_stroke, use_obj_fill] = [
        [
            obj[i] for i in range(len(use_coords)) if use_in_poly_box[i]
            and not use_in_leg_box[i]]
        for obj in [use_coords, use_stroke, use_fill]]

    [use_leg_coords, use_leg_stroke, use_leg_fill] = [
        [obj[i] for i in range(len(use_coords)) if use_in_leg_box[i]]
        for obj in [use_coords, use_stroke, use_fill]]

    best_leg_match = []
    if use_obj_coords and use_leg_coords:
        leg_match = [
            np.argwhere(f == np.array(use_leg_fill)) for f in use_obj_fill]
        best_leg_match = []
        for i in range(len(use_obj_coords)):
            obj = use_obj_coords[i]
            leg_objs = [use_leg_coords[j] for j in leg_match[i].flatten()]
            try:
                ind = np.argmin(
                    [
                        cv.matchShapes(obj, leg_obj, 1, 0)
                        for leg_obj in leg_objs]
                )
                best_leg_match.append(leg_match[i].flatten()[ind])
            except:
                best_leg_match.append(0)
    else:
        [
            use_obj_coords, use_obj_stroke, use_obj_fill,
            use_leg_coords, use_leg_stroke, use_leg_fill] = [[]]*6

    svg_shapes = [
        cv.drawContours(np.zeros(im1.shape[:2]), svg_coords, i, 1, -1)
        for i in range(len(svg_coords))]
    cp_shapes = [
        cv.drawContours(np.zeros(im1.shape[:2]), cp_coords, i, 1, -1)
        for i in range(len(cp_coords))]

    [svg_coords, svg_stroke, svg_fill] = [
        [
            obj[i] for i in range(len(svg_coords))
            if svg_in_poly_box[i] and not svg_in_leg_box[i]]
        for obj in [svg_coords, svg_stroke, svg_fill]]

    [cp_coords, cp_stroke, cp_fill] = [
        [
            obj[i] for i in range(len(cp_coords))
            if cp_in_poly_box[i] and not cp_in_leg_box[i]]
        for obj in [cp_coords, cp_stroke, cp_fill]]

    cp_match_ratios = []
    for cp in cp_shapes:
        best_match = max([np.equal(cp,s).sum() for s in svg_shapes])/cp.size
        cp_match_ratios.append(best_match)

    max_bad_pix = [tol*cp.sum() for cp in cp_shapes]
    match_thresh = [(im1.size-bp)/im1.size for bp in max_bad_pix]
    keep_cp = (np.array(cp_match_ratios) < np.array(match_thresh))

    cp_coords = [
        cp_coords[i] for i in range(len(cp_coords))
        if keep_cp[i]]

    leg_paths = [
        p for p in paths if
        (min_leg_path <= len(re.split('l|v|h|c',p['d'].lower())))
        and
        (
            (('stroke' in p.attrs.keys()) and (p['stroke'] != 'none'))
            or
            (('fill' in p.attrs.keys()) and (p['fill'] != 'none')))]

    leg_coords, leg_stroke, leg_fill = convert_path_coords(
        leg_paths, im1.shape, thresh)

    closed = [
        np.all(leg_coords[i][0] == leg_coords[i][-1])
        for i in range(len(leg_coords))]

    in_box = [
        np.all(lb_tl[0]-2 <= c[:,0,0])
        *np.all(c[:,0,0] <= lb_br[0]+2)
        *np.all(lb_tl[1]-2 <= c[:,0,1])
        *np.all(c[:,0,1] < lb_br[1]+2)
        for c in leg_coords]

    leg_max_area = 1e-2
    leg_coords_old = copy.deepcopy(leg_coords)
    [leg_coords, leg_stroke, leg_fill] = [
        [
            obj[i] for i in range(len(obj)) if
            cv.contourArea(
                np.round(leg_coords_old[i]).astype(np.int32)
            ) < leg_max_area*p_area
            and
            in_box[i]
            and closed[i]
        ] for obj in [leg_coords, leg_stroke, leg_fill]]

    svg_leg_text = soup.svg.find_all('tspan')
    leg_max_chars = 100
    svg_leg_text = [
        t for t in svg_leg_text
        if (1 < len(' '.join(t.contents)) < leg_max_chars)
        and 'legend' not in t.get_text().lower()]
    lt_coords = convert_tspan_coords(svg_leg_text, im1.shape)

    in_box = [
        np.any(
            (lb_tl[0]-2 <= c[:,0,0])
            *(c[:,0,0] <= lb_br[0]+2)
            *(lb_tl[1]-2 <= c[:,0,1])
            *(c[:,0,1] < lb_br[1]+2)) for c in lt_coords]

    svg_leg_text = [
        svg_leg_text[i] for i in range(len(svg_leg_text))
        if in_box[i]]
    lt_coords = [lt_coords[i] for i in range(len(lt_coords)) if in_box[i]]

    closest_t = get_nearest_text(leg_coords, lt_coords)
    use_closest_t = get_nearest_text(use_leg_coords, lt_coords)

    leg_colors = []
    for i in range(len(leg_coords)):
        if leg_fill[i] != 'none':
            leg_colors.append(leg_fill[i])
        elif leg_stroke[i] != 'none':
            leg_colors.append(leg_stroke[i])
        else:
            leg_colors.append('none')

    leg_match = []
    leg_lab = [
        convert_color(
            sRGBColor(to_rgb(lc)[0], to_rgb(lc)[1], to_rgb(lc)[2]),
            LabColor)
        for lc in leg_colors]
    if leg_colors:
        leg_areas = [cv.contourArea(lc) for lc in leg_coords]
        for i in range(len(svg_coords)):
            stroke_dist = []
            fill_dist = []
            if svg_stroke[i] != 'none':
                stroke_rgb = to_rgb(svg_stroke[i])
                stroke_lab = convert_color(
                    sRGBColor(stroke_rgb[0], stroke_rgb[1], stroke_rgb[2]),
                    LabColor)
                stroke_dist = [
                    delta_e_cie2000(stroke_lab, lc)
                    for lc in leg_lab]
            if svg_fill[i] != 'none':
                fill_rgb = to_rgb(svg_fill[i])
                fill_lab = convert_color(
                    sRGBColor(fill_rgb[0], fill_rgb[1], fill_rgb[2]),
                    LabColor)
                fill_dist = [
                    delta_e_cie2000(fill_lab, lc)
                    for lc in leg_lab]
            if stroke_dist and not fill_dist:
                matches = np.where(stroke_dist == np.min(stroke_dist))
                if len(matches[0]) == 1:
                    leg_match.append(matches[0][0])
                else:
                    area = cv.contourArea(svg_coords[i])
                    area_diffs = [
                        abs(area-leg_areas[j])
                        for j in range(len(leg_areas))
                        if j in matches[0]]
                    leg_match.append(matches[0][np.argmin(area_diffs)])
            elif fill_dist and not stroke_dist:
                matches = np.where(fill_dist == np.min(fill_dist))
                if len(matches[0]) == 1:
                    leg_match.append(matches[0][0])
                else:
                    area = cv.contourArea(svg_coords[i])
                    area_diffs = [
                        abs(area-leg_areas[j])
                        for j in range(len(leg_areas))
                        if j in matches[0]]
                    leg_match.append(matches[0][np.argmin(area_diffs)])
            else:
                # This can be amended to match method of above in
                # cases of multiple color matches
                comb_dist = np.array([stroke_dist, fill_dist])
                leg_match.append(
                    np.unravel_index(
                        np.argmin(comb_dist),
                        comb_dist.shape)[1])

    leg_text_all = []
    for s in svg_leg_text:
        cond1 = (s.parent.parent.name == 'g')
        cond1 *= (s.parent.parent.has_attr('clip-path'))
        cond1 *= (len(s.parent.parent('image')) == 0)
        cond2 = (len(s.parent('tspan'))==1)
        if cond1 and cond2:
            leg_text_all.append(s.parent.parent.get_text())
        elif cond2:
            leg_text_all.append(s.parent.get_text())
        else:
            leg_text_all.append(s.get_text())

    # import pdb; pdb.set_trace()
    leg_text_all = [
        re.sub('(\n)|!|\^|\N{PLUS-MINUS SIGN}', ' ', t) for t in leg_text_all]
    leg_text_all = [re.sub('[ ]{2,}', ' ', t) for t in leg_text_all]
    leg_text_all = [re.sub('(^[ ]+)|([ ]+$)', '', t) for t in leg_text_all]
    leg_text_all = [
        re.sub('([a-z]{2,})([A-Z])', r'\1 \2', t) for t in leg_text_all]

    leg_text = [leg_text_all[ind] for ind in closest_t]
    use_leg_text = [leg_text_all[ind] for ind in use_closest_t]

    leg_text_all = list(set(leg_text_all))

    confirm_names_win = tk.Toplevel(master)
    names_app = gui.Confirm_Names(confirm_names_win, leg_text_all)
    master.wait_window(confirm_names_win)

    leg_text_all_corrected = [
        names_app.n[i].get() for i in range(len(names_app.n))]

    if leg_text:
        names = [leg_text[lm] for lm in leg_match]
    else:
        names = ['Not identified']*len(svg_coords)

    use_names = []
    if best_leg_match:
        use_names = [use_leg_text[i] for i in best_leg_match]

    try:
        names = np.array(names).astype('<U100')
        for i in range(len(leg_text_all)):
            names[names==leg_text_all[i]] = leg_text_all_corrected[i]
        names = names.tolist()
    except:
        print(names)

    # Check polylabels
    name_poly_win = tk.Toplevel(master)
    name_poly_win.attributes('-zoomed', True)
    poly_app = gui.Name_Polygons(
        name_poly_win, im1, svg_coords,
        leg_text_all_corrected, names = names)
    master.wait_window(name_poly_win)

    poly_names = poly_app.names

    [svg_coords, svg_stroke, svg_fill, poly_names]  = [
        [
            obj[i] for i in range(len(svg_coords)) if poly_app.highlighted[i]]
        for obj in [svg_coords, svg_stroke, svg_fill, poly_names]]

    if use_obj_coords:
        try:
            use_names = np.array(use_names).astype('<U100')
            for i in range(len(leg_text_all)):
                use_names[use_names==leg_text_all[i]] = leg_text_all_corrected[i]
            use_names = use_names.tolist()
        except:
            print(use_names)

        # Check polylabels
        name_use_win = tk.Toplevel(master)
        name_use_win.attributes('-zoomed', True)
        name_use_app = gui.Name_Polygons(
            name_use_win, im1, use_obj_coords, leg_text_all_corrected, names = use_names
        )
        master.wait_window(name_use_win)
        use_names = name_use_app.names

        [use_obj_coords, use_obj_stroke, use_obj_fill, use_names]  = [
            [
                obj[i] for i in range(len(use_obj_coords))
                if name_use_app.highlighted[i]]
            for obj in [use_coords, use_obj_stroke, use_obj_fill, use_names]]

    svg_coords += use_obj_coords
    svg_stroke += use_obj_stroke
    svg_fill += use_obj_fill
    poly_names += use_names

    if cp_coords:
        name_cp_win = tk.Toplevel(master)
        name_cp_win.attributes('-zoomed', True)
        cp_app = gui.Name_Polygons(
            name_cp_win, im1, cp_coords, leg_text_all_corrected)
        master.wait_window(name_cp_win)

        cp_names = cp_app.names
        [cp_coords, cp_names] = [
            [
                obj[i] for i in range(len(cp_coords)) if cp_app.highlighted[i]]
            for obj in [cp_coords, cp_names]]
    else:
        cp_names = []

    poly_line=[]
    poly_fill=[]
    for i in range(len(svg_fill)):
        if svg_stroke[i] == 'none' and svg_fill[i] != 'none':
            poly_line.append(hex_to_kml_hex(svg_fill[i], alpha='ff'))
            poly_fill.append(hex_to_kml_hex(svg_fill[i], alpha='80'))

        elif svg_fill[i] == 'none' and svg_stroke[i] != 'none':
            poly_fill.append(hex_to_kml_hex(svg_stroke[i], alpha='80'))
            poly_line.append(hex_to_kml_hex(svg_stroke[i], alpha='ff'))
        else:
            poly_fill.append('80ff0000')
            poly_fill.append('ffff0000')

    subprocess.run(
        'mkdir ' + dir + '/' + str(page_num),
        shell=True)
    subprocess.run(
        'rm ' + dir + '/' + str(page_num)
        + '/svg.kml', shell=True)

    kml = simplekml.Kml()
    kml.document.name = str(page_num) + '_svg'

    styles = []
    for i in range(len(svg_coords)):
        sty = simplekml.Style()
        sty.linestyle.width = 2
        sty.linestyle.color = poly_line[i]
        sty.polystyle.color = poly_fill[i]
        styles.append(sty)

    poly_coords = gen_poly_coords(svg_coords, LON, LAT)

    for name in set(poly_names):
        fol = kml.newfolder(name=name)
        poly_inds = np.where(np.array(poly_names)==name)[0].tolist()
        for j in range(len(poly_inds)):
            if poly_coords[poly_inds[j]][0] == poly_coords[poly_inds[j]][-1]:
                poly = fol.newpolygon(
                    name = name + ' ' + str(j+1),
                    outerboundaryis = poly_coords[poly_inds[j]],
                    altitudemode='relativetoground')
            else:
                poly = fol.newlinestring(
                    name = name + ' ' + str(j+1),
                    coords = poly_coords[poly_inds[j]],
                    altitudemode='relativetoground')
            poly.style = styles[poly_inds[j]]

    if cp_coords:
        unique_cp_names = list(set(cp_names))
        num_colours = len(unique_cp_names)
        alpha=0.75
        cm = pylab.get_cmap('Set1')
        poly_colours = []
        line_colours = []

        for i in range(num_colours):
            cp = list(cm(1.*i/num_colours))
            cline = copy.deepcopy(cp)
            cp[3] = alpha
            cp = to_hex(cp, keep_alpha=True)[1:]
            cp = cp[6:]+cp[4:6]+cp[2:4]+cp[0:2]
            poly_colours.append(cp)
            cline = (np.array(cline)*0.8).tolist()
            cline[3] = alpha

            cline = to_hex(cline, keep_alpha=True)[1:]
            cline = cline[6:]+cline[4:6]+cline[2:4]+cline[0:2]
            line_colours.append(cline)

        styles = {}
        for i in range(len(unique_cp_names)):
            sty = simplekml.Style()
            sty.linestyle.width = 2
            sty.linestyle.color = poly_colours[i]
            sty.polystyle.color = line_colours[i]
            styles[unique_cp_names[i]]= sty

        poly_coords = gen_poly_coords(cp_coords, LON, LAT)

        for name in unique_cp_names:
            fol = kml.newfolder(name=name)
            poly_inds = np.where(np.array(cp_names)==name)[0].tolist()
            for j in range(len(poly_inds)):
                if poly_coords[poly_inds[j]][0] == poly_coords[poly_inds[j]][-1]:
                    poly = fol.newpolygon(
                        name = name + ' ' + str(j+1),
                        outerboundaryis = poly_coords[poly_inds[j]],
                        altitudemode='relativetoground')
                else:
                    poly = fol.newlinestring(
                        name = name + ' ' + str(j+1),
                        coords = poly_coords[poly_inds[j]],
                        altitudemode='relativetoground')
                poly.style = styles[name]
    kml.save(
        dir + '/'
        + str(page_num) + '/svg.kml')

    subprocess.run(
        'cp ' + base_dir + '/reference.qgs ' + base_dir
        + sub_dir + '/reference.qgs', shell=True)

    cmd=(
        'qgis --project ' + dir + '/reference.qgs '
        + dir + '/' + str(page_num)
        + '/svg.kml --extent {},{},{},{}'
    ).format(np.min(LON), np.min(LAT), np.max(LON), np.max(LAT))

    if (svg_coords+cp_coords):
        subprocess.run(cmd, shell=True)

    return leg_text_all_corrected + cp_names, im_leg, pb_tl, pb_br

def convert_path_coords(path_list, shape, thresh):
    path_coords = []
    stroke = []
    fill = []
    for p in path_list:
        # if 'L -1.439 19.679 L -.96 22.319 L' in p['d']:
        #     import pdb; pdb.set_trace()
        coords = interp_bezier(p['d'])
        has_z = re.search('(z\s*)$', coords.lower())
        coords = re.split('[a-zA-Z]', coords)
        coords.remove('')
        regex = re.compile(' +')
        coords = [c for c in coords if not regex.fullmatch(c)]
        coords = [
            re.sub(
                '(-*[0-9]*\.*[0-9]+)( )(-*[0-9]*\.*[0-9]+)', r'\1,\3', t
            ).split(',') for t in coords]
        if has_z:
            coords += [coords[0]]
        coords = np.array(coords).astype(float)

        coords = np.append(
            coords, values=np.ones([len(coords),1]), axis=1
        )

        if 'transform' in p.attrs.keys():
            transform = convert_transform(p['transform'])
            new_coords = (np.matmul(transform,coords.T)[0:2]).T
        else:
            new_coords = coords[0:2]

        new_coords = np.around(new_coords).astype(int)
        new_coords = crop_coords(new_coords, shape)
        new_coords = new_coords.reshape(
            [new_coords.shape[0],1,new_coords.shape[1]]
        )
        # Remove duplicate points
        new_coords = np.array(
            [
                v for i, v in enumerate(new_coords)
                if i == 0 or np.any(v != new_coords[i-1])
            ]
        )
        # Split coords into seperate coords if repeated point
        split_coords = []
        start = 0
        for i in range(1,len(new_coords)):
            previous = new_coords[start:i]
            m = np.argwhere(
                np.all(previous == new_coords[i], axis=2).flatten()
            ).flatten()
            if m.size > 0:
                if m[0] != 0:
                    # Add leading non-closed path
                    split_coords.append(new_coords[start:start+m[0]+1])
                # Add closed path
                split_coords.append(new_coords[start+m[0]:i+1])
                start = copy.deepcopy(i)
            if i == len(new_coords)-1:
                # Add trailing path
                split_coords.append(new_coords[start:])
        if len(split_coords) == 0:
            split_coords = [new_coords]

        for c in split_coords:
            area = cv.contourArea(c)
            if not area:
                area = 0
            if .85*shape[0]*shape[1] >= area:

                path_coords.append(c)
                try:
                    stroke.append(p['stroke'])
                except:
                    stroke.append('none')
                try:
                    fill.append(p['fill'])
                except:
                    fill.append('none')

    return path_coords, stroke, fill

def match_bezier(d):
    c_matches = re.finditer(
        '([a-zA-Z] +)*(-*[0-9]*\.*[0-9]+) (-*[0-9]*\.*[0-9]+) +'
        + 'c +(-*[0-9]*\.*[0-9]+) (-*[0-9]*\.*[0-9]+) '
        + '(-*[0-9]*\.*[0-9]+) (-*[0-9]*\.*[0-9]+) '
        + '((-*[0-9]*\.*[0-9]+) (-*[0-9]*\.*[0-9]+))*',
        d.lower()
    )
    match_list = []
    for c in c_matches:
        match_list.append(c)
    match_list = match_list[::-1]
    return match_list

def interp_bezier(d):
    match_list = match_bezier(d)
    while len(match_list)>0:
        for c in match_list:
            n = c.group(0).replace(' c', '').replace('l', '')
            n = np.array(n.replace('m', '').split())
            n = n.astype(float)
            n = n.reshape([len(n)//2,2]).T
            curve = bezier.curve.Curve.from_nodes(n)
            interp = np.round(curve.evaluate_multi(np.linspace(0,1,9)),4)
            interp = interp.astype(str).T
            repl = ['l {} {} '.format(coord[0], coord[1]) for coord in interp]
            repl = ''.join(repl)
            d = d[0:c.span(0)[0]] + repl + d[c.span(0)[1]:]

        match_list = match_bezier(d)
    return d

def crop_coords(coords, shape):
    coords[:,0][coords[:,0] >= shape[1]] = shape[1]-1
    coords[:,0][coords[:,0] < 0] = 0
    coords[:,1][coords[:,1] >= shape[0]] = shape[0]-1
    coords[:,1][coords[:,1] < 0] = 0
    return coords

def convert_tspan_coords(tspan_list, shape):
    tspan_coords = []
    [x, y] = [[t[c].split(' ') for t in tspan_list] for c in ['x', 'y']]
    for i in range(len(x)):
        if len(x[i])==1:
            x[i] = x[i]*len(y[i])
        if len(y[i])==1:
            y[i] = y[i]*len(x[i])

    coords = [
        np.array(
            [x[i], y[i], np.ones(len(x[i]))]).astype(float)
        for i in range(len(x))]

    for i in range(len(tspan_list)):
        p = tspan_list[i].parent
        transform = convert_transform(p['transform'])
        new_coords = (np.matmul(transform,coords[i])[0:2]).T
        new_coords = np.around(new_coords).astype(int)
        new_coords = crop_coords(new_coords, shape)
        tspan_coords.append(
            new_coords.reshape([new_coords.shape[0],1,new_coords.shape[1]]))
    return tspan_coords

def convert_use_coords(use_list, soup_tap, shape, thresh):

    use_coords = []
    stroke = []
    fill = []
    obj_list = []
    for i in range(len(use_list)):
        p = soup_tap.find(
            'symbol', id=use_list[i]['xlink:href'][1:]).path
        transform = convert_transform(use_list[i]['transform'])
        coords = interp_bezier(p['d'].lower())
        has_z = re.search('(z\s*)$', coords.lower())
        coords = re.split('[a-zA-Z]', coords)
        coords.remove('')
        regex = re.compile(' +')
        coords = [c for c in coords if not regex.fullmatch(c)]
        coords = [
            re.sub(
                '(-*[0-9]*\.*[0-9]+)( )(-*[0-9]*\.*[0-9]+)', r'\1,\3', t
            ).split(',') for t in coords]
        if has_z:
            coords += [coords[0]]
        coords = np.array(coords).astype(float)
        coords = np.append(
            coords, values=np.ones([len(coords),1]), axis=1)
        new_coords = (np.matmul(transform,coords.T)[0:2]).T
        new_coords = np.around(new_coords).astype(int)
        new_coords = crop_coords(new_coords, shape)
        new_coords = new_coords.reshape(
            [new_coords.shape[0],1,new_coords.shape[1]])

        use_coords.append(new_coords)
        obj_list.append(use_list[i])
        try:
            stroke.append(p['stroke'])
        except:
            try:
                stroke.append(use_list[i]['stroke'])
            except:
                stroke.append('none')
        try:
            fill.append(p['fill'])
        except:
            try:
                fill.append(use_list[i]['fill'])
            except:
                fill.append('none')

    return use_coords, stroke, fill, obj_list

def convert_transform(transform_string):
    transform = np.array(
        re.split(
            ',| ',
            transform_string.replace('matrix(', '').replace(')', '')))
    transform = transform.astype(float)
    transform = transform.reshape([3,2]).T
    transform = transform.tolist()
    transform.append([0,0,1])
    transform = np.array(transform)
    return transform

def get_nearest_text(leg_coords, lt_coords):
    closest_t = []
    for lc in leg_coords:
        # import pdb; pdb.set_trace()
        distances=[]
        for tc in lt_coords:
        # Assume text likely beside icon, so penalise vertical distances
            distances.append(
                np.min(
                    cdist(
                        lc.squeeze(axis=1), tc.squeeze(axis=1),
                        'euclidean', w=[1, 4])))
        closest_t.append(np.argmin(np.array(distances)))
    return closest_t

def remove_duplicates(coords, stroke, fill):
    i = 0
    f_i = len(coords)
    while i < f_i:
        j = i+1
        f_j = len(coords)
        while j < f_j:
            if np.array_equal(coords[i], coords[j]):
                for obj in [coords, stroke, fill]:
                    del obj[j]
                f_j -= 1
                f_i -= 1
                continue
            j += 1
        i += 1
    return coords, stroke, fill

def join_coords(coords, stroke, fill):
    i = 0
    f  = len(coords)
    while i < f:
        match = False
        j = i+1
        i_closed = np.all(coords[i][0][0] == coords[i][-1][0])
        while j < f and not i_closed:
            j_closed = np.all(coords[j][0][0] == coords[j][-1][0])
            if (stroke[i] == stroke[j]) and (fill[i] == fill[j]) and not j_closed:
                if np.all(coords[i][0][0] == coords[j][-1][0]):
                    coords[i] = np.concatenate([coords[j], coords[i]])
                    for obj in [coords, stroke, fill]:
                        del obj[j]
                    f -= 1
                    match = True
                    break
                elif np.all(coords[i][-1][0] == coords[j][0][0]):
                    coords[i] = np.concatenate([coords[i], coords[j]])
                    for obj in [coords, stroke, fill]:
                        del obj[j]
                    f -= 1
                    match = True
                    break
                else:
                    j += 1
            else:
                j += 1
        if not match:
            i += 1

    return coords, stroke, fill

def check_areas(coords, stroke, fill, thresh=1, node_thresh=2):
    areas = [
        cv.contourArea(c) for c in coords]
    [coords, stroke, fill] = [
        [
            obj[i] for i in range(len(coords))
            if areas[i] > thresh and len(obj[i]) > node_thresh]
        for obj in [coords, stroke, fill]]
    return coords, stroke, fill

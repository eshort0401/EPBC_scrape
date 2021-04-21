import re
import numpy as np
from scipy.spatial.distance import cdist
import cv2 as cv

def convert_path_coords(path_list, shape, thresh):
    path_coords = []
    stroke = []
    fill = []
    obj_list = []
    for p in path_list:
        coords = re.sub(
            'c (-*[0-9]*\.*[0-9]+) (-*[0-9]*\.*[0-9]+) '
            + '(-*[0-9]*\.*[0-9]+) (-*[0-9]*\.*[0-9]+) '
            + '(-*[0-9]*\.*[0-9]+) (-*[0-9]*\.*[0-9]+)',
            r'l \5 \6', p['d'].lower()
        )
        has_z = re.search('(Z\s*)$', coords)
        coords = re.split('[a-zA-Z]', coords)
        coords.remove('')
        regex = re.compile(' +')
        coords = [c for c in coords if not regex.fullmatch(c)]
        coords = [
            re.sub('([0-9|.])( )(-|.|[0-9])', r'\1,\3', t).split(',')
            for t in coords
        ]
        if has_z:
            coords += coords[0]
        coords = np.array(coords).astype(float)
        if 0 < np.linalg.norm(coords[-1]-coords[0]) <= 5:
            coords = np.append(coords, [coords[0]], axis=0)

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
        area = cv.contourArea(new_coords)
        if .75*shape[0]*shape[1] >= area >= thresh*shape[0]*shape[1]:
            path_coords.append(new_coords)
            obj_list.append(p)
            try:
                stroke.append(p['stroke'])
            except:
                stroke.append('none')
            try:
                fill.append(p['fill'])
            except:
                fill.append('none')

    return path_coords, stroke, fill, obj_list

def crop_coords(coords, shape):
    coords[:,0][coords[:,0] >= shape[1]] = shape[1]-1
    coords[:,0][coords[:,0] < 0] = 0
    coords[:,1][coords[:,1] >= shape[0]] = shape[0]-1
    coords[:,1][coords[:,1] < 0] = 0
    return coords

def convert_tspan_coords(tspan_list, shape):
    tspan_coords = []
    [x, y] = [
        [t[c].split(' ') for t in tspan_list] for c in ['x', 'y']
    ]
    for i in range(len(x)):
        if len(x[i])==1:
            x[i] = x[i]*len(y[i])
        if len(y[i])==1:
            y[i] = y[i]*len(x[i])

    coords = [
        np.array(
            [x[i], y[i], np.ones(len(x[i]))]
        ).astype(float)
        for i in range(len(x))
    ]

    for i in range(len(tspan_list)):
        p = tspan_list[i].parent
        transform = convert_transform(p['transform'])
        new_coords = (np.matmul(transform,coords[i])[0:2]).T
        new_coords = np.around(new_coords).astype(int)
        new_coords = crop_coords(new_coords, shape)
        tspan_coords.append(
            new_coords.reshape([new_coords.shape[0],1,new_coords.shape[1]])
        )
    return tspan_coords

def convert_use_coords(use_list, soup_tap, shape, thresh):

    use_coords = []
    stroke = []
    fill = []
    obj_list = []
    for i in range(len(use_list)):

        p = soup_tap.find(
            'symbol', id=use_list[i]['xlink:href'][1:]
        ).path

        transform = convert_transform(use_list[i]['transform'])
        coords = re.sub(
            'c (-*[0-9]*\.*[0-9]+) (-*[0-9]*\.*[0-9]+) '
            + '(-*[0-9]*\.*[0-9]+) (-*[0-9]*\.*[0-9]+) '
            + '(-*[0-9]*\.*[0-9]+) (-*[0-9]*\.*[0-9]+)',
            r'l \5 \6', p['d'].lower()
        )
        coords = re.split('[a-zA-Z]', coords)
        coords.remove('')
        regex = re.compile(' +')
        coords = [c for c in coords if not regex.fullmatch(c)]
        coords = [
            re.sub('([0-9|.])( )(-|.|[0-9])', r'\1,\3', t).split(',')
            for t in coords
        ]
        coords = np.array(coords).astype(float)
        coords = np.append(
            coords, values=np.ones([len(coords),1]), axis=1
        )
        new_coords = (np.matmul(transform,coords.T)[0:2]).T
        new_coords = np.around(new_coords).astype(int)
        new_coords = crop_coords(new_coords, shape)
        new_coords = new_coords.reshape(
            [new_coords.shape[0],1,new_coords.shape[1]]
        )
        area = cv.contourArea(new_coords)
        if area >= thresh*shape[0]*shape[1]:
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
            transform_string.replace('matrix(', '').replace(')', '')
        )
    ).astype(float)
    transform = transform.reshape([3,2]).T
    transform = transform.tolist()
    transform.append([0,0,1])
    transform = np.array(transform)
    return transform

def get_nearest_text(leg_coords, lt_coords):
    closest_t = []
    for lc in leg_coords:
        distances=[]
        for tc in lt_coords:
        # Assume text likely beside icon, so penalise vertical distances
            distances.append(
                np.min(
                    cdist(
                        lc.squeeze(axis=1), tc.squeeze(axis=1),
                        'euclidean', w=[1, 4]
                    )
                )
            )
        closest_t.append(np.argmin(np.array(distances)))
    return closest_t

def get_leg_text(closest_t, svg_leg_text):
    leg_text = []
    for ind in closest_t:
        cond = (svg_leg_text[ind].parent.parent.name == 'g')
        cond *= (svg_leg_text[ind].parent.parent.has_attr('clip-path'))
        if cond:
            leg_text.append(svg_leg_text[ind].parent.parent.get_text())
        else:
            leg_text.append(svg_leg_text[ind].parent.get_text())

    leg_text = [re.sub('(\n)|!', ' ', t) for t in leg_text]
    leg_text = [re.sub('[ ]{2,}', ' ', t) for t in leg_text]
    leg_text = [re.sub('(^[ ]+)|([ ]+$)', '', t) for t in leg_text]
    return leg_text

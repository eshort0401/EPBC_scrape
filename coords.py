import numpy as np
import gui
import tkinter as tk

def evaluate_paraboloid(x, y, A, coeff):
    c = copy.deepcopy(coeff)
    x = np.array(x)
    y = np.array(y)
    for i in range(len(x.shape)):
        c = np.expand_dims(c, axis=1)
    return (c*A(x,y)).sum(axis=0)

def get_coords(base_dir, sub_dir, master, im1):

    try:
        with open(base_dir + sub_dir + '/coord_dict.json', 'r') as f:
            coord_dict = json.load(f)
    except:
        coord_dict = {}
    map_templates = [int(n) for n in list(coord_dict.keys())]

    get_coords_win = tk.Toplevel(master)
    get_coords_win.attributes('-zoomed', True)
    get_coords_app = gui.Choose_Map_Template(
        master, map_templates, page_num, base_dir + sub_dir + '/pages/',
        title = 'Choose a map template'
    )

    if get_coords_app.v.get() >= 0:
        t_page_num = map_templates[get_coords_app.v.get()]

        if len(np.array(coord_dict[str(t_page_num)][0])) <= 7:
            c_lon = np.array(coord_dict[str(t_page_num)][0])
            c_lat = np.array(coord_dict[str(t_page_num)][1])

            if len(c_lon) == 3:
                A = lambda x,y: np.array([x*0+1, x, y])
            elif len(c_lon) == 6:
                A = lambda x,y: np.array([x*0+1, x, y, x**2, x*y, y**2])
            else:
                A = None

            x = np.arange(im1.shape[1])/im1.shape[1]
            y = np.arange(im1.shape[0])/im1.shape[0]
            XX, YY = np.meshgrid(x, y)

            LON = np.round(evaluate_paraboloid(XX, YY, c_lon), 6)
            LAT = np.round(evaluate_paraboloid(XX, YY, c_lat), 6)
        else:
            LON = np.array(coord_dict[str(t_page_num)][0])
            LAT = np.array(coord_dict[str(t_page_num)][1])

    elif get_coords_app.v.get() == -1:
        json_files = glob.glob(base_dir + sub_dir + '/JSON/edited/*.json')
        json_names = [j.split('/')[-1].split('.')[0] for j in json_files]

        path = base_dir + sub_dir + '/pages/' + file_name

        choose_points_win = tk.Toplevel(master)
        choose_points_win.attributes('-zoomed', True)
        choose_points_app = gui.Choose_Points(
            master, im1, text_list = json_names
        )
        root.mainloop()

        points = choose_points_app.points
        names = choose_points_app.names

        fig, ax = plt.subplots(1, figsize=(20,20))
        ax.imshow(im1)
        for i in range(len(points)):
            ax.plot(points[i][0], points[i][1], '.r', markersize=10)
            ax.text(
                points[i][0]+20, points[i][1]+12, names[i], color='r',
                fontsize=16
            )
            plt.tick_params(
                which='both', bottom=False, top=False, left=False, right=False,
                labelbottom=False, labelleft=False
            )
        fig.savefig(base_dir + sub_dir + '/' +str(page_num) + '/reference.png')

        if np.any([n not in json_names for n in names]):
            # approx_lon = input(
            #     'Enter approx. lon. of top left map corner in dec. degrees '
            #     + '(e.g. 150.12345678): '
            # )
            # approx_lon = float(approx_lon)

            approx_lon = tk.simpledialog.askstring(
                'Enter Approx. Lon.',
                'Enter approx. lon. of top left map corner in dec. degrees '
                + '(e.g. 150.12345678): '
            )
            approx_lon = float(approx_lon)


            approx_lat = tk.simpledialog.askstring(
                'Enter Approx. Lat.'
                'Enter approx. lat. of top left map corner in signed dec. degrees '
                + '(e.g. -25.12345678): '
            )
            approx_lat = float(approx_lat)

            approx_spread = tk.simpledialog.askstring(
                'Enter Approx. Width'
                'Enter approx. width of map in dec. degrees (e.g. 0.05): '
            )
            approx_spread = float(approx_spread)

            scaled_points = [
                (
                    approx_spread*x[0]/im1.shape[0] + approx_lon,
                    -approx_spread*x[1]/im1.shape[1] + approx_lat
                ) for x in points
            ]

        subprocess.run('rm -r ' + base_dir + sub_dir + '/JSON/raw', shell=True)
        subprocess.run('mkdir -p ' + base_dir + sub_dir + '/JSON/raw', shell=True)
        subprocess.run('mkdir -p ' + base_dir + sub_dir + '/JSON/edited', shell=True)

        if np.any([n not in json_names for n in names]) or not json_names:
            json_features = []
            for i in range(len(scaled_points)):
                json_feature = geojson.Feature(
                    geometry=geojson.Point(
                        scaled_points[i], precision=8, properties={'Name': names[i]}
                    )
                )
                json_features.append(json_feature)

            for i in range(len(json_features)):
                if names[i] not in json_names:
                    f = open(
                        base_dir + sub_dir + '/JSON/raw/' + names[i] + '.json',
                        'w'
                    )
                    f.write(
                        geojson.dumps(
                            json_features[i], sort_keys=True, indent=4
                        )
                    )
                    f.close()

            subprocess.run(
                'cp ' + base_dir + '/reference.qgs ' + base_dir
                + sub_dir + '/reference.qgs', shell=True
            )

            cmd=(
                'qgis --project ' + base_dir + sub_dir + '/reference.qgs '
                + base_dir + sub_dir + '/JSON/raw/*.json --extent {},{},{},{}'
            ).format(
                approx_lon,
                approx_lat+np.sign(approx_lat)*approx_spread,
                approx_lon+approx_spread,
                approx_lat-np.sign(approx_lat)*approx_spread,
            )
            subprocess.run(cmd, shell=True)

            subprocess.run(
                'mv ' + base_dir + sub_dir + '/JSON/raw/*json '
                + base_dir + sub_dir + '/JSON/edited/', shell=True
            )

        coords = []
        for i in range(len(points)):
            f = open(base_dir + sub_dir + '/JSON/edited/' + names[i] + '.json', 'r')
            coords.append(geojson.loads(f.read()))
            f.close()

        rows = np.array([point[1] for point in points])
        cols = np.array([point[0] for point in points])
        lons = np.array(
            [coord['geometry']['coordinates'][0] for coord in coords]
        )
        lats = np.array(
            [coord['geometry']['coordinates'][1] for coord in coords]
        )

        X = cols/im1.shape[1]
        Y = rows/im1.shape[0]

        if len(rows) < 3:
            A = None
        elif len(rows) < 7:
            A = lambda x,y: np.array([x*0+1, x, y])
        else:
            A = lambda x,y: np.array([x*0+1, x, y, x**2, x*y, y**2])

        c_lon, residuals, rank, s = np.linalg.lstsq(A(X,Y).T, lons, rcond=1e-8)
        c_lat, residuals, rank, s = np.linalg.lstsq(A(X,Y).T, lats, rcond=1e-8)

        def evaluate_paraboloid(x,y,coeff):
            c = copy.deepcopy(coeff)
            x = np.array(x)
            y = np.array(y)
            for i in range(len(x.shape)):
                c = np.expand_dims(c, axis=1)
            return (c*A(x,y)).sum(axis=0)

        x = np.arange(im1.shape[1])/im1.shape[1]
        y = np.arange(im1.shape[0])/im1.shape[0]
        XX, YY = np.meshgrid(x, y)

        LON = np.round(evaluate_paraboloid(XX, YY, c_lon), 6)
        LAT = np.round(evaluate_paraboloid(XX, YY, c_lat), 6)

        coord_dict[str(page_num)] = [c_lon.tolist(), c_lat.tolist()]
        with open(base_dir + sub_dir + '/coord_dict.json', 'w') as f:
            json.dump(coord_dict, f, indent=4)

    return LON, LAT

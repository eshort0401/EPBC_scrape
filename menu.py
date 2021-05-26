import tkinter as tk
from tkinter import ttk
import fitz
import subprocess
import numpy as np
import copy
from skimage.io import imread
import json, geojson
import glob
import copy

import gui
import coordinates

class Menu(ttk.Frame):
    def __init__(
            self, mainframe, filename=None,
            title='pymscrape version 0.1',
            base_dir = ('/home/student.unimelb.edu.au/shorte1/'
                + 'Documents/ACF_consulting')):
        ttk.Frame.__init__(self, master=mainframe)
        self.master.title(title)
        self.title = title
        self.file_path = filename
        self.base_dir = base_dir
        self.id_num = self.file_path.split('/')[-2]
        self.sub_dir = '/map_data/' + self.id_num
        self.dir = self.base_dir + self.sub_dir
        self.search_terms = ['legend']
        self.zoom_factor = 1
        self.filename = tk.StringVar()

        vbar = gui.AutoScrollbar(self.master, orient='vertical')
        hbar = gui.AutoScrollbar(self.master, orient='horizontal')
        vbar.grid(row=10, column=5, sticky='ns')
        hbar.grid(row=11, column=0, columnspan=4, sticky='we')

        self.console = tk.Listbox(
            self.master, width=87, xscrollcommand = hbar.set,
            yscrollcommand = vbar.set)
        self.console.grid(row=10, column=0, columnspan=4, sticky='w')
        self.linenumber = 1
        self.console.insert(
            self.linenumber,
            'Welcome to mscrape version 0.1. Copyright Ewan Short')
        self.linenumber += 1

        if not filename:
            self.filename.set('Click button to choose filename.')
        else:
            self.filename.set(filename.split('/')[-1])
            self.console.insert(
                self.linenumber,
                'File {} chosen.'.format(self.filename.get()))
            self.linenumber += 1

        self.page_num = -1
        self.page_label = tk.StringVar()
        self.page_label.set('Click button to choose page.')

        try:
            self.saved_pages = np.genfromtxt(
                self.dir + '/saved_pages.csv')
            self.saved_pages = self.saved_pages.astype(int).tolist()
        except:
            self.saved_pages = -1

        try:
            self.remaining_pages = np.genfromtxt(
                self.dir + '/remaining_pages.csv')
            self.remaining_pages = self.remaining_pages.astype(int).tolist()
        except:
            self.remaining_pages = copy.deepcopy(self.saved_pages)

        padding=10
        self.b_file = tk.Button(
            self.master, text="1. Choose File (f)", command=self.quit,
            padx=padding, pady=padding)
        self.b_file.grid(row=0, column=0, sticky='w')

        fn_label = tk.Label(self.master, textvariable=self.filename)
        fn_label.grid(row=0, column=1)

        self.b_search = tk.Button(
            self.master, text="2. Search for Maps (m)",
            command=self.search, padx=padding, pady=padding)
        self.b_search.grid(row=1, column=0, sticky='w')
        if not filename:
            self.b_search.state = tk.DISABLED

        self.search_label_var = tk.StringVar()
        if self.saved_pages == -1:
            self.search_label_var.set('Click to search for maps.')
        else:
            self.search_label_var.set(
                '{} pages with matching maps.'.format(
                    str(len(self.saved_pages))))
        search_label = tk.Label(
            self.master, textvariable=self.search_label_var)
        search_label.grid(row=1, column=1)

        self.b_page = tk.Button(
            self.master, text="3. Choose Page (p)",
            command=self.choose_page, padx=padding, pady=padding)
        self.b_page.grid(row=2, column=0, sticky='w')
        if self.saved_pages == -1:
            self.b_page['state'] = tk.DISABLED

        fn_label = tk.Label(self.master, textvariable=self.page_label)
        fn_label.grid(row=2, column=1)

        self.b_coords = tk.Button(
            self.master, text="4. Get Map Coordinates (m)",
            command=self.get_coords, padx=padding, pady=padding,
            state=tk.DISABLED)
        self.b_coords.grid(row=3, column=0, sticky='w')
        if self.page_num == -1:
            self.b_coords['state'] = tk.DISABLED

        self.b_svg = tk.Button(
            self.master, text="5. Scrape SVG Data (s)", command=self.quit,
            padx=padding, pady=padding, state=tk.DISABLED)
        self.b_svg.grid(row=4, column=0, sticky='w')

        self.b_bmp = tk.Button(
            self.master, text="6. Scrape Bitmap Image (b)", command=self.quit,
            padx=padding, pady=padding, state=tk.DISABLED)
        self.b_bmp.grid(row=5, column=0, sticky='w')

        self.b_done = tk.Button(
            self.master, text="Done (Enter)", command=self.quit,
            padx=padding, pady=padding)
        self.b_done.grid(row=6, column=0, sticky='w')

        self.master.bind('<Return>', self.quit)
        self.master.focus_set()

    def quit(self, event=None):
        self.master.destroy()

    def search(self, event=None):
        search_terms = tk.simpledialog.askstring(
            self.title, 'Input search terms as comma separated list.')
        self.search_terms += search_terms.split(',')

        subprocess.run('mkdir ' + self.dir, shell=True)
        subprocess.run('mkdir ' + self.dir + '/pages', shell=True)

        try:
            # Can seperate this as a function
            self.saved_pages=[]
            pdf_file = fitz.open(self.file_path)
            zoom_factor = 1
            for page_index in range(len(pdf_file)):
                page = pdf_file[page_index]
                page_size = page.mediabox_size[0]*page.mediabox_size[1]
                image_list = page.getImageList()
                image_sizes = np.array([im[2]*im[3] for im in image_list])
                save_page_image = [
                    t.strip() in page.getText().lower()
                    for t in self.search_terms]
                save_page_image = np.all(np.array(save_page_image))
                if save_page_image:
                    self.saved_pages.append(page.number)
                    mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
                    pix = page.get_pixmap(matrix=mat)
                    pix.writePNG(
                        self.dir
                        + '/pages/page-%i.png' % page.number)

                    self.console.insert(
                        self.linenumber,
                        'Map found on page {}.'.format(page.number))
                    self.linenumber += 1

            self.search_label_var.set(
                '{} pages with matching maps.'.format(
                    str(len(self.saved_pages))))
            np.savetxt(
                self.dir + "/saved_pages.csv",
                self.saved_pages, delimiter=",")
            self.b_page['state'] = tk.NORMAL

            try:
                self.remaining_pages = np.genfromtxt(
                    self.dir + '/remaining_pages.csv')
                self.remaining_pages = self.remaining_pages.astype(int).tolist()
            except:
                self.remaining_pages = copy.deepcopy(self.saved_pages)

        except:
            self.console.insert(self.linenumber, 'Could not open file.')
            self.linenumber += 1

    def choose_page(self, event=None):
        choose_page_win = tk.Toplevel(self.master)
        choose_page_win.attributes('-zoomed', True)
        choose_page_app = gui.Choose_Map(
            choose_page_win, self.remaining_pages,
            self.dir + '/pages/',
            title = 'Choose Map to Scrape')
        self.master.wait_window(choose_page_win)
        self.master.focus_set()
        self.page_num = self.remaining_pages[choose_page_app.v.get()]
        self.page_label.set('Page {} chosen.'.format(self.page_num))
        self.b_coords['state'] = tk.NORMAL
        self.console.insert(
                self.linenumber,
                'Page {} chosen.'.format(self.page_num))
        self.linenumber += 1

        subprocess.run(
            'mkdir ' + self.dir + '/' + str(self.page_num),
            shell=True)
        file_name = 'page-' + str(self.page_num) + '.png'
        self.im1 = imread(self.dir + '/pages/' + file_name)

    def get_coords(self, event=None):
        try:
            with open(
                self.dir
                + '/coord_dict.json', 'r') as f:
                coord_dict = json.load(f)
        except:
            coord_dict = {}
        map_templates = [int(n) for n in list(coord_dict.keys())]

        get_coords_win = tk.Toplevel(self.master)
        get_coords_win.attributes('-zoomed', True)
        get_coords_app = gui.Choose_Map_Template(
            get_coords_win, map_templates, self.page_num,
            self.dir + '/pages/',
            title = 'Choose a map template')
        self.master.wait_window(get_coords_win)
        self.master.focus_set()

        if get_coords_app.v.get() >= 0:
            t_page_num = map_templates[get_coords_app.v.get()]

            # Backward compatibility for old way of saving coordinates
            if len(np.array(coord_dict[str(t_page_num)][0])) <= 7:
                c_lon = np.array(coord_dict[str(t_page_num)][0])
                c_lat = np.array(coord_dict[str(t_page_num)][1])

                if len(c_lon) == 3:
                    A = lambda x,y: np.array([x*0+1, x, y])
                elif len(c_lon) == 6:
                    A = lambda x,y: np.array([x*0+1, x, y, x**2, x*y, y**2])
                else:
                    A = None

                x = np.arange(self.im1.shape[1])/self.im1.shape[1]
                y = np.arange(self.im1.shape[0])/self.im1.shape[0]
                XX, YY = np.meshgrid(x, y)
                LON = np.round(
                    coordinates.evaluate_paraboloid(XX, YY, c_lon), 6)
                LAT = np.round(
                    coordinates.evaluate_paraboloid(XX, YY, c_lat), 6)
            else:
                LON = np.array(coord_dict[str(t_page_num)][0])
                LAT = np.array(coord_dict[str(t_page_num)][1])

        elif get_coords_app.v.get() == -1:
            json_files = glob.glob(
                self.dir + '/JSON/edited/*.json')
            json_names = [j.split('/')[-1].split('.')[0] for j in json_files]
            path = self.dir + '/pages/' + self.filename.get()

            choose_points_win = tk.Toplevel(self.master)
            choose_points_win.attributes('-zoomed', True)
            choose_points_app = gui.Choose_Points(
                choose_points_win, self.im1, text_list = json_names)
            self.master.wait_window(choose_points_win)
            self.master.focus_set()

            points = choose_points_app.points
            names = choose_points_app.names

            ref_img_path = (
                self.dir + '/' + str(self.page_num)
                + '/reference.png')
            coordinates.save_reference_image(
                ref_img_path, self.im1, points, names)
            self.console.insert(
                self.linenumber,
                'Reference image saved {}.'.format(ref_img_path))
            self.linenumber += 1

            if np.any([n not in json_names for n in names]):
                scaled_points = coordinates.scale_points(self.im1, points)
            coordinates.create_JSON_dirs(self.base_dir, self.sub_dir)

            if np.any([n not in json_names for n in names]) or not json_names:
                json_features = []
                for i in range(len(scaled_points)):
                    json_feature = geojson.Feature(
                        geometry=geojson.Point(
                            scaled_points[i], precision=8,
                            properties={'Name': names[i]}))
                    json_features.append(json_feature)

                for i in range(len(json_features)):
                    if names[i] not in json_names:
                        f = open(
                            self.dir + '/JSON/raw/'
                            + names[i] + '.json', 'w')
                        f.write(
                            geojson.dumps(
                                json_features[i], sort_keys=True, indent=4))
                        f.close()

                subprocess.run(
                    'cp ' + self.base_dir + '/reference.qgs ' + self.base_dir
                    + self.sub_dir + '/reference.qgs', shell=True)

                cmd=(
                    'qgis --project ' + self.dir
                    + '/reference.qgs ' + self.dir
                    + '/JSON/raw/*.json ' + '--extent {},{},{},{}')
                cmd = cmd.format(
                    approx_lon, approx_lat+np.sign(approx_lat)*approx_spread,
                    approx_lon+approx_spread,
                    approx_lat-np.sign(approx_lat)*approx_spread)
                subprocess.run(cmd, shell=True)

                subprocess.run(
                    'mv ' + self.dir + '/JSON/raw/*json '
                    + self.dir + '/JSON/edited/',
                    shell=True)

            coords = []
            for i in range(len(points)):
                f = open(
                    self.dir
                    + '/JSON/edited/' + names[i] + '.json', 'r')
                coords.append(geojson.loads(f.read()))
                f.close()

            rows = np.array([point[1] for point in points])
            cols = np.array([point[0] for point in points])
            lons = np.array(
                [coord['geometry']['coordinates'][0] for coord in coords])
            lats = np.array(
                [coord['geometry']['coordinates'][1] for coord in coords])

            X = cols/self.im1.shape[1]
            Y = rows/self.im1.shape[0]

            if len(rows) < 3:
                A = None
            elif len(rows) < 7:
                A = lambda x,y: np.array([x*0+1, x, y])
            else:
                A = lambda x,y: np.array([x*0+1, x, y, x**2, x*y, y**2])

            c_lon, residuals, rank, s = np.linalg.lstsq(
                A(X,Y).T, lons, rcond=1e-8)
            c_lat, residuals, rank, s = np.linalg.lstsq(
                A(X,Y).T, lats, rcond=1e-8)

            x = np.arange(self.im1.shape[1])/self.im1.shape[1]
            y = np.arange(self.im1.shape[0])/self.im1.shape[0]
            XX, YY = np.meshgrid(x, y)

            self.LON = np.round(
                coordinates.evaluate_paraboloid(XX, YY, A, c_lon), 6)
            self.LAT = np.round(
                coordinates.evaluate_paraboloid(XX, YY, A, c_lat), 6)

            coord_dict[str(self.page_num)] = [c_lon.tolist(), c_lat.tolist()]
            with open(
                    self.dir
                    + '/coord_dict.json', 'w') as f:
                json.dump(coord_dict, f, indent=4)
        return

# Copyright Ewan Short. All rights reserved.
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, simpledialog
import fitz
import subprocess
import numpy as np
import copy
from skimage.io import imread
import json
import geojson
import glob
import os

import gui
import coordinates
import scrape_svg
import scrape_bmp
import pdf_analysis
from shell_tools import run_common_cmd, run_powershell_cmd


class Menu(ttk.Frame):
    def __init__(
            self, mainframe, filename=None,
            title='pymscrape v 0.1 Copyright Ewan Short All Rights Reserved',
            base_dir=('/home/student.unimelb.edu.au/shorte1/'
                      + 'Documents/ACF_consulting'),
            search_terms=['legend'], page_num=None, map_page_num=None,
            leg_names=None, im_leg=None, LON=None, LAT=None,
            pb_tl=None, pb_br=None, im1=None):

        ttk.Frame.__init__(self, master=mainframe)
        self.master.title(title)
        self.master.lift()
        self.title = title
        self.file_path = filename
        self.base_dir = base_dir
        if (self.base_dir[-1] == '/' or self.base_dir[-1] == '\\'):
            self.base_dir = self.base_dir[:-1]

        self.search_terms = search_terms
        self.zoom_factor = 1
        self.filename = tk.StringVar()

        vbar = gui.AutoScrollbar(self.master, orient='vertical')
        hbar = gui.AutoScrollbar(self.master, orient='horizontal')
        vbar.grid(row=10, column=5, sticky='ns')
        hbar.grid(row=11, column=0, columnspan=4, sticky='we')

        self.console = tk.Listbox(
            self.master, width=87, xscrollcommand=hbar.set,
            yscrollcommand=vbar.set)
        self.console.grid(row=10, column=0, columnspan=4, sticky='w')
        self.linenumber = 1
        self.console.insert(self.linenumber, 'Welcome to mscrape version 0.1.')
        self.linenumber += 1

        [
            self.page_num, self.map_page_num, self.leg_names, self.im_leg,
            self.im1, self.LAT, self.LON, self.pb_tl, self.pb_br] = [
            page_num, map_page_num, leg_names, im_leg, im1, LAT, LON,
            pb_tl, pb_br]

        if filename is None:
            self.filename.set('Click button to choose filename.')
            self.saved_pages = None
        else:
            self.filename.set(filename.split('/')[-1])
            self.console.insert(
                self.linenumber,
                'File {} chosen.'.format(self.filename.get()))
            self.linenumber += 1
            self.check_saved_pages()

        padding = 10
        self.b_file = tk.Button(
            self.master, text="1. Choose File (f)", command=self.choose_file,
            padx=padding, pady=padding)
        self.b_file.grid(row=0, column=0, sticky='w')

        self.fn_label = tk.Label(self.master, textvariable=self.filename)
        self.fn_label.grid(row=0, column=1)

        self.b_search = tk.Button(
            self.master, text="2. Search for Maps (m)",
            command=self.search, padx=padding, pady=padding)
        self.b_search.grid(row=1, column=0, sticky='w')

        self.search_label_var = tk.StringVar()
        if self.saved_pages is None:
            self.search_label_var.set('Click to search for maps.')
        else:
            self.search_label_var.set(
                '{} pages with matching maps.'.format(
                    str(len(self.saved_pages))))
        self.search_label = tk.Label(
            self.master, textvariable=self.search_label_var)
        self.search_label.grid(row=1, column=1)

        if filename is None:
            self.b_search['state'] = tk.DISABLED
            self.search_label.config(fg='#AAAAAA')

        self.b_page = tk.Button(
            self.master, text="3. Choose Page (p)",
            command=self.choose_page, padx=padding, pady=padding)
        self.b_page.grid(row=2, column=0, sticky='w')

        self.page_label_text = tk.StringVar()
        self.page_label_text.set('Click button to choose page.')
        self.page_label = tk.Label(
            self.master, textvariable=self.page_label_text)
        self.page_label.grid(row=2, column=1)

        if self.saved_pages is None:
            self.b_page['state'] = tk.DISABLED
            self.page_label.config(fg='#AAAAAA')

        self.b_coords = tk.Button(
            self.master, text="4. Get Map Coordinates (m)",
            command=self.get_coords, padx=padding, pady=padding)
        self.b_coords.grid(row=3, column=0, sticky='w')

        self.coords_label_text = tk.StringVar()
        self.coords_label_text.set(
            'Click button to generate physical coordinates.')
        self.coords_label = tk.Label(
            self.master, textvariable=self.coords_label_text)
        self.coords_label.grid(row=3, column=1)
        if self.page_num is None:
            self.b_coords['state'] = tk.DISABLED
            self.coords_label.config(fg='#AAAAAA')
        else:
            self.im1 = imread(
                self.dir + '/pages/' + 'page-' + str(self.page_num) + '.png')

        self.b_svg = tk.Button(
            self.master, text="5. Scrape SVG Data (s)", command=self.get_svg,
            padx=padding, pady=padding)
        self.b_svg.grid(row=4, column=0, sticky='w')

        self.svg_label_text = tk.StringVar()
        self.svg_label_text.set(
            'Click button to scrape SVG data.')
        self.svg_label = tk.Label(
            self.master, textvariable=self.svg_label_text)
        self.svg_label.grid(row=4, column=1)

        svg_dis_cond = (
            (self.page_num is None) or (self.im1 is None) or (self.LON is None)
            or (self.LAT is None) or (self.map_page_num is None))
        if svg_dis_cond:
            self.b_svg['state'] = tk.DISABLED
            self.svg_label.config(fg='#AAAAAA')

        self.b_bmp = tk.Button(
            self.master, text="6. Scrape Bitmap Image (b)",
            command=self.get_bmp, padx=padding, pady=padding)
        self.b_bmp.grid(row=5, column=0, sticky='w')

        self.bmp_label_text = tk.StringVar()
        self.bmp_label_text.set(
            'Click button to scrape BMP data.')
        self.bmp_label = tk.Label(
            self.master, textvariable=self.bmp_label_text)
        self.bmp_label.grid(row=5, column=1)

        bmp_dis_cond = (
            svg_dis_cond or (self.im_leg is None)
            or (self.pb_tl is None) or (self.pb_br is None))
        if bmp_dis_cond:
            self.b_bmp['state'] = tk.DISABLED
            self.bmp_label.config(fg='#AAAAAA')

        self.buttons = [
            self.b_file, self.b_search, self.b_page,
            self.b_coords, self.b_svg, self.b_bmp]

        self.b_done = tk.Button(
            self.master, text="Done (Enter)", command=self.quit,
            padx=padding, pady=padding)
        self.b_done.grid(row=6, column=0, sticky='w')

        self.master.bind('<Return>', self.quit)
        self.master.focus_set()

    def quit(self, event=None):
        self.master.destroy()

    def choose_file(self, event=None):
        self.file_path = filedialog.askopenfilename(
            initialdir=self.base_dir,
            title="Select PDF File",
            filetypes=(("PDF Files", "*.pdf"), ("All Files", "*.*")))
        self.filename.set(self.file_path.split('/')[-1])
        self.console.insert(
            self.linenumber,
            'File {} chosen.'.format(self.filename.get()))
        self.linenumber += 1
        self.b_search['state'] = tk.NORMAL
        self.search_label.config(fg='#000000')
        self.check_saved_pages()
        if not self.saved_pages:
            self.search_label_var.set('Click to search for maps.')
            self.b_page['state'] = tk.DISABLED
            self.page_label.config(fg='#AAAAAA')
        else:
            self.b_page['state'] = tk.NORMAL
            self.page_label.config(fg='#000000')
            self.search_label.config(fg='#000000')
            self.search_label_var.set(
                '{} pages with matching maps.'.format(
                    str(len(self.saved_pages))))
        self.page_label_text.set('Click button to choose page.')
        self.b_coords['state'] = tk.DISABLED
        self.coords_label.config(fg='#AAAAAA')
        self.coords_label_text.set(
            'Click button to generate physical coordinates.')
        self.b_svg['state'] = tk.DISABLED
        self.svg_label.config(fg='#AAAAAA')
        self.svg_label_text.set(
            'Click button to scrape SVG data.')
        self.b_bmp['state'] = tk.DISABLED
        self.bmp_label.config(fg='#AAAAAA')
        self.bmp_label_text.set('Click button to scrape BMP data.')
        return

    def check_saved_pages(self, event=None):
        self.id_num = self.file_path.split('/')[-2]
        self.sub_dir = '/map_data/' + self.id_num
        self.dir = self.base_dir + self.sub_dir

        try:
            self.saved_pages = np.genfromtxt(self.dir + '/saved_pages.csv')
            self.saved_pages = self.saved_pages.astype(int).tolist()
        except:
            self.saved_pages = None
        try:
            self.remaining_pages = np.genfromtxt(
                self.dir + '/remaining_pages.csv')
            self.remaining_pages = self.remaining_pages.astype(int).tolist()
        except:
            self.remaining_pages = copy.deepcopy(self.saved_pages)

    def search(self, event=None):

        self.search_label_var.set('Searching for maps. Please Wait.')
        self.b_search['state'] = tk.DISABLED
        self.fn_label.config(fg='#AAAAAA')
        self.b_file['state'] = tk.DISABLED
        self.b_page['state'] = tk.DISABLED
        self.page_label.config(fg='#AAAAAA')

        search_terms = simpledialog.askstring(
            self.title, 'Input search terms as comma separated list.',
            parent=self.master)
        self.search_terms += search_terms.split(',')
        self.search_terms = [
            t.strip() for t in self.search_terms if t != '' and t != ' ']

        run_common_cmd('mkdir ' + self.dir, self.base_dir)
        run_common_cmd('mkdir ' + self.dir + '/pages', self.base_dir)
        # try:
        # Can seperate this as a function
        self.saved_pages = []
        pdf_file = fitz.open(self.file_path)
        for page_index in range(len(pdf_file)):
            page = pdf_file[page_index]
            large_image, has_text, text_matches = pdf_analysis.detect_map(
                page, self.search_terms)
            if np.all(text_matches) and large_image:
                self.saved_pages.append(page.number)
                mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
                pix = page.get_pixmap(matrix=mat)
                pix.writePNG(
                    self.dir + '/pages/page-%i.png' % page.number)
                self.console.insert(
                    self.linenumber,
                    'Map found on page {}.'.format(page.number))
                self.linenumber += 1

        np.savetxt(
            self.dir + "/saved_pages.csv",
            self.saved_pages, delimiter=",")

        try:
            self.remaining_pages = np.genfromtxt(
                self.dir + '/remaining_pages.csv')
            self.remaining_pages = self.remaining_pages.astype(int)
            self.remaining_pages = self.remaining_pages.tolist()
        except:
            self.remaining_pages = copy.deepcopy(self.saved_pages)

        self.search_label_var.set(
            '{} pages with matching maps.'.format(
                str(len(self.saved_pages))))
        self.b_search['state'] = tk.NORMAL
        self.b_page['state'] = tk.NORMAL
        self.page_label.config(fg='#000000')
        self.page_label_text.set('Click button to choose page.')
        self.fn_label.config(fg='#000000')
        self.b_file['state'] = tk.NORMAL
        # except:
        #     self.console.insert(self.linenumber, 'Could not open file.')
        #     self.linenumber += 1

    def choose_page(self, event=None):
        choose_page_win = tk.Toplevel(self.master)
        if os.name == 'nt':
            choose_page_win.state('zoomed')
            choose_page_win.lift()
        else:
            choose_page_win.attributes('-zoomed', True)
        choose_page_app = gui.Choose_Map(
            choose_page_win, self.remaining_pages,
            self.dir + '/pages/', title='Choose Map to Scrape')
        self.master.wait_window(choose_page_win)
        self.master.focus_set()
        self.page_num = self.remaining_pages[choose_page_app.v.get()]
        self.page_label_text.set('Page {} chosen.'.format(self.page_num))
        self.console.insert(
            self.linenumber, 'Page {} chosen.'.format(self.page_num))
        self.linenumber += 1

        run_common_cmd(
            'mkdir ' + self.dir + '/' + str(self.page_num), self.base_dir)
        file_name = 'page-' + str(self.page_num) + '.png'
        self.im1 = imread(self.dir + '/pages/' + file_name)

        self.b_coords['state'] = tk.NORMAL
        self.coords_label.config(fg='#000000')
        self.coords_label_text.set(
            'Click button to generate physical coordinates.')
        self.page_label.config(fg='#000000')
        self.b_svg['state'] = tk.DISABLED
        self.svg_label.config(fg='#AAAAAA')
        self.svg_label_text.set(
            'Click button to scrape SVG data.')
        self.b_bmp['state'] = tk.DISABLED
        self.bmp_label.config(fg='#AAAAAA')
        self.bmp_label_text.set(
            'Click button to scrape BMP data.')

    def get_coords(self, event=None):
        try:
            with open(self.dir + '/coord_dict.json', 'r') as f:
                coord_dict = json.load(f)
        except:
            coord_dict = {}
        map_templates = [int(n) for n in list(coord_dict.keys())]

        get_coords_win = tk.Toplevel(self.master)
        if os.name == 'nt':
            get_coords_win.state('zoomed')
            get_coords_win.lift()
        else:
            get_coords_win.attributes('-zoomed', True)
        get_coords_app = gui.Choose_Map_Template(
            get_coords_win, map_templates, self.page_num,
            self.dir + '/pages/', title='Choose a map template')
        self.master.wait_window(get_coords_win)
        self.master.focus_set()

        if get_coords_app.v.get() >= 0:
            self.map_page_num = map_templates[get_coords_app.v.get()]

            # Backward compatibility for old way of saving coordinates
            if len(np.array(coord_dict[str(self.map_page_num)][0])) <= 7:
                c_lon = np.array(coord_dict[str(self.map_page_num)][0])
                c_lat = np.array(coord_dict[str(self.map_page_num)][1])

                if len(c_lon) == 3:
                    A = lambda x, y: np.array([x*0+1, x, y])
                elif len(c_lon) == 6:
                    A = lambda x, y: np.array([x*0+1, x, y, x**2, x*y, y**2])
                else:
                    A = None

                x = np.arange(self.im1.shape[1])/self.im1.shape[1]
                y = np.arange(self.im1.shape[0])/self.im1.shape[0]
                XX, YY = np.meshgrid(x, y)
                self.LON = np.round(
                    coordinates.evaluate_paraboloid(XX, YY, A, c_lon), 6)
                self.LAT = np.round(
                    coordinates.evaluate_paraboloid(XX, YY, A, c_lat), 6)
            else:
                self.LON = np.array(coord_dict[str(self.map_page_num)][0])
                self.LAT = np.array(coord_dict[str(self.map_page_num)][1])

            self.coords_label_text.set(
                'Map Template {} Chosen'.format(self.map_page_num))

        elif get_coords_app.v.get() == -1:
            self.map_page_num = self.page_num
            json_files = glob.glob(
                self.dir + '/JSON/edited/*.json')
            json_names = [
                j.split('/')[-1].split('\\')[-1].split('.')[0]
                for j in json_files]

            choose_points_win = tk.Toplevel(self.master)
            if os.name == 'nt':
                choose_points_win.state('zoomed')
                choose_points_win.lift()
            else:
                choose_points_win.attributes('-zoomed', True)
            choose_points_app = gui.Choose_Points(
                choose_points_win, self.im1, text_list=json_names)
            self.master.wait_window(choose_points_win)
            self.master.focus_set()

            points = choose_points_app.points
            names = choose_points_app.names
            names = [n.replace(' ', '_') for n in names]

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
                (
                    scaled_points, approx_lon,
                    approx_lat, approx_spread) = coordinates.scale_points(
                        self.im1, points)
            coordinates.create_JSON_dirs(self.dir)

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
                            self.dir + '/JSON/raw/' + names[i] + '.json', 'w')
                        f.write(geojson.dumps(
                            json_features[i], sort_keys=True, indent=4))
                        f.close()

                run_common_cmd(
                    'cp ' + self.base_dir + '/reference.qgs ' + self.dir
                    + '/reference.qgs', self.base_dir)

                if os.name == 'nt':
                    cmd = 'qgis-ltr-bin-g7 --project ' + self.dir
                    cmd += '/reference.qgs '
                    for name in names:
                        if name not in json_names:
                            cmd += self.dir + '/JSON/raw/{}.json '.format(name)
                    cmd += '--extent {},{},{},{}'
                    cmd = cmd.format(
                        approx_lon,
                        approx_lat+np.sign(approx_lat)*approx_spread,
                        approx_lon+approx_spread,
                        approx_lat-np.sign(approx_lat)*approx_spread)
                    subprocess.run(cmd, shell=True)

                    cmd = 'move-item -path {}/JSON/raw/*json '.format(self.dir)
                    cmd += '-destination {}/JSON/edited/'.format(self.dir)
                    run_powershell_cmd(cmd, self.base_dir)
                else:
                    cmd = (
                        'qgis --project ' + self.dir
                        + '/reference.qgs ' + self.dir
                        + '/JSON/raw/*.json ' + '--extent {},{},{},{}')
                    cmd = cmd.format(
                        approx_lon,
                        approx_lat+np.sign(approx_lat)*approx_spread,
                        approx_lon+approx_spread,
                        approx_lat-np.sign(approx_lat)*approx_spread)
                    run_common_cmd(cmd, self.base_dir)

                    subprocess.run(
                        'mv ' + self.dir + '/JSON/raw/*json '
                        + self.dir + '/JSON/edited/', shell=True)

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
                A(X, Y).T, lons, rcond=1e-8)
            c_lat, residuals, rank, s = np.linalg.lstsq(
                A(X, Y).T, lats, rcond=1e-8)

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

            self.coords_label_text.set(
                'New Template Created from Page {}'.format(self.page_num))

        self.b_svg['state'] = tk.NORMAL
        self.svg_label.config(fg='#000000')
        self.svg_label_text.set(
            'Click button to scrape SVG data.')
        self.b_bmp['state'] = tk.DISABLED
        self.bmp_label.config(fg='#AAAAAA')
        self.bmp_label_text.set(
            'Click button to scrape BMP data.')

        return

    def get_svg(self, event=None):

        self.console.insert(
            self.linenumber,
            'Scraping SVG data. This may take a few minutes. Please Wait.')
        self.linenumber += 1

        self.svg_label_text.set('Working. Please Wait.')
        self.disable_buttons()

        self.leg_names, self.im_leg, self.pb_tl, self.pb_br = scrape_svg.scrape_svg(
            self.file_path, self.page_num, self.im1,
            self.base_dir, self.sub_dir, self.master,
            self.LON, self.LAT, self.zoom_factor)

        self.bmp_label.config(fg='#000000')
        self.svg_label_text.set('KML file saved.')
        self.enable_buttons()

        self.console.insert(
            self.linenumber,
            'KML file saved to {}/{}.'.format(self.dir, self.page_num))
        self.linenumber += 1

        return

    def get_bmp(self, event=None):

        self.disable_buttons()
        self.console.insert(
            self.linenumber, 'Scraping BMP data. Please Wait.')
        self.linenumber += 1

        self.bmp_label_text.set('Working. Please Wait.')

        scrape_bmp.scrape_bmp(
            self.master, self.file_path, self.page_num,
            self.base_dir, self.sub_dir, self.leg_names, self.im_leg,
            self.LON, self.LAT, self.pb_tl, self.pb_br)

        self.remaining_pages.remove(self.page_num)
        np.savetxt(
            self.dir + "/remaining_pages.csv",
            self.remaining_pages, delimiter=",")

        self.b_bmp['state'] = tk.NORMAL
        self.bmp_label.config(fg='#000000')
        self.bmp_label_text.set('KML file saved.')

        self.enable_buttons()
        self.console.insert(
            self.linenumber,
            'KML file saved to {}/{}.'.format(self.dir, self.page_num))
        self.linenumber += 1

        return

    def disable_buttons(self, event=None):

        for b in self.buttons:
            b['state'] = tk.DISABLED

    def enable_buttons(self, event=None):

        for b in self.buttons:
            b['state'] = tk.NORMAL

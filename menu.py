import tkinter as tk
from tkinter import ttk
import fitz
import subprocess
import numpy as np
import gui
import copy

class Menu(ttk.Frame):
    def __init__(
        self, mainframe, filename=None,
        title='pymscrape version 0.1',
        base_dir = '/home/student.unimelb.edu.au/shorte1/Documents/ACF_consulting'
    ):
        ttk.Frame.__init__(self, master=mainframe)
        self.title = title
        self.file_path = filename
        self.base_dir = base_dir
        self.master.title(title)
        self.id_num = self.file_path.split('/')[-2]
        self.sub_dir = '/map_data/' + self.id_num
        self.zoom_factor = 1

        vbar = gui.AutoScrollbar(self.master, orient='vertical')
        hbar = gui.AutoScrollbar(self.master, orient='horizontal')
        vbar.grid(row=10, column=5, sticky='ns')
        hbar.grid(row=11, column=0, columnspan=4, sticky='we')
        self.console = tk.Listbox(
            self.master, width=87, xscrollcommand = hbar.set,
            yscrollcommand = vbar.set
        )
        self.console.grid(row=10, column=0, columnspan=4, sticky='w')
        self.linenumber = 1
        self.console.insert(
            self.linenumber,
            'Welcome to mscrape version 0.1. Copyright Ewan Short'
        )
        self.linenumber += 1
        self.search_terms = ['legend']
        self.filename = tk.StringVar()
        if not filename:
            self.filename.set('Click button to choose filename.')
        else:
            self.filename.set(filename.split('/')[-1])
            self.console.insert(
                self.linenumber,
                'File {} chosen.'.format(self.filename.get())
            )
            self.linenumber += 1

        self.page_num = -1

        self.page_label = tk.StringVar()
        self.page_label.set('Click button to choose page.')

        try:
            self.saved_pages = np.genfromtxt(
                self.base_dir + self.sub_dir + '/saved_pages.csv'
            ).astype(int).tolist()
        except:
            self.saved_pages = -1

        try:
            self.remaining_pages = np.genfromtxt(
                self.base_dir + self.sub_dir + '/remaining_pages.csv'
            ).astype(int).tolist()
        except:
            self.remaining_pages = copy.deepcopy(self.saved_pages)

        padding=10
        self.b_file = tk.Button(
            self.master, text="1. Choose File (f)", command=self.quit,
            padx=padding, pady=padding
        )
        self.b_file.grid(row=0, column=0, sticky='w')

        fn_label = tk.Label(self.master, textvariable=self.filename)
        fn_label.grid(row=0, column=1)

        self.b_search = tk.Button(
            self.master, text="2. Search for Maps (m)",
            command=self.search, padx=padding, pady=padding
        )
        self.b_search.grid(row=1, column=0, sticky='w')
        if not filename:
            self.b_search.state = tk.DISABLED

        self.search_label_var = tk.StringVar()
        if self.saved_pages == -1:
            self.search_label_var.set('Click to search for maps.')
        else:
            self.search_label_var.set(
                '{} pages with matching maps.'.format(
                    str(len(self.saved_pages))
                )
            )
        search_label = tk.Label(
            self.master, textvariable=self.search_label_var
        )
        search_label.grid(row=1, column=1)

        self.b_page = tk.Button(
            self.master, text="3. Choose Page (p)",
            command=self.choose_page, padx=padding, pady=padding
        )
        self.b_page.grid(row=2, column=0, sticky='w')
        if self.saved_pages == -1:
            self.b_page['state'] = tk.DISABLED

        fn_label = tk.Label(self.master, textvariable=self.page_label)
        fn_label.grid(row=2, column=1)

        self.b_coords = tk.Button(
            self.master, text="4. Get Map Coordinates (m)", command=self.quit,
            padx=padding, pady=padding, state=tk.DISABLED
        )
        self.b_coords.grid(row=3, column=0, sticky='w')
        if self.page_num == -1:
            self.b_coords['state'] = tk.DISABLED

        self.b_svg = tk.Button(
            self.master, text="5. Scrape SVG Data (s)", command=self.quit,
            padx=padding, pady=padding, state=tk.DISABLED
        )
        self.b_svg.grid(row=4, column=0, sticky='w')

        self.b_bmp = tk.Button(
            self.master, text="6. Scrape Bitmap Image (b)", command=self.quit,
            padx=padding, pady=padding, state=tk.DISABLED
        )
        self.b_bmp.grid(row=5, column=0, sticky='w')

        self.b_done = tk.Button(
            self.master, text="Done (Enter)", command=self.quit,
            padx=padding, pady=padding
        )
        self.b_done.grid(row=6, column=0, sticky='w')

        self.master.bind('<Return>', self.quit)
        self.master.focus_set()

    def quit(self, event=None):
        self.master.destroy()

    def search(self, event=None):
        search_terms = tk.simpledialog.askstring(
            self.title, 'Input search terms as comma separated list.'
        )
        self.search_terms = search_terms.split(',')

        subprocess.run(
            'mkdir ' + self.base_dir + '/map_data/' + self.id_num,
            shell=True
        )
        subprocess.run(
            'mkdir ' + self.base_dir + '/map_data/' + self.id_num + '/pages',
            shell=True
        )

        try:
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
                    for t in self.search_terms
                ]
                save_page_image = np.all(np.array(save_page_image))
                if save_page_image:
                    self.saved_pages.append(page.number)

                    mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
                    pix = page.get_pixmap(matrix=mat)
                    pix.writePNG(
                        self.base_dir + self.sub_dir + '/pages/page-%i.png' % page.number
                    )

                    self.console.insert(
                        self.linenumber,
                        'Map found on page {}.'.format(page.number)
                    )
                    self.linenumber += 1

            self.search_label_var.set(
                '{} pages with matching maps.'.format(
                    str(len(self.saved_pages))
                )
            )

            np.savetxt(
                self.base_dir + self.sub_dir + "/saved_pages.csv",
                self.saved_pages, delimiter=","
            )

            self.b_page['state'] = tk.NORMAL

            try:
                self.remaining_pages = np.genfromtxt(
                    self.base_dir + self.sub_dir + '/remaining_pages.csv'
                ).astype(int).tolist()
            except:
                self.remaining_pages = copy.deepcopy(self.saved_pages)

        except:
            self.console.insert(
                self.linenumber,
                'Could not open file.'
            )
            self.linenumber += 1

    def choose_page(self, event=None):
        choose_page_win = tk.Toplevel(self.master)
        choose_page_win.attributes('-zoomed', True)
        choose_page_app = gui.Choose_Map(
            choose_page_win, self.remaining_pages,
            self.base_dir + self.sub_dir + '/pages/',
            title = 'Choose Map to Scrape'
        )
        self.master.wait_window(choose_page_win)
        self.master.focus_set()
        self.page_num = self.remaining_pages[choose_page_app.v.get()]
        self.page_label.set('Page {} chosen.'.format(self.page_num))
        self.b_coords['state'] = tk.NORMAL
        self.console.insert(
                self.linenumber,
                'Page {} chosen.'.format(self.page_num)
            )
        self.linenumber += 1

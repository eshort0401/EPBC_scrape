import copy

import tkinter as tk
from tkinter import ttk
from tkinter.simpledialog import askstring

from PIL import Image, ImageTk

import numpy as np
import cv2 as cv
import random

# Base tkinter scroll/zoom class based on
# https://stackoverflow.com/questions/41656176/tkinter-canvas-zoom-move-pan
class AutoScrollbar(ttk.Scrollbar):
    ''' A scrollbar that hides itself if it's not needed.
        Works only if you use the grid geometry manager '''
    def set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            self.grid_remove()
        else:
            self.grid()
            ttk.Scrollbar.set(self, lo, hi)

    def pack(self, **kw):
        raise tk.TclError('Cannot use pack with this widget')

    def place(self, **kw):
        raise tk.TclError('Cannot use place with this widget')

class Zoom_Scroll(ttk.Frame):
    ''' Advanced zoom of the image '''
    def __init__(self, mainframe, image, title='Zoom and Scroll'):
        ''' Initialize the main Frame '''
        ttk.Frame.__init__(self, master=mainframe)
        self.master.title(title)
        # Buttons
        b_done = tk.Button(
            self.master, text="Done (Enter)", command=self.quit
        )
        b_done.grid(row=0, column=0, sticky='w')
        c = 10
        # Vertical and horizontal scrollbars for canvas
        vbar = AutoScrollbar(self.master, orient='vertical')
        hbar = AutoScrollbar(self.master, orient='horizontal')
        vbar.grid(row=1, column=c, sticky='ns')
        hbar.grid(row=2, column=0, columnspan=c, sticky='we')
        # Create canvas and put image on it
        self.canvas = tk.Canvas(
            self.master, highlightthickness=0,
            xscrollcommand=hbar.set, yscrollcommand=vbar.set
        )
        self.canvas.grid(row=1, column=0, columnspan=c, sticky='nswe')
        self.canvas.update()  # wait till canvas is created
        vbar.configure(command=self.scroll_y)  # bind scrollbars to the canvas
        hbar.configure(command=self.scroll_x)
        # Make the canvas expandable
        self.master.rowconfigure(1, weight=1)
        [self.master.columnconfigure(i, weight=1) for i in range(c)]
        # Bind events to the Canvas
        self.canvas.bind('<Configure>', self.show_image)  # canvas is resized
        self.canvas.bind('<ButtonPress-1>', self.move_from)
        self.canvas.bind('<B1-Motion>',     self.move_to)
        self.canvas.bind('<MouseWheel>', self.wheel)  # with Windows and MacOS, but not Linux
        self.canvas.bind('<Button-5>',   self.wheel)  # only with Linux, wheel scroll down
        self.canvas.bind('<Button-4>',   self.wheel)  # only with Linux, wheel scroll up
        self.canvas.bind('<Return>', self.quit)
        self.canvas.focus_set()

        self.image = Image.fromarray(image)
        self.width, self.height = self.image.size
        self.imscale = 1.0  # scale for the canvaas image
        self.delta = 1.3  # zoom magnitude
        # Put image into container rectangle and use it to set proper coordinates to the image
        self.container = self.canvas.create_rectangle(0, 0, self.width, self.height, width=0)
        self.show_image()

    def quit(self, event=None):
        self.master.destroy()

    def scroll_y(self, *args, **kwargs):
        ''' Scroll canvas vertically and redraw the image '''
        self.canvas.yview(*args, **kwargs)  # scroll vertically
        self.show_image()  # redraw the image

    def scroll_x(self, *args, **kwargs):
        ''' Scroll canvas horizontally and redraw the image '''
        self.canvas.xview(*args, **kwargs)  # scroll horizontally
        self.show_image()  # redraw the image

    def move_from(self, event):
        ''' Remember previous coordinates for scrolling with the mouse '''
        self.canvas.scan_mark(event.x, event.y)

    def move_to(self, event):
        ''' Drag (move) canvas to the new position '''
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        self.show_image()  # redraw the image

    def wheel(self, event):
        ''' Zoom with mouse wheel '''
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        bbox = self.canvas.bbox(self.container)  # get image area
        if bbox[0] < x < bbox[2] and bbox[1] < y < bbox[3]: pass  # Ok! Inside the image
        else: return  # zoom only inside image area
        scale = 1.0
        # Respond to Linux (event.num) or Windows (event.delta) wheel event
        if event.num == 5 or event.delta == -120:  # scroll down
            i = min(self.width, self.height)
            if int(i * self.imscale) < 30: return  # image is less than 30 pixels
            self.imscale /= self.delta
            scale        /= self.delta
        if event.num == 4 or event.delta == 120:  # scroll up
            i = min(self.canvas.winfo_width(), self.canvas.winfo_height())
            if i < self.imscale: return  # 1 pixel is bigger than the visible area
            self.imscale *= self.delta
            scale        *= self.delta
        self.canvas.scale('all', x, y, scale, scale)  # rescale all canvas objects
        self.show_image()

    def get_coords(self, x, y):
        bbox = self.canvas.bbox(self.container)  # get image area
        x_plot = self.canvas.canvasx(0) + x
        y_plot = self.canvas.canvasy(0) + y
        x_true = (x_plot - bbox[0])/self.imscale
        y_true = (y_plot - bbox[1])/self.imscale
        return x_true, y_true, x_plot, y_plot

    def get_plot_coords(self, x_true, y_true):
        bbox = self.canvas.bbox(self.container)
        x_plot = self.imscale*x_true + bbox[0]
        y_plot = self.imscale*y_true + bbox[1]
        return x_plot, y_plot

    def show_image(self, event=None):
        ''' Show image on the Canvas '''
        bbox1 = self.canvas.bbox(self.container)  # get image area
        # Remove 1 pixel shift at the sides of the bbox1
        bbox1 = (bbox1[0] + 1, bbox1[1] + 1, bbox1[2] - 1, bbox1[3] - 1)
        bbox2 = (self.canvas.canvasx(0),  # get visible area of the canvas
                 self.canvas.canvasy(0),
                 self.canvas.canvasx(self.canvas.winfo_width()),
                 self.canvas.canvasy(self.canvas.winfo_height()))
        bbox = [min(bbox1[0], bbox2[0]), min(bbox1[1], bbox2[1]),  # get scroll region box
                max(bbox1[2], bbox2[2]), max(bbox1[3], bbox2[3])]
        if bbox[0] == bbox2[0] and bbox[2] == bbox2[2]:  # whole image in the visible area
            bbox[0] = bbox1[0]
            bbox[2] = bbox1[2]
        if bbox[1] == bbox2[1] and bbox[3] == bbox2[3]:  # whole image in the visible area
            bbox[1] = bbox1[1]
            bbox[3] = bbox1[3]
        self.canvas.configure(scrollregion=bbox)  # set scroll region
        x1 = max(bbox2[0] - bbox1[0], 0)  # get coordinates (x1,y1,x2,y2) of the image tile
        y1 = max(bbox2[1] - bbox1[1], 0)
        x2 = min(bbox2[2], bbox1[2]) - bbox1[0]
        y2 = min(bbox2[3], bbox1[3]) - bbox1[1]
        if int(x2 - x1) > 0 and int(y2 - y1) > 0:  # show image if it in the visible area
            x = min(int(x2 / self.imscale), self.width)   # sometimes it is larger on 1 pixel...
            y = min(int(y2 / self.imscale), self.height)  # ...and sometimes not
            image = self.image.crop((int(x1 / self.imscale), int(y1 / self.imscale), x, y))
            imagetk = ImageTk.PhotoImage(image.resize((int(x2 - x1), int(y2 - y1))))
            imageid = self.canvas.create_image(max(bbox2[0], bbox1[0]), max(bbox2[1], bbox1[1]),
                                               anchor='nw', image=imagetk)
            self.canvas.lower(imageid)  # set image into background
            self.canvas.imagetk = imagetk  # keep an extra reference to prevent garbage-collection

class Get_Legend_Box(Zoom_Scroll):
    def __init__(
        self, mainframe, image,
        title='Right click to select top left and botton '
        + 'right corners of legend box.'
    ):
        Zoom_Scroll.__init__(self, mainframe, image, title=title)

        b_delete = tk.Button(
            self.master, text="Delete Box (d)", command=self.delete_box
        )
        b_delete.grid(row=0, column=1)

        self.p1 = None
        self.p2 = None
        self.box_r = None
        self.p1_r = None
        self.p2_r = None

        self.canvas.bind("<Button 3>", self.draw_box)
        self.canvas.bind('<Return>', self.quit)
        self.canvas.bind('<d>', self.delete_box)
        self.canvas.focus_set()

    def delete_box(self, event=None):
        [
            self.canvas.delete(obj)
            for obj in [self.box_r, self.p1_r, self.p2_r]
        ]
        self.p1 = None
        self.p2 = None
        self.box_r = None

    def draw_box(self, event):

        x, y, x_plot, y_plot = self.get_coords(event.x, event.y)
        if not self.p1:
            self.canvas.delete(self.p1_r)
            self.p1 = [x, y]
            self.p1_r = self.canvas.create_rectangle(
                x_plot-2*self.imscale, y_plot-2*self.imscale,
                x_plot+2*self.imscale, y_plot+2*self.imscale,
                width=1, fill='red', outline='red'
            )
        elif not self.p2:
            if (x > self.p1[0]) and (y > self.p1[1]):
                self.canvas.delete(self.p2_r)
                self.p2 = [x, y]
                self.p2_r = self.canvas.create_rectangle(
                    x_plot-2*self.imscale, y_plot-2*self.imscale,
                    x_plot+2*self.imscale, y_plot+2*self.imscale,
                    width=1, fill='red', outline='red'
                )
                p1_plot = self.get_plot_coords(self.p1[0], self.p1[1])
                self.box_r = self.canvas.create_rectangle(
                    p1_plot[0], p1_plot[1], x_plot, y_plot,
                    width=1, outline='red'
                )
        else:
            [
                self.canvas.delete(obj)
                for obj in [self.box_r, self.p1_r, self.p2_r]
            ]
            self.p1 = None
            self.p2 = None
            self.box_r = None

class Choose_Points(Zoom_Scroll):
    def __init__(
        self, mainframe, image, text_list, title='Right click to record point.'
    ):
        Zoom_Scroll.__init__(self, mainframe, image, title=title)
        self.points = []
        self.names = []
        self.points_r = []
        self.names_r = []
        self.text_list = copy.deepcopy(text_list)

        b_delete = tk.Button(
            self.master, text="Delete Last Point (d)", command=self.delete_last_point
        )
        b_delete.grid(row=0, column=1)

        self.canvas.bind('<ButtonPress-3>', self.record_point)
        self.canvas.bind('<d>', self.delete_last_point)
        self.canvas.focus_set()

    def delete_last_point(self, event=None):
        if len(self.points) > 0:
            self.points.pop()
            self.names.pop()
            self.canvas.delete(self.names_r[-1])
            self.canvas.delete(self.points_r[-1])
            self.names_r.pop()
            self.points_r.pop()

    def record_point(self, event):

        ''' Show image on the Canvas '''
        x, y, x_plot, y_plot = self.get_coords(event.x, event.y)
        on_image = (0<=x<=self.image.size[0])*(0<=y<=self.image.size[1])

        if on_image:
            r = self.canvas.create_rectangle(
                x_plot-2*self.imscale, y_plot-2*self.imscale,
                x_plot+2*self.imscale, y_plot+2*self.imscale,
                width=1, fill='red', outline='red'
            )
            self.points_r.append(r)

            self.new_window = tk.Toplevel(self.master)
            self.app = Name_Polygons_Popup(
                self.new_window, self.text_list
            )
            self.master.wait_window(self.new_window)
            self.canvas.focus_set()

            if 0 <= self.app.v.get() < len(self.text_list):
                name = self.text_list[self.app.v.get()]
            elif self.app.v.get() == -1:
                name = self.app.n.get()

            r = self.canvas.create_text(
                x_plot+10*self.imscale, y_plot, anchor='w',
                text='({}, {}) '.format(round(x,4), round(y,4)) + name,
                fill='red', font=('Arial', 14, 'bold')
            )
            self.names_r.append(r)
            self.points.append((x, y))
            self.names.append(name)

class Name_Polygons(Zoom_Scroll):
    def __init__(
        self, mainframe, image, coords, text_list,
        names = None, title='Confirm Object Names'
    ):
        Zoom_Scroll.__init__(self, mainframe, image, title=title)
        self.text_list = copy.deepcopy(text_list)
        # Convert line coords into thin poly coords
        self.coords = copy.deepcopy(coords)
        for i in range(len(self.coords)):
            if not np.all(self.coords[i][0] == self.coords[i][-1]):
                thick_im = np.zeros(image.shape[:2]).astype(np.uint8)
                for j in range(len(self.coords[i])-1):
                    thick_im += cv.line(
                        thick_im, tuple(np.squeeze(self.coords[i][j])),
                        tuple(np.squeeze(self.coords[i][j+1])), 1, 2)
                thick_im = (thick_im > 0).astype(np.uint8)
                thick_line = cv.findContours(
                    thick_im, cv.RETR_CCOMP, cv.CHAIN_APPROX_TC89_L1)[0][0]
                self.coords[i] = thick_line

        self.com = []
        self.raw_image = copy.deepcopy(image)
        for i in range(len(self.coords)):
            M = cv.moments(self.coords[i])
            try:
                self.com.append(
                    [int(M['m10']/M['m00']), int(M['m01']/M['m00'])]
                )
            except:
                self.com.append(self.coords[i][0].flatten().tolist())

        self.highlighted = np.array([True]*len(self.coords))
        if not names:
            names = ['No label']*len(self.coords)
        self.names = names
        self.names_offset = [
            random.uniform(0,2*np.pi) for i in range(len(self.names))
        ]
        self.names_r = [None]*len(self.coords)
        self.label_set = np.array([[set([])]*image.shape[1]]*image.shape[0])

        for i in range(len(self.coords)):
            contour = cv.drawContours(
                np.zeros(image.shape[:2]), self.coords, i, 1, -1
            )
            sets = self.label_set[contour>0]
            sets = [s.union({i}) for s in sets]
            self.label_set[contour>0] = sets

        self.contour_image = copy.deepcopy(self.raw_image).astype(np.uint8)
        for i in np.argwhere(self.highlighted == True).flatten():
            self.contour_image = cv.drawContours(
                self.contour_image, self.coords, i, (255,0,0), 2
            )

        self.image = Image.fromarray(self.contour_image)

        for i in range(len(self.coords)):
            if self.com[i]:
                self.names_r[i] = self.canvas.create_text(
                    self.com[i][0] + 5 * np.cos(self.names_offset[i]),
                    self.com[i][1] + 5 * np.sin(self.names_offset[i]),
                    anchor='w', text=self.names[i], fill='red',
                    font=('Arial', 14, 'bold')
                )

        b_all = tk.Button(
            self.master, text="Highlight All (a)",
            command=self.highlight_all
        )
        b_all.grid(row=0, column=2)
        b_none = tk.Button(
            self.master, text="Highlight None (n)",
            command=self.highlight_none
        )
        b_none.grid(row=0, column=1)

        self.canvas.bind("<Button 3>", self.highlight_poly)
        self.canvas.bind('<q>', self.quit)
        self.canvas.bind('<a>', self.highlight_all)
        self.canvas.bind('<n>', self.highlight_none)
        self.canvas.focus_set()
        self.show_image()

    def highlight_all(self, event=None):
        self.highlighted = np.array([True]*len(self.coords))
        self.contour_image = copy.deepcopy(self.raw_image).astype(np.uint8)
        for i in np.argwhere(self.highlighted == True).flatten():
            self.contour_image = cv.drawContours(
                self.contour_image, self.coords, i, (255,0,0), 2
            )
            self.canvas.delete(self.names_r[i])
            com_x_plot, com_y_plot = self.get_plot_coords(
                self.com[i][0], self.com[i][1]
            )
            fill = 'red'
            font = ('Arial', 14, 'bold')
            self.names_r[i] = self.canvas.create_text(
                com_x_plot+5*np.cos(self.names_offset[i])*self.imscale,
                com_y_plot+5*np.sin(self.names_offset[i])*self.imscale,
                anchor='w', text=self.names[i],
                fill=fill, font=font
            )

        self.image = Image.fromarray(self.contour_image.astype(np.uint8))
        self.show_image()

    def highlight_none(self, event=None):
        self.highlighted = np.array([False]*len(self.coords))
        self.contour_image = copy.deepcopy(self.raw_image).astype(np.uint8)
        for i in np.argwhere(self.highlighted == False).flatten():
            self.contour_image = cv.drawContours(
                self.contour_image, self.coords, i, (0,255,0), 1
            )
            self.canvas.delete(self.names_r[i])
            com_x_plot, com_y_plot = self.get_plot_coords(
                self.com[i][0], self.com[i][1]
            )

            fill = '#0f0'
            font = ('Arial', 14)
            self.names_r[i] = self.canvas.create_text(
                com_x_plot+5*np.cos(self.names_offset[i])*self.imscale,
                com_y_plot+5*np.sin(self.names_offset[i])*self.imscale,
                anchor='w', text=self.names[i],
                fill=fill, font=font
            )

        self.image = Image.fromarray(self.contour_image.astype(np.uint8))
        self.show_image()

    def highlight_poly(self, event):

        x, y, x_plot, y_plot = self.get_coords(event.x, event.y)
        inds = self.label_set[round(y),round(x)]

        if len(inds) > 0:
            if len(inds) == 1:
                ind = list(inds)[0]
            else:
                self.new_window = tk.Toplevel(self.master)
                self.app = Name_Polygons_Popup(
                    self.new_window,
                    [
                        str(i+1) + ' ' + self.names[i]
                        + ' (' + (not self.highlighted[i])*'Not '
                        + 'Highlighted)' for i in inds
                    ],
                    title = 'Choose object.'
                )
                self.app.e.destroy()
                self.app.rb[-1].destroy()
                self.master.wait_window(self.new_window)
                self.canvas.focus_set()
                ind = list(inds)[self.app.v.get()]

            self.highlighted[ind] = not self.highlighted[ind]
            self.contour_image = copy.deepcopy(self.raw_image).astype(np.uint8)
            for i in np.argwhere(self.highlighted == False).flatten():
                self.contour_image = cv.drawContours(
                    self.contour_image, self.coords, i, (0,255,0), 1
                )
            for i in np.argwhere(self.highlighted == True).flatten():
                self.contour_image = cv.drawContours(
                    self.contour_image, self.coords, i, (255,0,0), 2
                )

            self.image = Image.fromarray(self.contour_image.astype(np.uint8))
            self.show_image()

            if self.highlighted[ind]:
                self.new_window = tk.Toplevel(self.master)
                self.app = Name_Polygons_Popup(
                    self.new_window, self.text_list
                )
                self.master.wait_window(self.new_window)
                self.canvas.focus_set()

                if 0 <= self.app.v.get() < len(self.text_list):
                    self.names[ind] = self.text_list[self.app.v.get()]
                elif self.app.v.get() == -1:
                    self.names[ind] = self.app.n.get()
                    self.text_list.append(self.app.n.get())

            for i in range(len(self.coords)):
                if self.com[i]:
                    self.canvas.delete(self.names_r[i])
                    com_x_plot, com_y_plot = self.get_plot_coords(
                        self.com[i][0], self.com[i][1]
                    )
                    if self.highlighted[i]:
                        fill = 'red'
                        font = ('Arial', 14, 'bold')
                    else:
                        fill = '#0f0'
                        font = ('Arial', 14)
                    self.names_r[i] = self.canvas.create_text(
                        com_x_plot + 5 * np.cos(self.names_offset[i]) * self.imscale,
                        com_y_plot + 5 * np.sin(self.names_offset[i]) * self.imscale,
                        anchor='w', text=self.names[i],
                        fill=fill, font=font
                    )

class Name_Polygons_Popup():
    def __init__(
        self, master, text_list,
        title='Choose a legend entry for this polygon.'
    ):
        self.master = master
        self.frame = tk.Frame(self.master)
        self.master.title(title)
        self.v = tk.IntVar()
        self.v.set(999)
        self.n = tk.StringVar()
        self.rb = []

        button = tk.Button(
            self.frame, text="Done (Enter)", state=tk.DISABLED, command=self.master.destroy
        )

        def activate_button():
            button['state'] = tk.NORMAL

        for i in range(len(text_list)):
            rb = tk.Radiobutton(
                self.frame,
                text=str(i+1) + '. ' + text_list[i],
                padx = 20,
                variable=self.v,
                value=i,
                justify = tk.LEFT,
                command = activate_button
            )
            self.rb.append(rb)
            rb.grid(row=i)

        rb = tk.Radiobutton(
            self.frame,
            text=str(len(text_list)+1) + '. Add New',
            padx = 20,
            variable=self.v,
            value=-1,
            justify = tk.LEFT,
            command = activate_button
        )
        self.rb.append(rb)
        rb.grid(row=len(text_list))

        # for i in range(len(self.rb)):
        #     if (i+1) < 10:
        #         self.master.bind(
        #             str(i+1), lambda e, bn=i: self.rb[bn].invoke()
        #         )

        self.master.bind('<Return>', lambda e: button.invoke())

        e = tk.Entry(
            self.frame, textvariable = self.n
        )
        self.e = e
        e.grid(row=len(text_list)+1)
        button.grid(row=len(text_list)+2)
        self.frame.pack()

class Confirm_Names(ttk.Frame):
    def __init__(
        self, master, text_list,
        title='Confirm Legend Entries'
    ):
        self.master = master
        self.master.title(title)
        self.frame = tk.Frame(self.master)
        self.text_list = copy.deepcopy(text_list)
        self.n = [tk.StringVar() for i in range(len(self.text_list))]
        for i in range(len(self.n)):
            self.n[i].set(self.text_list[i])
        self.e = []
        for i in range(len(text_list)):
            label_text = tk.StringVar()
            label_text.set(str(i+1) + '.')
            label = tk.Label(self.master, textvariable=label_text)
            label.grid(row=i, column=0)
            e = tk.Entry(self.master, textvariable = self.n[i], width=50)
            self.e.append(e)
            e.grid(row=i, column=1)

        button = tk.Button(
            self.master, text="Done (Enter)", command=self.master.destroy
        )
        button.grid(row=len(text_list), column=1, columnspan=2)

        self.master.bind('<Return>', lambda e: button.invoke())

class Define_Training_Regions(Zoom_Scroll):
    def __init__(
        self, mainframe, image, text_list,
        legend=None, title='Choose training regions.'
    ):
        Zoom_Scroll.__init__(self, mainframe, image, title=title)
        self.label = 0
        self.names = ['Backgound']
        self.master.title(
            'Choose training regions for {}'.format(self.names[self.label])
        )
        self.text_list = text_list + ['Map background']

        self.p1 = None
        self.p2 = None
        self.boxes = [np.array([[]]).reshape([0,5]).astype(int)]
        self.p1_r = None
        self.p2_r = None

        self.canvas.bind("<Button 3>", self.draw_box)
        self.canvas.bind('<Left>', self.previous_label)
        self.canvas.bind('<p>', self.previous_label)
        self.canvas.bind('<Right>', self.next_label)
        self.canvas.bind('<n>', self.next_label)
        self.canvas.focus_set()

        try:
            shape = legend.shape
        except:
            shape = [0]

        if len(shape) in [2,3]:
            self.new_window = tk.Toplevel(self.master)
            self.new_window.canvas = tk.Canvas(
                self.new_window, width=legend.shape[1], height=legend.shape[0], cursor='tcross'
            )
            self.new_window.canvas.update()  # wait till canvas is created
            self.new_window.canvas.pack(expand = 'yes', fill = 'both')
            im = Image.fromarray(legend)
            ph = ImageTk.PhotoImage(image=im)
            self.new_window.canvas.ph = ph
            self.new_window.canvas.create_image(0, 0, image = ph, anchor = 'nw')
            self.new_window.canvas.ph = ph

        b_next = tk.Button(
            self.master, text="Next Category (Right Arrow)",
            command=self.next_label
        )
        b_next.grid(row=0, column=2)
        b_previous = tk.Button(
            self.master, text="Previous Category (Left Arrow)",
            command=self.previous_label
        )
        b_previous.grid(row=0, column=1)
        self.canvas.focus_set()

    def draw_box(self, event):
        # import pdb; pdb.set_trace()
        boxes = self.boxes[self.label]
        x, y, x_plot, y_plot = self.get_coords(event.x, event.y)
        if boxes.size > 0:
            x_cond = np.logical_and(boxes[:,0]<=x, x<=boxes[:,2])
            y_cond = np.logical_and(boxes[:,1]<=y, y<=boxes[:,3])
            in_boxes = np.argwhere(
                np.logical_and(x_cond, y_cond)
            ).flatten()
        else:
            in_boxes = np.array([])

        if in_boxes.size > 0:
            for box_num in in_boxes:
                self.canvas.delete(boxes[box_num,4])
            self.boxes[self.label] = np.delete(
                self.boxes[self.label], in_boxes.tolist(), 0
            )
            self.p1 = None
            self.p2 = None
            self.canvas.delete(self.p1_r)
            self.canvas.delete(self.p2_r)

        else:
            if not self.p1:
                self.canvas.delete(self.p1_r)
                self.p1 = [x, y]
                self.p1_r = self.canvas.create_rectangle(
                    x_plot-2*self.imscale, y_plot-2*self.imscale,
                    x_plot+2*self.imscale, y_plot+2*self.imscale,
                    width=1, fill='red', outline='red'
                )
            elif not self.p2:
                if (x > self.p1[0]) and (y > self.p1[1]):
                    self.canvas.delete(self.p2_r)
                    self.p2 = [x, y]
                    self.p2_r = self.canvas.create_rectangle(
                        x_plot-2*self.imscale, y_plot-2*self.imscale,
                        x_plot+2*self.imscale, y_plot+2*self.imscale,
                        width=1, fill='red', outline='red'
                    )
                    p1_x_plot, p1_y_plot = self.get_plot_coords(
                        self.p1[0], self.p1[1]
                    )
                    r = self.canvas.create_rectangle(
                        p1_x_plot, p1_y_plot, x_plot, y_plot,
                        width=2, outline='red'
                    )
                    self.boxes[self.label] = np.append(
                        self.boxes[self.label], [
                            [self.p1[0], self.p1[1], self.p2[0], self.p2[1], r]
                        ],
                        axis=0
                    ).astype(int)
            else:
                self.canvas.delete(self.p1_r)
                self.canvas.delete(self.p2_r)
                self.p1 = [x, y]
                self.p1_r = self.canvas.create_rectangle(
                    x_plot-2*self.imscale, y_plot-2*self.imscale,
                    x_plot+2*self.imscale, y_plot+2*self.imscale,
                    width=2, outline='red', fill='red'
                )
                self.p2 = None

    def next_label(self, event=None):
        if len(self.boxes) < 20:
            self.canvas.delete(self.p1_r)
            self.canvas.delete(self.p2_r)
            self.p1 = None
            self.p2 = None

            for box in self.boxes[self.label]:
                self.canvas.delete(box[4])

            if self.label == len(self.boxes)-1:

                self.boxes.append(np.array([[]]).reshape([0,5]).astype(int))
                self.new_window = tk.Toplevel(self.master)

                self.app = Name_Polygons_Popup(
                    self.new_window, self.text_list,
                    'Select name for new group of training boxes.'
                )
                self.master.wait_window(self.new_window)
                self.canvas.focus_set()

                if 0 <= self.app.v.get() < len(self.text_list):
                    self.names.append(self.text_list[self.app.v.get()])
                elif self.app.v.get() == -1:
                    self.names.append(self.app.n.get())
                    self.text_list.append(self.app.n.get())

            self.label += 1

            self.master.title(
                'Choose training regions for {}'.format(self.names[self.label])
            )

            for box in self.boxes[self.label]:
                p1_x_plot, p1_y_plot = self.get_plot_coords(box[0], box[1])
                p2_x_plot, p2_y_plot = self.get_plot_coords(box[2], box[3])
                r = self.canvas.create_rectangle(
                    p1_x_plot, p1_y_plot, p2_x_plot, p2_y_plot,
                    width=2, outline='red'
                )
                box[4] = r

    def previous_label(self, event=None):
        if self.label > 0:
            self.canvas.delete(self.p1_r)
            self.canvas.delete(self.p2_r)
            self.p1 = None
            self.p2 = None
            for box in self.boxes[self.label]:
                self.canvas.delete(box[4])
            self.label -= 1
            for box in self.boxes[self.label]:
                p1_x_plot, p1_y_plot = self.get_plot_coords(box[0], box[1])
                p2_x_plot, p2_y_plot = self.get_plot_coords(box[2], box[3])
                r = self.canvas.create_rectangle(
                    p1_x_plot, p1_y_plot, p2_x_plot, p2_y_plot,
                    width=2, outline='red'
                )
                box[4] = r
            self.master.title(
                'Choose training regions for {}'.format(self.names[self.label])
            )

class Choose_Kept_Categories():
    def __init__(
        self, master, text_list,
        title='Choose the recovered polygon classes to keep.'
    ):
        self.master = master
        self.frame = tk.Frame(self.master)
        self.master.title(title)
        self.v = [tk.IntVar() for i in range(len(text_list))]

        button = tk.Button(
            self.frame, text="Done", state=tk.DISABLED,
            command=self.master.destroy
        )

        def activate_button():
            button['state'] = tk.NORMAL

        for i in range(len(text_list)):
            tk.Checkbutton(
                self.frame,
                text=text_list[i],
                padx = 20,
                variable=self.v[i],
                justify = tk.LEFT,
                command = activate_button
            ).grid(row=i)

        button.grid(row=len(text_list))

        self.frame.pack()

class Choose_Map():
    def __init__(
        self, master, page_nums, dir,
        title='Choose a map to scrape.'
    ):
        self.master = master
        self.master.title(title)
        self.container = ttk.Frame(self.master)
        self.canvas = tk.Canvas(self.container)
        scrollbar = ttk.Scrollbar(
            self.container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")))

        self.canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.rb = []
        self.v = tk.IntVar()
        self.v.set(-999)
        self.ph = []
        self.fn = []
        self.n = [tk.StringVar() for i in range(len(page_nums))]

        self.button = tk.Button(
            self.container, text="Done (Enter)", state=tk.DISABLED,
            command=self.master.destroy)

        def activate_button():
            self.button['state'] = tk.NORMAL

        for i in range(len(page_nums)):
            file_name = 'page-' + str(page_nums[i]) + '.png'
            self.fn.append(file_name)
            img = Image.open(dir + file_name)
            img.thumbnail([256,256],Image.ANTIALIAS)
            self.ph.append(ImageTk.PhotoImage(img))
        for i in range(len(page_nums)):
            self.n[i].set('Page ' + str(page_nums[i]))
            l = tk.Label(
                self.scrollable_frame, textvariable=self.n[i],
            )
            row = i // 3
            col = i-3*row
            l.grid(row=row, column=2*col+1)

            rb = tk.Radiobutton(
                self.scrollable_frame,
                variable=self.v,
                value=i,
                image=self.ph[i],
                command=activate_button,
                height=220,
            )
            self.rb.append(rb)
            rb.grid(row=row, column=2*col)
        self.button.pack()
        self.master.bind('<MouseWheel>', self.on_mousewheel)
        self.master.bind('<Button-5>',   self.scroll_up)
        self.master.bind('<Button-4>',   self.scroll_down)
        self.master.bind('<Return>', lambda e: self.button.invoke())

        self.container.pack(fill='both', expand=True)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def scroll_up(self, event):
        self.canvas.yview_scroll(1, "units")

    def scroll_down(self, event):
        self.canvas.yview_scroll(-1, "units")

    def on_mousewheel(self, event):
        self.canvas.yview_scroll(event.delta, "units")

class Choose_Map_Template(Choose_Map):
    def __init__(
        self, master, page_nums, current_page, dir,
        title='Choose a map template.'
    ):
        Choose_Map.__init__(self, master, page_nums, dir, title=title)

        def activate_button():
            self.button['state'] = tk.NORMAL

        self.n_new = tk.StringVar()
        self.n_new.set(
            'Create new template from current map (page ' + str(current_page)
            + ')')
        label = tk.Label(
            self.scrollable_frame, textvariable=self.n_new)
        row = (len(page_nums)+1)//3
        col = len(page_nums)+1-3*row
        label.grid(row=row, column=2*col+1)

        file_name = 'page-' + str(current_page) + '.png'
        self.fn.append(file_name)
        img = Image.open(dir + file_name)
        img.thumbnail([256,256],Image.ANTIALIAS)
        self.ph_new = ImageTk.PhotoImage(img)

        rb = tk.Radiobutton(
            self.scrollable_frame, variable=self.v, value=-1, image=self.ph_new,
            command=activate_button, height=220)
        self.rb.append(rb)
        rb.grid(row=row, column=2*col)

import copy

import tkinter as tk
from tkinter import ttk
from tkinter.simpledialog import askstring

from PIL import Image, ImageTk

import numpy as np
import cv2 as cv

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

class Choose_Points(ttk.Frame):
    ''' Advanced zoom of the image '''
    def __init__(self, mainframe, path, text_list):
        ''' Initialize the main Frame '''
        ttk.Frame.__init__(self, master=mainframe)
        self.master.title('Right click to choose points.')
        # Vertical and horizontal scrollbars for canvas
        vbar = AutoScrollbar(self.master, orient='vertical')
        hbar = AutoScrollbar(self.master, orient='horizontal')
        vbar.grid(row=0, column=1, sticky='ns')
        hbar.grid(row=1, column=0, sticky='we')
        self.points = []
        self.names = []
        self.text_list = copy.deepcopy(text_list)
        # Create canvas and put image on it
        self.canvas = tk.Canvas(self.master, highlightthickness=0,
                                xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        self.canvas.grid(row=0, column=0, sticky='nswe')
        self.canvas.update()  # wait till canvas is created
        vbar.configure(command=self.scroll_y)  # bind scrollbars to the canvas
        hbar.configure(command=self.scroll_x)
        # Make the canvas expandable
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)
        # Bind events to the Canvas
        self.canvas.bind('<Configure>', self.show_image)  # canvas is resized
        self.canvas.bind('<ButtonPress-1>', self.move_from)
        self.canvas.bind('<B1-Motion>',     self.move_to)
        self.canvas.bind('<MouseWheel>', self.wheel)  # with Windows and MacOS, but not Linux
        self.canvas.bind('<Button-5>',   self.wheel)  # only with Linux, wheel scroll down
        self.canvas.bind('<Button-4>',   self.wheel)  # only with Linux, wheel scroll up
        self.canvas.bind('<ButtonPress-3>', self.record_point)
        self.image = Image.open(path)  # open image
        self.width, self.height = self.image.size
        self.imscale = 1.0  # scale for the canvaas image
        self.delta = 1.3  # zoom magnitude
        # Put image into container rectangle and use it to set proper coordinates to the image
        self.container = self.canvas.create_rectangle(0, 0, self.width, self.height, width=0)
        self.show_image()

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

    def record_point(self, event):

        ''' Show image on the Canvas '''
        bbox = self.canvas.bbox(self.container)  # get image area
        x_plot = self.canvas.canvasx(0) + event.x
        y_plot = self.canvas.canvasy(0) + event.y
        x = (x_plot - bbox[0])/self.imscale
        y = (y_plot - bbox[1])/self.imscale
        on_image = (0<=x<=self.image.size[0])*(0<=y<=self.image.size[1])

        if on_image:
            self.canvas.create_rectangle(
                x_plot-2*self.imscale, y_plot-2*self.imscale,
                x_plot+2*self.imscale, y_plot+2*self.imscale,
                width=1, fill='red', outline='red'
            )

            self.new_window = tk.Toplevel(self.master)
            self.app = Name_Polygons_Popup(
                self.new_window, self.text_list
            )
            self.master.wait_window(self.new_window)

            if 0 <= self.app.v.get() < len(self.text_list):
                name = self.text_list[self.app.v.get()]
            elif self.app.v.get() == -1:
                name = self.app.n.get()

            self.canvas.create_text(
                x_plot+10*self.imscale, y_plot, anchor='w',
                text='(' + str(x) + ', ' + str(y) + ') ' + name,
                fill='red', font=('Times New Roman', 12)
            )
            self.points.append((x, y))
            self.names.append(name)

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

class Name_Polygons(ttk.Frame):
    def __init__(self, mainframe, image, coords, text_list):
        ttk.Frame.__init__(self, master=mainframe)
        self.master.title('Click to choose polygons.')
        self.text_list = copy.deepcopy(text_list)
        self.coords = copy.deepcopy(coords)
        self.image = image
        self.canvas = tk.Canvas(
            self.master, width=100, height=100, cursor='tcross'
        )
        self.canvas.pack(expand = 'yes', fill = 'both')
        self.canvas.update()

        self.highlighted = np.array([False]*len(self.coords))
        self.names = ['No label']*len(self.coords)
        self.label_objects = np.zeros(image.shape[:2])
        for i in range(len(self.coords)):
            self.label_objects = cv.drawContours(
                self.label_objects, self.coords, i, i+1, -1
            )
        self.label_objects = self.label_objects.astype(int)
        self.contour_image = copy.deepcopy(self.image)
        for i in np.argwhere(self.highlighted == False).flatten():
            self.contour_image = cv.drawContours(
                self.contour_image, self.coords, i, (0,255,0), 2
            )

        im = Image.fromarray(self.contour_image.astype(np.uint8))
        ph = ImageTk.PhotoImage(image=im)
        self.canvas.ph = ph

        self.canvas.create_image(0, 0, image = ph, anchor = 'nw')
        self.canvas.ph = ph

        self.canvas.bind("<Button 1>", self.highlight_poly)

    #function to be called when mouse is clicked
    def highlight_poly(self, event):

        x, y = [event.x, event.y]
        ind = self.label_objects[y,x]
        if ind > 0:
            self.highlighted[ind-1] = not self.highlighted[ind-1]

            self.contour_image = copy.deepcopy(self.image)

            for i in np.argwhere(self.highlighted == False).flatten():
                self.contour_image = cv.drawContours(
                    self.contour_image, self.coords, i, (0,255,0), 2
                )
            for i in np.argwhere(self.highlighted == True).flatten():
                self.contour_image = cv.drawContours(
                    self.contour_image, self.coords, i, (0,255,0), -1
                )

            im = Image.fromarray(self.contour_image.astype(np.uint8))
            ph = ImageTk.PhotoImage(image=im)
            self.canvas.ph = ph
            self.canvas.create_image(0, 0, image = ph, anchor = 'nw')

            if self.highlighted[ind-1]:
                self.new_window = tk.Toplevel(self.master)

                self.app = Name_Polygons_Popup(
                    self.new_window, self.text_list
                )

                self.master.wait_window(self.new_window)

                if 0 <= self.app.v.get() < len(self.text_list):
                    self.names[ind-1] = self.text_list[self.app.v.get()]
                elif self.app.v.get() == -1:
                    self.names[ind-1] = self.app.n.get()
                    self.text_list.append(self.app.n.get())

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

        button = tk.Button(
            self.frame, text="Done", state=tk.DISABLED, command=self.master.destroy
        )

        def activate_button():
            button['state'] = tk.NORMAL

        for i in range(len(text_list)):
            tk.Radiobutton(
                self.frame,
                text=text_list[i],
                padx = 20,
                variable=self.v,
                value=i,
                justify = tk.LEFT,
                command = activate_button
            ).grid(row=i)

        tk.Radiobutton(
            self.frame,
            text="None of these.",
            padx = 20,
            variable=self.v,
            value=-1,
            justify = tk.LEFT,
            command = activate_button
        ).grid(row=len(text_list))

        tk.Entry(self.frame, textvariable = self.n).grid(row=len(text_list)+1)
        button.grid(row=len(text_list)+2)

        self.frame.pack()

class Define_Training_Regions(ttk.Frame):
    def __init__(self, mainframe, image, text_list):
        ttk.Frame.__init__(self, master=mainframe)
        self.label = 0
        self.names = ['Backgound']
        self.master.title(
            'Choose training regions for {}'.format(self.names[self.label])
        )
        self.text_list = text_list + ['Map background']

        self.canvas = tk.Canvas(
            self.master, width=100, height=100, cursor='tcross'
        )
        self.canvas.update()  # wait till canvas is created

        self.canvas.pack(expand = 'yes', fill = 'both')

        im = Image.fromarray(image)
        ph = ImageTk.PhotoImage(image=im)
        self.canvas.ph = ph

        self.canvas.create_image(0, 0, image = ph, anchor = 'nw')
        self.canvas.ph = ph

        self.p1 = None
        self.p2 = None
        self.boxes = [np.array([[]]).reshape([0,5]).astype(int)]
        self.p1_r = None
        self.p2_r = None

        self.canvas.bind("<Button 1>", self.draw_box)
        self.canvas.bind('<Left>', self.previous_label)
        self.canvas.bind('<p>', self.previous_label)
        self.canvas.bind('<Right>', self.next_label)
        self.canvas.bind('<n>', self.next_label)
        self.canvas.focus_set()

    def draw_box(self, event):
        boxes = self.boxes[self.label]
        if boxes.size > 0:
            x_cond = np.logical_and(
                boxes[:,0]<=event.x,
                event.x<=boxes[:,2]
            )
            y_cond = np.logical_and(
                boxes[:,1]<=event.y,
                event.y<=boxes[:,3]
            )
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
                self.p1 = [event.x, event.y]
                self.p1_r = self.canvas.create_rectangle(
                    event.x-2, event.y-2, event.x+2, event.y+2,
                    width=1, fill='red', outline='red'
                )
            elif not self.p2:
                if (event.x > self.p1[0]) and (event.y > self.p1[1]):
                    self.canvas.delete(self.p2_r)
                    self.p2 = [event.x, event.y]
                    self.p2_r = self.canvas.create_rectangle(
                        event.x-2, event.y-2, event.x+2, event.y+2,
                        width=1, fill='red', outline='red'
                    )
                    r = self.canvas.create_rectangle(
                        self.p1[0], self.p1[1], self.p2[0], self.p2[1],
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

                self.p1 = [event.x, event.y]
                self.p1_r = self.canvas.create_rectangle(
                    event.x-2, event.y-2, event.x+2, event.y+2,
                    width=2, outline='red'
                )
                self.p2 = None

    def next_label(self, event):
        if len(self.boxes) < 10:
            self.canvas.delete(self.p1_r)
            self.canvas.delete(self.p2_r)
            self.p1 = None
            self.p2 = None
            if self.label == len(self.boxes)-1:

                self.boxes.append(np.array([[]]).reshape([0,5]).astype(int))
                self.new_window = tk.Toplevel(self.master)

                self.app = Name_Polygons_Popup(
                    self.new_window, self.text_list,
                    'Select name for new group of training boxes.'
                )
                self.master.wait_window(self.new_window)

                if 0 <= self.app.v.get() < len(self.text_list):
                    self.names.append(self.text_list[self.app.v.get()])
                elif self.app.v.get() == -1:
                    self.names.append(self.app.n.get())
                    self.text_list.append(self.app.n.get())

            for box in self.boxes[self.label]:
                self.canvas.delete(box[4])

            self.label += 1

            self.master.title(
                'Choose training regions for {}'.format(self.names[self.label])
            )

            for box in self.boxes[self.label]:
                r = self.canvas.create_rectangle(
                    box[0], box[1], box[2], box[3],
                    width=2, outline='red'
                )
                box[4] = r

    def previous_label(self, event):
        if self.label > 0:
            self.canvas.delete(self.p1_r)
            self.canvas.delete(self.p2_r)
            self.p1 = None
            self.p2 = None
            for box in self.boxes[self.label]:
                self.canvas.delete(box[4])
            self.label -= 1
            for box in self.boxes[self.label]:
                r = self.canvas.create_rectangle(
                    box[0], box[1], box[2], box[3],
                    width=2, outline='red'
                )
                box[4] = r
            self.master.title(
                'Choose training regions for {}'.format(self.names[self.label])
            )

class Get_Legend_Box(ttk.Frame):
    def __init__(self, mainframe, image):
        ttk.Frame.__init__(self, master=mainframe)
        self.master.title(
            'Click to select top left and bottom right corners of legend box.'
        )

        self.canvas = tk.Canvas(
            self.master, width=100, height=100, cursor='tcross'
        )
        self.canvas.update()  # wait till canvas is created


        self.canvas.pack(expand = 'yes', fill = 'both')

        im = Image.fromarray(image)
        ph = ImageTk.PhotoImage(image=im)
        self.canvas.ph = ph

        self.canvas.create_image(0, 0, image = ph, anchor = 'nw')
        self.canvas.ph = ph

        self.p1 = None
        self.p2 = None
        self.rect = None
        self.p1_r = None
        self.p2_r = None

        self.canvas.bind("<Button 1>", self.draw_box)
        self.canvas.focus_set()

    def draw_box(self, event):

        if not self.p1:
            self.canvas.delete(self.p1_r)
            self.p1 = [event.x, event.y]
            self.p1_r = self.canvas.create_rectangle(
                event.x-2, event.y-2, event.x+2, event.y+2,
                width=1, fill='red', outline='red'
            )
        elif not self.p2:
            self.canvas.delete(self.p2_r)
            self.p2 = [event.x, event.y]
            self.p2_r = self.canvas.create_rectangle(
                event.x-2, event.y-2, event.x+2, event.y+2,
                width=1, fill='red', outline='red'
            )
            self.rect = self.canvas.create_rectangle(
                self.p1[0], self.p1[1], self.p2[0], self.p2[1],
                width=1, outline='red'
            )
        else:
            self.canvas.delete(self.p1_r)
            self.canvas.delete(self.p2_r)
            self.canvas.delete(self.rect)

            self.p1 = [event.x, event.y]
            self.p1_r = self.canvas.create_rectangle(
                event.x-2, event.y-2, event.x+2, event.y+2,
                width=1, fill='red', outline='red'
            )
            self.p2 = None

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
            self.frame, text="Done", state=tk.DISABLED, command=self.master.destroy
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

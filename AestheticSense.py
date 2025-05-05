import sys
import os
import datetime
from pathlib import Path
import piexif
from send2trash import send2trash
import json

from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QLabel, \
    QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog, QGridLayout, QScrollArea, \
    QTextEdit, QFileSystemModel, QTreeView, QTreeWidget, QAction, QGraphicsView, QSizePolicy, QMessageBox, \
    QFormLayout, QComboBox, QLineEdit, QGroupBox, QSizePolicy, QSpinBox, QProgressDialog
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QDir, QFileSystemWatcher, QTimer


from model import predict_image, save_changes

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.all_image_paths = []
        self.image_paths = []  # List to store image paths being used
        self.current_index = -1  # Track current image index for prev and next buttons, start with -1 (no image selected)
        self.is_initialized = False  # Flag to check if the gallery is initialized
        self.edit_flag = False  # Flag to check if file updates are external or application
        self.filtered_flag = False 
        self.selected_images = set()  # Store selected images

        # Timer to delay the directory change handling
        self.change_timer = QTimer(self)
        self.change_timer.setSingleShot(True)  # Make sure the timer triggers only once at a time
        self.change_timer.setInterval(500)  # Set interval for debouncing (500 ms)
        self.change_timer.timeout.connect(self.handle_directory_change)

        self.setWindowTitle("AestheticSense")
        self.resize(1400, 950)

        # Central Widget
        self.centralwidget = QWidget(self)
        self.setCentralWidget(self.centralwidget)

        # Main Layout
        self.main_layout = QHBoxLayout(self.centralwidget)
        self.image_center = QVBoxLayout()
        self.analyse_bar = QHBoxLayout()
        self.image_center.addLayout(self.analyse_bar)

        # Tree Widget
        self.treeWidget = QTreeView()
        self.treeWidget.setMaximumWidth(300)
        self.treeWidget.clicked.connect(self.on_item_clicked)
        self.main_layout.addWidget(self.treeWidget, alignment=Qt.AlignLeft)
        self.main_layout.addLayout(self.image_center)
        
        # Buttons
        self.analyse_btn = QPushButton("Analyse Images")  # Button to trigger All Image Analysis
        self.analyse_btn.clicked.connect(self.analyse_images)  # Connect button to function
        self.analyse_btn.setVisible(False)  # Hidden initially

        self.analyse_current_btn = QPushButton("Analyse This Image")  # Button For Single Image Analysis
        self.analyse_current_btn.clicked.connect(self.analyse_current_image)
        self.analyse_current_btn.setVisible(False)  # Hidden initially

        self.analyse_selected_btn = QPushButton("Analyse Selected") # Button For Selected Image Analysis
        self.analyse_selected_btn.clicked.connect(self.analyse_selected_images)
        self.analyse_selected_btn.setVisible(False)  # Hidden initially

        # Box to get which rating value to filter for
        self.filter_value = QComboBox()
        self.filter_value.addItem("No Filter")
        self.filter_value.addItem("1")
        self.filter_value.addItem("2")
        self.filter_value.addItem("3")
        self.filter_value.addItem("4")
        self.filter_value.addItem("5")
        self.filter_value.setVisible(False)  

        self.filter_btn = QPushButton("Filter Images") 
        self.filter_btn.clicked.connect(self.load_filtered_images)
        self.filter_btn.setVisible(False)  # Hidden initially

        # Adding to Horizontal Layout
        self.analyse_bar.addWidget(self.analyse_btn)
        self.analyse_bar.addWidget(self.analyse_current_btn)
        self.analyse_bar.addWidget(self.analyse_selected_btn)
        self.analyse_bar.addWidget(self.filter_btn)
        self.analyse_bar.addWidget(self.filter_value)

        # Grid Layout for Image Blocks
        self.grid_layout = QGridLayout()

        # Scroll Area for Images
        self.scroll_area = QScrollArea()
        self.scroll_widget = QWidget()
        self.scroll_widget.setLayout(self.grid_layout)
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        self.image_center.addWidget(self.scroll_area)

        # Full-Size Image Viewer
        self.full_image_label = QLabel()
        self.full_image_label.setAlignment(Qt.AlignCenter)
        self.full_image_label.setStyleSheet("border: 2px solid black;")  # Border around full image
        self.full_image_label.setFixedSize(900, 700)  # Set Full Image fixed size 
        self.full_image_label.setVisible(False)  # Initially hidden

        # Metadata Panel
        self.metadata_panel = QGroupBox('Image Information')

        self.metadata_panel_form = QFormLayout()
        self.image_name_label = QLabel(); self.image_name_label.setWordWrap(True)
        self.date_label = QLabel(); self.date_label.setWordWrap(True)
        self.rating_label = QLabel(); self.rating_label.setWordWrap(True)
        self.aesthetic_score_label = QLabel(); self.aesthetic_score_label.setWordWrap(True)
        self.aesthetic_highlights_label = QLabel(); self.aesthetic_highlights_label.setWordWrap(True)
        self.potential_improvements_label = QLabel(); self.potential_improvements_label.setWordWrap(True)
    
        self.metadata_panel_form.addRow(QLabel("Image Name:"), self.image_name_label)
        self.metadata_panel_form.addRow(QLabel("Date:"), self.date_label)
        self.metadata_panel_form.addRow(QLabel("Rating:"),self.rating_label)
        self.metadata_panel_form.addRow(QLabel("Aesthetic Score:"),self.aesthetic_score_label)
        self.metadata_panel_form.addRow(QLabel("Aesthetic Highlights:"),self.aesthetic_highlights_label)
        self.metadata_panel_form.addRow(QLabel("Potential Improvements:"),self.potential_improvements_label)

        # Add a separator line
        self.metadata_panel_form.addRow(QLabel("<hr>"))  

        # Editable fields
        self.edit_image_name = QLineEdit()
        self.edit_rating = QSpinBox()
        self.edit_rating.setRange(1, 5)

        self.metadata_panel_form.addRow(QLabel("Edit Name:"), self.edit_image_name)
        self.metadata_panel_form.addRow(QLabel("Edit Rating:"), self.edit_rating)

        # Save button
        self.save_button = QPushButton("Save Changes")
        self.save_button.clicked.connect(self.save_changes)
        self.metadata_panel_form.addRow(self.save_button)

        # Add a separator line
        self.metadata_panel_form.addRow(QLabel("<hr>")) 

        # Delete button
        self.delete_button = QPushButton("Delete Image")
        self.delete_button.clicked.connect(self.delete_image)
        self.metadata_panel_form.addRow(self.delete_button)

        self.metadata_panel.setLayout(self.metadata_panel_form)
        self.metadata_panel.setFixedWidth(300)  # Adjust width as needed
        self.metadata_panel.setVisible(False)  # Initially hidden

        # Full Image Layout
        full_image_layout = QHBoxLayout()
        full_image_layout.addWidget(self.full_image_label)
        full_image_layout.addWidget(self.metadata_panel)

        self.main_layout.addLayout(full_image_layout)

        # Navigation buttons
        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("Previous")
        self.next_btn = QPushButton("Next")
        self.prev_btn.clicked.connect(self.show_previous)
        self.next_btn.clicked.connect(self.show_next)

        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.next_btn)

        # Initially hide navigation buttons
        self.prev_btn.setVisible(False)
        self.next_btn.setVisible(False)
        self.image_center.addLayout(nav_layout)
    
        # Menu Bar
        self.menubar = self.menuBar()
        self.menuFile = self.menubar.addMenu("File")

        self.Load_Folder = QAction("Load Folder", self)
        self.Load_Folder.triggered.connect(self.load_folder)
        self.menuFile.addAction(self.Load_Folder)

        self.Load_Files = QAction("Load Files", self)
        self.Load_Files.triggered.connect(self.load_files)
        self.menuFile.addAction(self.Load_Files)

        self.folder_watcher = QFileSystemWatcher(self)

    def load_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")

        if folder:
            # Load all images from the selected folder
            self.image_paths = [os.path.join(folder, f) for f in os.listdir(folder) 
                                if f.lower().endswith(('.jpg', '.jpeg'))]

            if not self.image_paths:
                QMessageBox.warning(self, "No Images Found", "No images found in the selected folder!", QMessageBox.Ok)
                return
            
            self.setTree(folder)
            self.basic_load()

    def load_files(self):
        files, files_types = QFileDialog.getOpenFileNames(None, "Select Files", "", "Images (*.jpg *.jpeg)")
        self.image_paths = files

        if not self.image_paths:
            QMessageBox.warning(self, "No Images Found", "No images found!", QMessageBox.Ok)
            return
            
        self.folder_watcher.removePaths(self.folder_watcher.directories())
        self.treeWidget.setModel(None)
        self.basic_load()

    def basic_load(self): 
        self.all_image_paths = self.image_paths.copy()
        self.analyse_btn.setVisible(True) 
        self.analyse_selected_btn.setVisible(True)
        self.filter_btn.setVisible(True)  
        self.filter_value.setVisible(True)  
        self.prev_btn.setVisible(False)
        self.next_btn.setVisible(False)
        self.analyse_current_btn.setVisible(False)
        self.metadata_panel.setVisible(False)
        self.display_images()
    
    def setTree(self, folder):
        self.model = QFileSystemModel()
        self.model.setRootPath(folder)
        self.model.setNameFilters(["*.jpg", "*.jpeg"])  # Adjust for both .jpg and .jpeg files
        self.model.setNameFilterDisables(False)  # Enable the filter to show only those files
        self.model.setFilter(QDir.Files)
        self.treeWidget.setModel(self.model)
        self.treeWidget.setRootIndex(self.model.index(folder))
        self.treeWidget.setColumnWidth(0, 250)
        self.treeWidget.setAlternatingRowColors(True)
        self.treeWidget.setColumnHidden(1, True)  # Hide the "Size" column
        self.treeWidget.setColumnHidden(2, True)  # Hide the "Type" column
        self.treeWidget.setColumnHidden(3, True)  # Hide the "Date Modified" column

        # Always clear old paths
        self.folder_watcher.removePaths(self.folder_watcher.directories())

        # Add new folder
        self.folder_watcher.addPath(folder)
        self.folder_watcher.directoryChanged.connect(self.on_directory_changed)

    def on_directory_changed(self):
        if self.edit_flag == True:
            self.edit_flag = False
            return
        self.change_timer.start()

    def handle_directory_change(self):
        folder = self.folder_watcher.directories()[0]

        new_image_paths = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.jpeg'))]
        
        removed = set(self.all_image_paths).difference(set(new_image_paths))
        added = set(new_image_paths).difference(set(self.all_image_paths))

        if not removed and not added:
            return
        
        self.all_image_paths = new_image_paths.copy()

        if self.full_image_label.isVisible() == False and self.filtered_flag == False:
            self.clearLayout(self.grid_layout)
            self.selected_images.clear()
            self.image_paths = new_image_paths.copy()
            self.display_images() 
            return

        if self.filtered_flag == False:
            self.clearLayout(self.grid_layout)
            self.selected_images.clear()
            self.image_paths = new_image_paths.copy()
            row = 0
            for img_path in self.image_paths:
                self.addImage(img_path, row, 0) # All in one column
                row += 1
        
    def display_images(self):
        if not self.image_paths:
            QMessageBox.warning(self, "No Images Found", "No images found!", QMessageBox.Ok)
            return

        self.current_index = 0  # Set to first image index
        self.is_initialized = True  # Mark as initialized
        self.full_image_label.setVisible(False) # Initially hide the full image
        self.clearLayout(self.grid_layout)
        self.selected_images.clear()
        row, col = 0, 0
            
        for img_path in self.image_paths:
            self.addImage(img_path, row, col)
            col += 1
            if col >= 5:  # 5 images per row
                col = 0
                row += 1

        self.grid_layout.setColumnStretch(self.grid_layout.columnCount(), 1)
        self.grid_layout.setRowStretch(self.grid_layout.rowCount(), 1)

    def clearLayout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clearLayout(item.layout())

    def addImage(self, img_path, row, col):
        exif_dict = piexif.load(img_path)
        rating = exif_dict["0th"].get(18246, None)
        
        # Load and scale image while keeping aspect ratio
        img = QPixmap(img_path).scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        vbox = QVBoxLayout()
        
        label = QLabel()
        label.setFixedSize(320, 320)
        label.setPixmap(img)
        label.setAlignment(Qt.AlignCenter | Qt.AlignTop)
        
        line = os.path.basename(img_path)
        line = "\u200b".join(line)
        line += "\n"
        line += self.star_numbers(rating)
        stars_label = QLabel(line)  # Adding stars
        stars_label.setWordWrap(True)
        stars_label.setStyleSheet("background-color: lightgrey; border: solid blue; padding: 0px; border-radius: 10px;")
        stars_label.setAlignment(Qt.AlignCenter | Qt.AlignTop)    
        stars_label.setFixedWidth(320)  
        stars_label.setFixedHeight(50)  

        vbox.addWidget(label)
        vbox.addWidget(stars_label)
        label.mousePressEvent = lambda event, path=img_path, lbl=label: self.label_clicked(event, path, lbl)
        widget = QWidget()
        widget.setLayout(vbox)
        widget.setStyleSheet("background-color: grey; border: solid blue; padding: 0px; border-radius: 10px;")
        self.grid_layout.addWidget(widget, row, col)

    def switch_gallery_layout(self, layout_type):
        self.clearSelectedImages()
        widgets = []
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widgets.append(widget) 
        if layout_type == 'multi-row':
            row, col = 0, 0
            for widget in widgets:
                self.grid_layout.addWidget(widget, row, col)
                col += 1
                if col >= 5:  # 5 images per row
                    col = 0
                    row += 1
        elif layout_type == 'single-column':
            row = 0
            col = 0
            for widget in widgets:
                self.grid_layout.addWidget(widget, row, 0)  # All in one column
                row += 1

    def label_clicked(self, event, path, lbl):
        if event.button() == Qt.LeftButton and not event.modifiers():  
            self.toggle_full_image(path)  # (show/hide full image)
        elif  event.modifiers() & Qt.ControlModifier:  # Ctrl + Click
            self.toggle_selection(path, lbl) 

    def toggle_selection(self, img_path, label):
        if img_path in self.selected_images:
            self.selected_images.remove(img_path)
            label.setStyleSheet("")  # Normal
        else:
            self.selected_images.add(img_path)
            label.setStyleSheet("background-color: lightblue; border: solid blue;")  # Highlighted

    def toggle_full_image(self, img_path):
        if self.full_image_label.isVisible() and self.current_full_image == img_path:
            self.full_image_label.setVisible(False)  # Hide the full image
            self.switch_gallery_layout('multi-row')
            self.prev_btn.setVisible(False)  # Hide the navigation buttons
            self.next_btn.setVisible(False)
            self.metadata_panel.setVisible(False)
            self.analyse_current_btn.setVisible(False) # Hide analyse button
            self.filter_btn.setVisible(True)
            self.filter_value.setVisible(True)   
        elif self.full_image_label.isVisible():
            self.show_full_image(img_path)
            self.clearSelectedImages()
        else:
            self.show_full_image(img_path)  # Show the selected full image
            self.switch_gallery_layout('single-column')
            self.prev_btn.setVisible(True)  # Show the navigation buttons
            self.next_btn.setVisible(True)
            self.filter_btn.setVisible(False)  
            self.filter_value.setVisible(False)  

    def show_full_image(self, img_path):
        exif_dict = piexif.load(img_path)
        rating = exif_dict["0th"].get(18246, None)
        date = datetime.datetime.fromtimestamp(os.path.getctime(img_path)).strftime("%d-%m-%Y")

        pixmap = QPixmap(img_path)
        scaled_pixmap = pixmap.scaled(self.full_image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.full_image_label.setPixmap(scaled_pixmap)

        if img_path in self.image_paths:
            self.current_index = self.image_paths.index(img_path)
        else:
            self.current_index = -1
        
        self.full_image_label.setVisible(True)  # Show the full image
        self.metadata_panel.setVisible(True)
        self.analyse_current_btn.setVisible(True)  # Show button when image is displayed

        highlights, improvements, aesthetic_score = self.aesthetic_comments(exif_dict)

        self.current_full_image = img_path
        line = os.path.basename(img_path)
        self.image_name_label.setText("\u200b".join(line))
        self.date_label.setText(date)
        self.rating_label.setText(self.star_numbers(rating)) 
        self.aesthetic_score_label.setText(str(aesthetic_score)) 
        self.aesthetic_highlights_label.setText(highlights)
        self.potential_improvements_label.setText(improvements) 

        self.edit_image_name.setText(line)
        if rating is not None:
            self.edit_rating.setValue(rating)
        else:
            self.edit_rating.setValue(0)

    def show_previous(self):
        if self.image_paths and self.current_index > 0:
            self.current_index -= 1
            self.show_full_image(self.image_paths[self.current_index])
            
    def show_next(self):
        if self.image_paths and self.current_index < len(self.image_paths) - 1:
            self.current_index += 1
            self.show_full_image(self.image_paths[self.current_index])

    def on_item_clicked(self, index):
        file_path = self.model.filePath(index)

        # Replace the last forward slash with a backslash
        file_path = file_path.rsplit('/', 1)
        if len(file_path) > 1:
            file_path = file_path[0] + '\\' + file_path[1]
        else:
            file_path = file_path[0]  # in case there's no forward slash in the path
        self.toggle_full_image(file_path)

    def load_filtered_images(self):
        self.image_paths = []
        if (self.filter_value.currentText() == "No Filter"):
            self.filtered_flag = False
            self.image_paths = self.all_image_paths.copy()
            self.display_images()
            return
        
        self.filtered_flag = True
        for img_path in self.all_image_paths:
            try:
                exif_dict = piexif.load(img_path)
                rating = exif_dict["0th"].get(18246, None)

                if rating == None:
                    continue
                if str(rating) == self.filter_value.currentText():
                    self.image_paths.append(img_path)
            except:
                rating = None
        self.display_images()

    def set_grid_metadata(self, img_path):
        if not img_path in self.image_paths:
            return
        
        exif_dict = piexif.load(img_path)
        rating = exif_dict["0th"].get(18246, None)
        index = self.image_paths.index(img_path)
        # Get the widget from the layout
        vbox = self.grid_layout.itemAt(index).widget()  # Get the QWidget from the layout
        # Retrieve the layout from the QWidget
        vbox_layout = vbox.layout()  # Get the QVBoxLayout from the QWidget
        stars_label = vbox_layout.itemAt(1).widget()  # The second widget, which is the stars label
        line = os.path.basename(img_path)
        line = "\u200b".join(line)
        line += "\n"
        line += self.star_numbers(rating)
        # Update star info
        stars_label.setText(line)      

        label = vbox_layout.itemAt(0).widget()
        label.mousePressEvent = lambda event, path=img_path, lbl=label: self.label_clicked(event, path, lbl)

    def set_metadata_panel(self, img_path):
        if self.full_image_label.isVisible() and self.current_full_image == img_path:
            exif_dict = piexif.load(img_path)
            rating = exif_dict["0th"].get(18246, None)
            date = datetime.datetime.fromtimestamp(os.path.getctime(img_path)).strftime("%d-%m-%Y")
            highlights, improvements, aesthetic_score = self.aesthetic_comments(exif_dict)
            line = os.path.basename(img_path)
            self.image_name_label.setText("\u200b".join(line))
            self.date_label.setText(date)
            self.rating_label.setText(self.star_numbers(rating)) 
            self.aesthetic_score_label.setText(str(aesthetic_score)) 
            self.aesthetic_highlights_label.setText(highlights)
            self.potential_improvements_label.setText(improvements) 

    def analyse_images(self):
        if not self.image_paths:
            QMessageBox.warning(self, "No Images Found", "No images found!", QMessageBox.Ok)
            return
        
        button_reply = QMessageBox.question(self, 'Confirm Action', "Would You like to Analyse All Shown Images?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if button_reply == QMessageBox.No:
            return
        
        progress = QProgressDialog("Analysing images...", "Cancel", 0, len(self.image_paths), self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)  # Show immediately compared to default of 4 secs

        i = 0
        for img_path in self.image_paths:
            progress.setValue(i)
            if progress.wasCanceled():
                break

            self.edit_flag = True
            img_path = predict_image(img_path)
            self.set_metadata_panel(img_path)
            self.set_grid_metadata(img_path)
            i += 1

        progress.setValue(len(self.image_paths))
        self.clearSelectedImages()

    def analyse_current_image(self):
        if self.current_index < 0 or self.current_index >= len(self.image_paths):
            return
        
        button_reply = QMessageBox.question(self, 'Confirm Action', "Would You like to Analyse Current Image?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if button_reply == QMessageBox.No:
            return
        
        progress = QProgressDialog("Analysing images...", "Cancel", 0, 1, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)  # Show immediately compared to default of 4 secs

        self.edit_flag = True
        img_path = self.current_full_image  # Get the current image
        img_path = predict_image(img_path)
        self.set_metadata_panel(img_path)
        self.set_grid_metadata(img_path)

        progress.setValue(1)
        self.clearSelectedImages()

    def analyse_selected_images(self):
        if not self.selected_images:
            QMessageBox.warning(self, "No Images Found", "No images found!", QMessageBox.Ok)
            return
        
        button_reply = QMessageBox.question(self, 'Confirm Action', "Would You like to Analyse Selected Images?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if button_reply == QMessageBox.No:
            return
        
        progress = QProgressDialog("Analysing images...", "Cancel", 0, len(self.selected_images), self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)  # Show immediately compared to default of 4 secs

        i = 0
        for img_path in self.selected_images:
            progress.setValue(i)
            if progress.wasCanceled():
                break

            self.edit_flag = True
            img_path = predict_image(img_path)
            self.set_metadata_panel(img_path)
            self.set_grid_metadata(img_path)
            i += 1

        progress.setValue(len(self.selected_images))
        self.clearSelectedImages()

    def save_changes(self):
        button_reply = QMessageBox.question(self, 'Confirm Action', "Would You like to Save Changes?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if button_reply == QMessageBox.No:
            return
        
        img_path = self.current_full_image
        directory = os.path.dirname(img_path)
        new_path = os.path.join(directory, self.edit_image_name.text())

        try:
            os.rename(img_path, new_path)
        except FileExistsError:
            QMessageBox.critical(None, "Rename Error", "File already exists at:\n" + new_path)
            return
        except Exception as e:
            QMessageBox.critical(None, "Rename Error", "An unexpected error occurred")
            return
            
        # Update paths inside image_paths and all_image_paths
        if img_path in self.image_paths:
            index = self.image_paths.index(img_path)
            self.image_paths[index] = new_path
        
        if img_path in self.all_image_paths:
            index = self.all_image_paths.index(img_path)
            self.all_image_paths[index] = new_path

        save_changes(new_path, self.edit_rating.value())
        self.current_full_image = new_path
        self.set_grid_metadata(new_path)
        self.set_metadata_panel(new_path)
        self.clearSelectedImages()

    def delete_image(self):
        button_reply = QMessageBox.question(self, 'Confirm Action', "Would You like to Delete Image?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if button_reply == QMessageBox.No:
            return
    
        img_path = self.current_full_image
        path = os.path.abspath(img_path)
        send2trash(path) # Send to trash instead of actual deletion incase of a mistake

        if img_path in self.image_paths:
            self.image_paths.remove(img_path)
        if img_path in self.all_image_paths:
            self.all_image_paths.remove(img_path)

        self.clearSelectedImages()
        self.filtered_flag = False
        self.image_paths = self.all_image_paths.copy()

        if len(self.image_paths) == 0:
            self.clearLayout(self.grid_layout)

        self.display_images() 
        self.full_image_label.setVisible(False)  # Hide the full image
        self.prev_btn.setVisible(False)  # Hide the navigation buttons
        self.next_btn.setVisible(False)
        self.metadata_panel.setVisible(False)
        self.analyse_current_btn.setVisible(False) # Hide analyse button
        self.filter_btn.setVisible(True)
        self.filter_value.setVisible(True)  

    def clearSelectedImages(self):
        for selected_images in self.selected_images:
            index = self.image_paths.index(selected_images)
            # Get the widget from the layout
            vbox = self.grid_layout.itemAt(index).widget()  # Get the QWidget from the layout
            # Retrieve the layout from the QWidget
            vbox_layout = vbox.layout()  # Get the QVBoxLayout from the QWidget
            image_label = vbox_layout .itemAt(0).widget()  # The first widget, which is the image label
            image_label.setStyleSheet("")
        self.selected_images.clear()

    def star_numbers(self, number):
        if number == None:
            return "☆☆☆☆☆"
        if number == 1:
            return "★☆☆☆☆"
        if number == 2:
            return "★★☆☆☆"
        if number == 3:
            return "★★★☆☆"
        if number == 4:
            return "★★★★☆"
        if number == 5:
            return "★★★★★"

    def aesthetic_comments(self, exif_dict):
        highlights = ""
        improvements = ""
        score = ""

        try:
            user_comment = piexif.helper.UserComment.load(exif_dict["Exif"][piexif.ExifIFD.UserComment])
        except:
            user_comment = None
            return "", "", None
        
        # Convert string to dictionary
        dict_obj = json.loads(user_comment)

        if dict_obj['fc9_BalancingElement'] >= 0.10:
            highlights += 'Balanced elements\n'
        if dict_obj['fc9_BalancingElement'] <= -0.1:
            improvements += 'Unbalanced elements.\n'

        if dict_obj['fc9_ColorHarmony'] >= 0.10:
            highlights += 'Colour harmony \n'
        if dict_obj['fc9_ColorHarmony'] <= -0.1:
            improvements += 'Bad colour combination.\n'
        
        if dict_obj['fc9_Content'] >= 0.10:
            highlights += 'Interesting content.\n'
        if dict_obj['fc9_Content'] <= -0.1:
            improvements += 'Boring content.\n'

        if dict_obj['fc9_DoF'] >= 0.10:
            highlights += 'Good Depth of Field.\n'
        if dict_obj['fc9_DoF'] <= -0.1:
            improvements += 'Out of Focus on Foreground.\n'

        if dict_obj['fc9_Light'] >= 0.10:
            highlights += 'Interesting lighting.\n'
        if dict_obj['fc9_Light'] <= -0.1:
            improvements += 'Bad lighting.\n'

        if dict_obj['fc9_MotionBlur'] >= 0.10:
            highlights += 'Good motion blur.\n'
        if dict_obj['fc9_MotionBlur'] <= -0.1:
            improvements += 'Undesired motion blur.\n'

        if dict_obj['fc9_Object'] >= 0.10:
            highlights += 'Clear/emphasized object.\n'
        if dict_obj['fc9_Object'] <= -0.1:
            improvements += 'No object emphasis.\n'

        if dict_obj['fc9_Repetition'] >= 0.10:
            highlights += 'Repeated pattern.\n'

        if dict_obj['fc9_Symmetry'] >= 0.10:
            highlights += 'Symmetry pattern.\n'

        if dict_obj['fc9_RuleOfThirds'] >= 0.10:
            highlights += 'Good usage of Rule of Thirds\n'
        if dict_obj['fc9_RuleOfThirds'] <= -0.1:
            improvements += 'Bad component placement(Rule of Thirds).\n'

        if dict_obj['fc9_VividColor'] >= 0.10:
            highlights += 'Vivid colour.\n'
        if dict_obj['fc9_VividColor'] <= -0.1:
            improvements += 'Dull/boring colour.\n'

        score = int(dict_obj['fc11_score']*100)

        return highlights, improvements, score

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
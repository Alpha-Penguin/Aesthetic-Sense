import sys
import os
from pathlib import Path
import piexif
import json

from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QLabel, \
    QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog, QGridLayout, QScrollArea, \
    QTextEdit, QFileSystemModel, QTreeView, QTreeWidget, QAction, QGraphicsView, QSizePolicy, QMessageBox, \
    QFormLayout, QComboBox, QLineEdit, QGroupBox, QSizePolicy, QSpinBox
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QDir

from model import predict_image

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.all_image_paths = []
        self.image_paths = []  # List to store image paths being used
        self.current_index = -1  # Track current image index, start with -1 (no image selected)
        self.is_initialized = False  # Flag to check if the gallery is initialized
        self.selected_images = set()  # Store selected images

        self.setWindowTitle("MainWindow")
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

        self.analyse_selected_btn = QPushButton("Analyse Selected")
        self.analyse_selected_btn.clicked.connect(self.analyse_selected_images)
        self.analyse_selected_btn.setVisible(False)  # Hidden initially

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
        self.full_image_label.setFixedSize(900, 700)  # Set fixed size for full image
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

    def load_folder(self):
        """Open a dialog to select a folder and show files inside while browsing."""
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")

        if folder:
            # Load all images from the selected folder
            self.image_paths = [os.path.join(folder, f) for f in os.listdir(folder) 
                                if f.lower().endswith(('.jpg', '.jpeg'))]

            if not self.image_paths:
                QMessageBox.warning(self, "No Images Found", "No images found in the selected folder!", QMessageBox.Ok)
                return
            
            self.all_image_paths = self.image_paths.copy()
            self.setTree(folder)
            self.analyse_btn.setVisible(True) 
            self.analyse_selected_btn.setVisible(True)
            self.filter_btn.setVisible(True)  
            self.filter_value.setVisible(True)  
            self.display_images()

    def load_files(self):
        """Open a dialog to select a folder and show files inside while browsing."""
        files, files_types = QFileDialog.getOpenFileNames(None, "Select Files", "", "Images (*.jpg *.jpeg)")
        print(files)
        self.image_paths = files

        if not self.image_paths:
            QMessageBox.warning(self, "No Images Found", "No images found in the selected folder!", QMessageBox.Ok)
            return
            
        self.all_image_paths = self.image_paths.copy()
        self.analyse_btn.setVisible(True) 
        self.analyse_selected_btn.setVisible(True)
        self.filter_btn.setVisible(True)  
        self.filter_value.setVisible(True)  
        self.display_images()


    def display_images(self):
        """Displays images in a grid format with borders and padding."""
        if not self.image_paths:
            QMessageBox.warning(self, "No Images Found", "No images found!", QMessageBox.Ok)
            return

        self.current_index = 0  # Set to first image index
        self.is_initialized = True  # Mark as initialized
        # Initially hide the full image
        self.full_image_label.setVisible(False)
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

    def switch_gallery_layout(self, layout_type):
        """Switch between grid (multi-row) and column layout (single-column)."""
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

    def clearLayout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clearLayout(item.layout())

    def label_clicked(self, event, path, lbl):
        if event.button() == Qt.LeftButton and not event.modifiers():  
            self.toggle_full_image(path)  # (show/hide full image)
        elif  event.modifiers() & Qt.ControlModifier:  # Ctrl + Click
            self.toggle_selection(path, lbl) 

    def toggle_selection(self, img_path, label):
        """Toggles selection of an image on Ctrl+Click."""
        if img_path in self.selected_images:
            self.selected_images.remove(img_path)
            label.setStyleSheet("")  # Normal
        else:
            self.selected_images.add(img_path)
            label.setStyleSheet("background-color: lightblue; border: solid blue;")  # Highlighted

    def toggle_full_image(self, img_path):
        """Toggles visibility of the full image."""
        if self.full_image_label.isVisible() and self.image_paths[self.current_index] == img_path:
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
        """Displays the selected image in full size within a fixed label size."""
        exif_dict = piexif.load(img_path)
        rating = exif_dict["0th"].get(18246, None)
        aesthetic_score = exif_dict["0th"].get(18249, None)

        pixmap = QPixmap(img_path)
        # Scale the image to fit within the fixed label size (800x600)
        scaled_pixmap = pixmap.scaled(self.full_image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        # Set the scaled image to the label
        self.full_image_label.setPixmap(scaled_pixmap)
        self.current_index = self.image_paths.index(img_path)
        self.full_image_label.setVisible(True)  # Show the full image
        self.metadata_panel.setVisible(True)
        self.analyse_current_btn.setVisible(True)  # Show button when image is displayed

        highlights, improvements = self.aesthetic_comments(exif_dict)
        line = os.path.basename(img_path)
        self.image_name_label.setText("\u200b".join(line))
        self.date_label.setText("")
        self.rating_label.setText(self.star_numbers(rating)) 
        self.aesthetic_score_label.setText(str(aesthetic_score)) 
        self.aesthetic_highlights_label.setText(highlights)
        self.potential_improvements_label.setText(improvements) 
           
    def addImage(self, img_path, row, col):
        exif_dict = piexif.load(img_path)
        rating = exif_dict["0th"].get(18246, None)

        # Load and scale image while keeping aspect ratio
        img = QPixmap(img_path).scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        vbox = QVBoxLayout()
        # Create a fixed-size label with grey background
        label = QLabel()
        label.setFixedSize(320, 320)
        # Center image within label
        label.setPixmap(img)
        label.setAlignment(Qt.AlignCenter | Qt.AlignTop)
        # Create stars label (placeholder for now)
        line = os.path.basename(img_path)
        line = "\u200b".join(line)
        line += "\n"
        line += self.star_numbers(rating)
        stars_label = QLabel(line)  # Replace with actual star rating ⭐⭐⭐⭐⭐ ★★★★
        stars_label.setWordWrap(True)
        stars_label.setStyleSheet("background-color: lightgrey; border: solid blue; padding: 0px; border-radius: 10px;")
        stars_label.setAlignment(Qt.AlignCenter | Qt.AlignTop)    
        # Adjust size of the stars label to fit its content
        stars_label.setFixedWidth(320)  # Match the width to the image label
        stars_label.setFixedHeight(50)  # Adjust the height as needed based on font size

        vbox.addWidget(label)
        vbox.addWidget(stars_label)

        label.mousePressEvent = lambda event, path=img_path, lbl=label: self.label_clicked(event, path, lbl)

        widget = QWidget()
        widget.setLayout(vbox)
        widget.setStyleSheet("background-color: grey; border: solid blue; padding: 0px; border-radius: 10px;")
        self.grid_layout.addWidget(widget, row, col)

    def show_previous(self):
        """Shows the previous image in full size."""
        if self.image_paths and self.current_index > 0:
            self.current_index -= 1
            if self.full_image_label.isVisible():
                self.show_full_image(self.image_paths[self.current_index])
            else:
                self.toggle_full_image(self.image_paths[self.current_index])

    def show_next(self):
        """Shows the next image in full size."""
        if self.image_paths and self.current_index < len(self.image_paths) - 1:
            self.current_index += 1
            if self.full_image_label.isVisible():
                self.show_full_image(self.image_paths[self.current_index])
            else:
                self.toggle_full_image(self.image_paths[self.current_index])

    def on_item_clicked(self, index):
        file_path = self.model.filePath(index)

        # Replace the last forward slash with a backslash
        file_path = file_path.rsplit('/', 1)
        if len(file_path) > 1:
            file_path = file_path[0] + '\\' + file_path[1]
        else:
            file_path = file_path[0]  # in case there's no forward slash in the path
        self.toggle_full_image(file_path)

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

    def analyse_images(self):
        """This method will trigger image analysis for selected images."""
        if not self.image_paths:
            print("No images loaded!")
            return

        for img_path in self.image_paths:
            print("img_path: " + img_path)
            img_path = predict_image(img_path)
            self.set_metadata_panel(img_path)
        self.clearSelectedImages()

    def analyse_current_image(self):
        """Analyse only the currently displayed image."""
        if self.current_index < 0 or self.current_index >= len(self.image_paths):
            print("No image selected for analysis!")
            return

        img_path = self.image_paths[self.current_index]  # Get the current image
        print("img_path: " + img_path)
        img_path = predict_image(img_path)
        self.set_metadata_panel(img_path)

        self.clearSelectedImages()

    def analyse_selected_images(self):
        """Analyses only selected images."""
        if not self.selected_images:
            print("No images selected for analysis.")
            return

        for img_path in self.selected_images:
            print("img_path: " + img_path)
            img_path = predict_image(img_path)

            self.set_metadata_panel(img_path)

    
        self.clearSelectedImages()

    def load_filtered_images(self):
        #self.image_paths = self.all_image_paths.copy()
        #self.image_paths = [self.image_paths[1]]
        print("value =" )
        print(self.filter_value.currentText())

        self.image_paths = []
        if (self.filter_value.currentText() == "No Filter"):
            self.image_paths = self.all_image_paths.copy()
            self.display_images()
            return
        
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
            print(rating)

        #print(self.image_paths)
        self.display_images()

        self.image_paths = self.all_image_paths.copy()

    def set_metadata_panel(self, img_path):
        exif_dict = piexif.load(img_path)
        rating = exif_dict["0th"].get(18246, None)
        aesthetic_score = exif_dict["0th"].get(18249, None)
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
        stars_label.setText(line)  # For example, update the text (or star rating)

        if self.full_image_label.isVisible() and self.image_paths[self.current_index] == img_path:
            highlights, improvements = self.aesthetic_comments(exif_dict)
            line = os.path.basename(img_path)
            self.image_name_label.setText("\u200b".join(line))
            self.date_label.setText("")
            self.rating_label.setText(self.star_numbers(rating)) 
            self.aesthetic_score_label.setText(str(aesthetic_score)) 
            self.aesthetic_highlights_label.setText(highlights)
            self.potential_improvements_label.setText(improvements)      


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

        try:
            user_comment = piexif.helper.UserComment.load(exif_dict["Exif"][piexif.ExifIFD.UserComment])
        except:
            user_comment = None
            return "", ""
        
        # Convert string to dictionary
        dict_obj = json.loads(user_comment)
        print(dict_obj)
        print(dict_obj['fc9_VividColor'])

#-Start comments

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

        return highlights, improvements



if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
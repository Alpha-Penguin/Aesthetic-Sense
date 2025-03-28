import sys
import os
from pathlib import Path

from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QLabel, \
    QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog, QGridLayout, QScrollArea, \
    QTextEdit, QFileSystemModel, QTreeView, QTreeWidget, QAction, QGraphicsView, QSizePolicy, QMessageBox, \
    QFormLayout, QComboBox, QLineEdit, QGroupBox, QSizePolicy
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QDir

from model import predict_image, predict_multiple_images

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.image_paths = []  # List to store image paths
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

        self.analyse_bar.addWidget(self.analyse_btn)
        self.analyse_bar.addWidget(self.analyse_current_btn)
        self.analyse_bar.addWidget(self.analyse_selected_btn)

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
        #self.metadata_panel.setReadOnly(True)
        self.image_name_label = QLabel("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaabbba")
        self.image_name_label.setWordWrap(True)
        self.image_name_label.setMinimumWidth(50)
        self.image_name_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        line = "This is a high-aesthetic image"
        line += "\nHas balanced elements"
        line += "\nGood usage of rule of thirds"
        line += "\nGood usage of rule of thirds"
        line += "\nGood usage of rule of thirds"
        line += "\nGood usage of rule of thirds"
        line += "\nGood usage of rule of thirds"

        self.metadata_panel_form.addRow(QLabel("Image Name:"), self.image_name_label)
        self.metadata_panel_form.addRow(QLabel("Date:"),QLabel("12/05/11"))
        self.metadata_panel_form.addRow(QLabel("Rating:"),QLabel("*****"))
        self.metadata_panel_form.addRow(QLabel("Tech Score:"),QLabel("*****"))
        self.metadata_panel_form.addRow(QLabel("Aesthetic Score:"),QLabel("*****"))
        self.metadata_panel_form.addRow(QLabel("Followed \nAesthetic Rules:"),QLabel(line))
        self.metadata_panel_form.addRow(QLabel("Advice:"),QLabel("Has Bad color combinations"))

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
        self.Load_Folder.triggered.connect(self.load_images)
        self.menuFile.addAction(self.Load_Folder)

    def load_images(self):
        """Open a dialog to select a folder and show files inside while browsing."""
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")

        if folder:
            # Load all images from the selected folder
            self.image_paths = [os.path.join(folder, f) for f in os.listdir(folder) 
                                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]

            if not self.image_paths:
                QMessageBox.warning(self, "No Images Found", "No images found in the selected folder!", QMessageBox.Ok)
                return

            self.setTree(folder)
            self.analyse_btn.setVisible(True) 
            self.analyse_selected_btn.setVisible(True)
            self.display_images()


    def display_images(self):
        """Displays images in a grid format with borders and padding."""
        if not self.image_paths:
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
        elif self.full_image_label.isVisible():
            self.show_full_image(img_path)
            self.clearSelectedImages()
        else:
            self.show_full_image(img_path)  # Show the selected full image
            self.switch_gallery_layout('single-column')
            self.prev_btn.setVisible(True)  # Show the navigation buttons
            self.next_btn.setVisible(True)

    def show_full_image(self, img_path):
        """Displays the selected image in full size within a fixed label size."""
        pixmap = QPixmap(img_path)
        # Scale the image to fit within the fixed label size (800x600)
        scaled_pixmap = pixmap.scaled(self.full_image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        # Set the scaled image to the label
        self.full_image_label.setPixmap(scaled_pixmap)
        self.current_index = self.image_paths.index(img_path)
        self.full_image_label.setVisible(True)  # Show the full image
        self.metadata_panel.setVisible(True)
        self.analyse_current_btn.setVisible(True)  # Show button when image is displayed
    
    def addImage(self, img_path, row, col):

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
        line += "\n ****a"
        stars_label = QLabel(line)  # Replace with actual star rating ⭐⭐⭐⭐⭐
        stars_label.setStyleSheet("background-color: lightgrey; border: solid blue; padding: 0px; border-radius: 10px;")
        stars_label.setAlignment(Qt.AlignCenter | Qt.AlignTop)    
        # Adjust size of the stars label to fit its content
        stars_label.setFixedWidth(320)  # Match the width to the image label
        stars_label.setFixedHeight(30)  # Adjust the height as needed based on font size

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
        # Get the widget from the layout
        vbox = self.grid_layout.itemAt(0).widget()  # Get the QWidget from the layout
        # Retrieve the layout from the QWidget
        vbox_layout = vbox.layout()  # Get the QVBoxLayout from the QWidget
        stars_label = vbox_layout .itemAt(1).widget()  # The second widget, which is the stars label
        line = os.path.basename(file_path)
        line += "\n ⭐⭐⭐⭐⭐"
        # Update star info
        stars_label.setText(line)  # For example, update the text (or star rating)


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
            img_path, pred_score = predict_image(img_path)
        self.clearSelectedImages()
            

    def analyse_current_image(self):
        """Analyse only the currently displayed image."""
        if self.current_index < 0 or self.current_index >= len(self.image_paths):
            print("No image selected for analysis!")
            return

        img_path = self.image_paths[self.current_index]  # Get the current image
        print("img_path: " + img_path)
        img_path, pred_score = predict_image(img_path)

        self.clearSelectedImages()
        # Display the score near the full image
        #self.full_image_label.setToolTip("Score:" + str(pred_score))  # Hover text with score

    def analyse_selected_images(self):
        """Analyses only selected images."""
        if not self.selected_images:
            print("No images selected for analysis.")
            return

        for img_path in self.selected_images:
            print("img_path: " + img_path)
            img_path, pred_score = predict_image(img_path)

    
        self.clearSelectedImages()

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFileDialog, QGridLayout, QScrollArea
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

from model import predict_image, predict_multiple_images

class ImageGallery(QWidget):
    def __init__(self):
        super().__init__()
        self.image_paths = []  # List to store image paths
        self.current_index = -1  # Track current image index, start with -1 (no image selected)
        self.is_initialized = False  # Flag to check if the gallery is initialized

        self.selected_images = set()  # Store selected images
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Image Gallery Viewer")
        self.setGeometry(100, 100, 1000, 800)  # Fixed window size

        # Layouts
        main_layout = QHBoxLayout()  # Horizontal layout for side-by-side display
        self.grid_layout = QGridLayout()

        # Scroll Area for Images
        self.scroll_area = QScrollArea()
        self.scroll_widget = QWidget()
        self.scroll_widget.setLayout(self.grid_layout)
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)

        # Buttons
        self.load_btn = QPushButton("Load Images")
        self.load_btn.clicked.connect(self.load_images)

        self.analyze_btn = QPushButton("Analyze Images")  # New button to trigger analysis
        self.analyze_btn.clicked.connect(self.analyze_images)  # Connect button to function

        self.analyze_current_btn = QPushButton("Analyze This Image")  # New button For Single Image
        self.analyze_current_btn.clicked.connect(self.analyze_current_image)
        self.analyze_current_btn.setVisible(False)  # Hidden initially

        self.analyze_selected_btn = QPushButton("Analyze Selected")
        self.analyze_selected_btn.clicked.connect(self.analyze_selected_images)

        # Full-Size Image Viewer
        self.full_image_label = QLabel()
        self.full_image_label.setAlignment(Qt.AlignCenter)
        self.full_image_label.setStyleSheet("border: 2px solid black;")  # Border around full image
        self.full_image_label.setFixedSize(800, 600)  # Set fixed size for full image
        self.full_image_label.setVisible(False)  # Initially hidden

        main_layout.addWidget(self.analyze_current_btn)

        # Navigation buttons
        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("Previous")
        self.next_btn = QPushButton("Next")
        self.prev_btn.clicked.connect(self.show_previous)
        self.next_btn.clicked.connect(self.show_next)

        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.next_btn)

        # Add widgets to gallery layout
        gallery_layout = QVBoxLayout()  # For the gallery section
        gallery_layout.addWidget(self.load_btn)
        gallery_layout.addWidget(self.scroll_area)
        gallery_layout.addLayout(nav_layout)  # Using addLayout() instead of addWidget()
        main_layout.addWidget(self.analyze_btn) # ADD ANALYSE
        main_layout.addWidget(self.analyze_selected_btn) # Add Select Analyse

        # Add the gallery layout and the full image layout side by side
        main_layout.addLayout(gallery_layout)  # Gallery/grid on left
        main_layout.addWidget(self.full_image_label)  # Full-size image on right

        self.setLayout(main_layout)

        # Initially hide navigation buttons
        self.prev_btn.setVisible(False)
        self.next_btn.setVisible(False)

    def load_images(self):
        """Open a dialog to select a folder and show files inside while browsing."""
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")

        if folder:
            # Load all images from the selected folder
            self.image_paths = [os.path.join(folder, f) for f in os.listdir(folder) 
                                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]

            if not self.image_paths:
                print("No images found in the selected folder!")
                return

            self.display_images()

    def display_images(self):
        """Displays images in a grid format with borders and padding."""
        for i in reversed(range(self.grid_layout.count())):  # Clear previous images
            self.grid_layout.itemAt(i).widget().setParent(None)

        if not self.image_paths:
            return

        self.current_index = 0  # Set to first image index
        self.is_initialized = True  # Mark as initialized
        # Initially hide the full image
        self.full_image_label.setVisible(False)
        self.switch_gallery_layout('multi-row')

        # Display thumbnails with borders and grey padding
        row, col = 0, 0
        thumbnail_size = 200  # Fixed size for consistency

        for img_path in self.image_paths:
            # Load and scale image while keeping aspect ratio
            img = QPixmap(img_path).scaled(thumbnail_size - 20, thumbnail_size - 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)

            # Create a fixed-size label with grey background
            label = QLabel()
            label.setFixedSize(thumbnail_size, thumbnail_size)
            label.setStyleSheet("background-color: grey; border: 2px solid black;")  # Grey padding and border

            # Center image within label
            label.setPixmap(img)
            label.setAlignment(Qt.AlignCenter)


            # Mouse event for selection and full image
            #def mousePressEvent(event, path=img_path, lbl=label):
            #    if event.modifiers() & Qt.ControlModifier:  # Ctrl + Click
            #        self.toggle_selection(path, lbl)
            #    else:
            #        self.show_full_image(path)

            #label.mousePressEvent = mousePressEvent

            #label.mousePressEvent = lambda event, path=img_path, lbl=label: label_clicked(event, path, lbl)

            def label_clicked(event, path, lbl):
                if event.button() == Qt.LeftButton and not event.modifiers():  
                    self.toggle_full_image(path)  # Existing behavior (show/hide full image)
                #elif event.button() == Qt.LeftButton and event.modifiers() == Qt.ControlModifier:
                #    self.toggle_selection(path, lbl)  # New: Ctrl+Click for selection
                elif  event.modifiers() & Qt.ControlModifier:  # Ctrl + Click
                    self.toggle_selection(path, lbl)

            label.mousePressEvent = lambda event, path=img_path, lbl=label: label_clicked(event, path, lbl)
         


            # Allow clicking to show/hide full-size image
            #label.mousePressEvent = lambda event, path=img_path: self.toggle_full_image(path)

            self.grid_layout.addWidget(label, row, col)
            col += 1
            if col >= 5:  # 5 images per row
                col = 0
                row += 1

    def toggle_full_image(self, img_path):
        """Toggles visibility of the full image."""
        if self.full_image_label.isVisible() and self.image_paths[self.current_index] == img_path:
            self.full_image_label.setVisible(False)  # Hide the full image
            self.switch_gallery_layout('multi-row')
            self.prev_btn.setVisible(False)  # Hide the navigation buttons
            self.next_btn.setVisible(False)

            self.analyze_current_btn.setVisible(False) # Hide analyse button? 
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

        self.analyze_current_btn.setVisible(True)  # Show button when image is displayed

    def switch_gallery_layout(self, layout_type):
        """Switch between grid (multi-row) and column layout (single-column)."""
        for i in reversed(range(self.grid_layout.count())):  # Clear previous layout
            self.grid_layout.itemAt(i).widget().setParent(None)
            self.selected_images.clear()


        if layout_type == 'multi-row':
            self.grid_layout.setRowStretch(0, 1)  # Stretch first row
            row, col = 0, 0
            thumbnail_size = 200  # Fixed size for consistency

            for img_path in self.image_paths:
                # Load and scale image while keeping aspect ratio
                img = QPixmap(img_path).scaled(thumbnail_size - 20, thumbnail_size - 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)

                # Create a fixed-size label with grey background
                label = QLabel()
                label.setFixedSize(thumbnail_size, thumbnail_size)
                label.setStyleSheet("background-color: grey; border: 2px solid black;")  # Grey padding and border

                # Center image within label
                label.setPixmap(img)
                label.setAlignment(Qt.AlignCenter)

                # Allow clicking to show/hide full-size image
                label.mousePressEvent = lambda event, path=img_path: self.toggle_full_image(path)

                def label_clicked(event, path, lbl):
                    if event.button() == Qt.LeftButton and not event.modifiers():  
                        self.toggle_full_image(path)  # Existing behavior (show/hide full image)
                    #elif event.button() == Qt.LeftButton and event.modifiers() == Qt.ControlModifier:
                    #    self.toggle_selection(path, lbl)  # New: Ctrl+Click for selection
                    elif  event.modifiers() & Qt.ControlModifier:  # Ctrl + Click
                        self.toggle_selection(path, lbl)

                label.mousePressEvent = lambda event, path=img_path, lbl=label: label_clicked(event, path, lbl)

                self.grid_layout.addWidget(label, row, col)
                col += 1
                if col >= 5:  # 5 images per row
                    col = 0
                    row += 1

        elif layout_type == 'single-column':
            self.grid_layout.setRowStretch(0, 1)  # Stretch first row
            row = 0
            col = 0
            for img_path in self.image_paths:
                img = QPixmap(img_path).scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                label = QLabel()
                label.setPixmap(img)
                label.setFixedSize(200, 200)
                label.setStyleSheet("background-color: grey; border: 2px solid black;")
                label.setAlignment(Qt.AlignCenter)
                label.mousePressEvent = lambda event, path=img_path: self.toggle_full_image(path)

                def label_clicked(event, path, lbl):
                    if event.button() == Qt.LeftButton and not event.modifiers():  
                        self.toggle_full_image(path)  # Existing behavior (show/hide full image)
                    #elif event.button() == Qt.LeftButton and event.modifiers() == Qt.ControlModifier:
                    #    self.toggle_selection(path, lbl)  # New: Ctrl+Click for selection
                    elif  event.modifiers() & Qt.ControlModifier:  # Ctrl + Click
                        self.toggle_selection(path, lbl)

                label.mousePressEvent = lambda event, path=img_path, lbl=label: label_clicked(event, path, lbl)

                self.grid_layout.addWidget(label, row, col)
                row += 1

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

    def analyze_images(self):
        """This method will trigger image analysis for selected images."""
        if not self.image_paths:
            print("No images loaded!")
            return

        for img_path in self.image_paths:
            # Call your existing image analysis function here
            # This is where you'll integrate your model's `predict_image` function
            #img_path, pred_score = predict_image(img_path)  # Assuming you have this function defined
            #print(f"Image: {img_path}, Predicted Score: {pred_score}")
            print("img_path: " + img_path)
            img_path, pred_score = predict_image(img_path)
            
            # Optionally, display the predicted score (e.g., stars or rating) below the image
            # You can add a QLabel or a custom widget with the result in the grid layout.

    def analyze_current_image(self):
        """Analyze only the currently displayed image."""
        if self.current_index < 0 or self.current_index >= len(self.image_paths):
            print("No image selected for analysis!")
            return

        img_path = self.image_paths[self.current_index]  # Get the current image
        #img_path, pred_score = predict_image(img_path)  # Run model on this image

        print("img_path: " + img_path)
        img_path, pred_score = predict_image(img_path)
        # Optionally display the score near the full image
        #self.full_image_label.setToolTip("Score:" + str(pred_score))  # Hover text with score

    def analyze_selected_images(self):
        """Analyzes only selected images."""
        if not self.selected_images:
            print("No images selected for analysis.")
            return

        for img_path in self.selected_images:
            #print(f"Analyzing {img_path}...")  # Replace this with actual model processing
            print("img_path: " + img_path)
            img_path, pred_score = predict_image(img_path)

        for i in range(self.grid_layout.count()):
            widget = self.grid_layout.itemAt(i).widget()
            if isinstance(widget, QLabel):
                widget.setStyleSheet("background-color: grey; border: 2px solid black;")  # Reset style
        
 

        self.selected_images.clear()


    def toggle_selection(self, img_path, label):
        """Toggles selection of an image on Ctrl+Click."""
        if img_path in self.selected_images:
            self.selected_images.remove(img_path)
            label.setStyleSheet("background-color: grey; border: 2px solid black;")  # Normal
        else:
            self.selected_images.add(img_path)
            label.setStyleSheet("background-color: lightblue; border: 2px solid blue;")  # Highlighted



if __name__ == "__main__":
    app = QApplication(sys.argv)
    gallery = ImageGallery()
    gallery.show()
    sys.exit(app.exec_())

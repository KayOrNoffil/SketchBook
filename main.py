import sys
import sqlite3
import datetime
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, QFileDialog, QColorDialog, QDialog, QVBoxLayout, \
    QLabel, QLineEdit, QPushButton, QToolBar, QMessageBox, QComboBox
from PyQt5.QtGui import QPainter, QPen, QImage, QColor, QIcon, QPolygon
from PyQt5.QtCore import Qt, QPoint, QRect


class Database:
    def __init__(self):
        current_datetime = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        self.db_name = f"user_actions_{current_datetime}.db"
        self.connection = sqlite3.connect(self.db_name)
        self.create_table()

    def create_table(self):
        cursor = self.connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.connection.commit()

    def add_action(self, action):
        cursor = self.connection.cursor()
        cursor.execute('INSERT INTO actions (action) VALUES (?)', (action,))
        self.connection.commit()

    def get_actions(self):
        cursor = self.connection.cursor()
        cursor.execute('SELECT * FROM actions')
        return cursor.fetchall()

    def delete_last_action(self):
        cursor = self.connection.cursor()
        cursor.execute('DELETE FROM actions WHERE id = (SELECT MAX(id) FROM actions)')
        self.connection.commit()


class CanvasSizeDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Set Canvas Size")
        self.layout = QVBoxLayout()
        self.width_input = QLineEdit(self)
        self.height_input = QLineEdit(self)
        self.layout.addWidget(QLabel("Width:"))
        self.layout.addWidget(self.width_input)
        self.layout.addWidget(QLabel("Height:"))
        self.layout.addWidget(self.height_input)
        self.ok_button = QPushButton("OK", self)
        self.ok_button.clicked.connect(self.accept)
        self.layout.addWidget(self.ok_button)
        self.setLayout(self.layout)

    def get_size(self):
        return int(self.width_input.text()), int(self.height_input.text())


class PaintApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sketchbook")
        self.db = Database()
        self.init_canvas_size()
        self.image = QImage(self.size(), QImage.Format_RGB32)
        self.image.fill(Qt.white)
        self.drawing = False
        self.pen_color = Qt.black
        self.pen_size = 2  # Default brush size
        self.brush_type = "Normal Brush"
        self.shape_type = "Free Drawing"
        self.last_point = QPoint()
        self.start_point = QPoint()
        self.init_ui()

    def init_canvas_size(self):
        dialog = CanvasSizeDialog()
        if dialog.exec_() == QDialog.Accepted:
            width, height = dialog.get_size()
            self.setGeometry(100, 100, width, height)
            self.image = QImage(width, height, QImage.Format_RGB32)
            self.image.fill(Qt.white)

    def init_ui(self):
        toolbar = QToolBar(self)
        self.addToolBar(toolbar)

        clear_action = QAction(QIcon('icons/clear.png'), 'Clear', self)
        clear_action.triggered.connect(self.clear_canvas)
        save_action = QAction(QIcon('icons/save.png'), 'Save', self)
        save_action.triggered.connect(self.save_image)
        open_action = QAction(QIcon('icons/open.png'), 'Open', self)
        open_action.triggered.connect(self.open_image)
        color_action = QAction(QIcon('icons/color.png'), 'Color', self)
        color_action.triggered.connect(self.choose_color)
        history_action = QAction(QIcon('icons/history.png'), 'Show History', self)
        history_action.triggered.connect(self.show_history)
        undo_action = QAction(QIcon('icons/undo.png'), 'Undo', self)
        undo_action.triggered.connect(self.undo_last_action)

        self.size_input = QLineEdit(self)
        self.size_input.setPlaceholderText("Size (1-256)")
        self.size_input.setMaxLength(3)
        self.size_input.setFixedWidth(100)
        self.size_input.returnPressed.connect(self.change_size)
        toolbar.addWidget(self.size_input)

        self.brush_selector = QComboBox(self)
        self.brush_selector.addItems(["Normal Brush", "Round Brush", "Square Brush", "Eraser"])
        self.brush_selector.currentIndexChanged.connect(self.change_brush_type)
        toolbar.addWidget(self.brush_selector)

        self.shape_selector = QComboBox(self)
        self.shape_selector.addItems(["Free Drawing", "Rectangle", "Circle", "Triangle"])
        self.shape_selector.currentIndexChanged.connect(self.change_shape_type)
        toolbar.addWidget(self.shape_selector)

        toolbar.addAction(open_action)
        toolbar.addAction(save_action)
        toolbar.addAction(clear_action)
        toolbar.addAction(color_action)
        toolbar.addAction(history_action)
        toolbar.addAction(undo_action)

    def clear_canvas(self):
        self.image.fill(Qt.white)
        self.update()
        self.db.add_action("Canvas cleared")

    def save_image(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "PNG Files (*.png);;All Files (*)",
                                                   options=options)
        if file_name:
            self.image.save(file_name)
            self.db.add_action(f"Image saved as {file_name}")

    def open_image(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.xpm *.jpg);;All Files (*)",
                                                   options=options)
        if file_name:
            self.image.load(file_name)
            self.update()
            self.db.add_action(f"Image opened: {file_name}")

    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.pen_color = color
            self.db.add_action(f"Color changed to {color.name()}")

    def change_size(self):
        try:
            size = int(self.size_input.text())
            if 1 <= size <= 256:
                self.pen_size = size
                self.db.add_action(f"Size changed to {self.pen_size}")
            else:
                QMessageBox.warning(self, "Invalid Size", "Enter a positive integer between 1 and 256.")
        except ValueError:
            QMessageBox.warning(self, "Invalid Size", "Enter a valid integer.")

    def change_brush_type(self):
        self.brush_type = self.brush_selector.currentText()
        self.db.add_action(f"Brush type changed to {self.brush_type}")

    def change_shape_type(self):
        self.shape_type = self.shape_selector.currentText()
        self.db.add_action(f"Shape type changed to {self.shape_type}")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.last_point = event.pos()
            self.start_point = event.pos()

    def mouseMoveEvent(self, event):
        if self.drawing:
            if self.shape_type == "Free Drawing":
                current_point = event.pos()
                self.draw_shape(self.last_point, current_point)
                self.last_point = current_point
                self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = False
            if self.shape_type != "Free Drawing":
                self.draw_shape(self.start_point, event.pos())
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(0, 0, self.image)

    def draw_shape(self, start_point, end_point):
        painter = QPainter(self.image)
        pen = QPen(self.pen_color, self.pen_size, Qt.SolidLine)
        painter.setPen(pen)

        if self.shape_type == "Free Drawing":
            if self.brush_type == "Eraser":
                pen = QPen(Qt.white, self.pen_size, Qt.SolidLine)
                painter.setPen(pen)
            painter.drawLine(start_point, end_point)
        elif self.shape_type == "Rectangle":
            rect = QRect(start_point, end_point)
            painter.drawRect(rect)
        elif self.shape_type == "Circle":
            radius = (end_point - start_point).manhattanLength()
            painter.drawEllipse(start_point, radius, radius)
        elif self.shape_type == "Triangle":
            points = QPolygon([start_point, end_point, QPoint(end_point.x(), start_point.y())])
            painter.drawPolygon(points)

    def show_history(self):
        actions = self.db.get_actions()
        history_text = "\n".join([f"{action[0]}: {action[1]} at {action[2]}" for action in actions])
        QMessageBox.information(self, "Action History", history_text if history_text else "No action records.")

    def undo_last_action(self):
        self.db.delete_last_action()
        QMessageBox.information(self, "Undo Action", "Last action undone.")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PaintApp()
    window.show()
    sys.exit(app.exec_())

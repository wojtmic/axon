from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QLabel
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QKeyEvent, QPalette, QColor
import os
from .utils import process_string
from .config import CONFIG_ROOT
from typing import List
from .generator import AxonEntry
import subprocess

class AxonListItemWidget(QWidget):
    def __init__(self, main_text='Axon list item', sub_text='This is in fact a list item',
                 icon=None, parent=None):
        super().__init__(parent)
    
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,5,5,5)
        layout.setSpacing(10)

        t_layout = QVBoxLayout()
        t_layout.setContentsMargins(0,0,0,0)
        t_layout.setSpacing(0)

        self.main_text = QLabel(main_text)
        self.main_text.setObjectName('ResultMainText')
        font_m = self.main_text.font()
        font_m.setPointSize(font_m.pointSize()+1)
        font_m.setBold(True)
        self.main_text.setFont(font_m)

        self.sub_text = QLabel(sub_text)
        self.sub_text.setObjectName('ResultSubText')
        font_s = self.sub_text.font()
        font_s.setPointSize(font_s.pointSize()-1)
        self.sub_text.setFont(font_s)

        palette = self.sub_text.palette()
        palette.setColor(QPalette.ColorRole.Text, QColor(Qt.GlobalColor.lightGray))
        self.sub_text.setPalette(palette)
        self.sub_text.setWordWrap(True)

        # Assemble layout
        t_layout.addWidget(self.main_text)
        t_layout.addWidget(self.sub_text)

        layout.addLayout(t_layout)
    
    def sizeHint(self):
        width = super().sizeHint().width()

        main_height = self.main_text.sizeHint().height()
        sub_height = self.sub_text.sizeHint().height()

        total_height = main_height + sub_height + 16

        return QSize(width, max(total_height, 60))

class AxonWindow(QWidget):
    def __init__(self, config=None, entries=None, style=None):
        super().__init__()
        self.entries = entries
        self.config = config
        self.styleT = style
        self.init_ui()

        self.style_ui()
    
    def init_ui(self): # Init of main ui
        self.setWindowTitle('Axon')
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.entry = QLineEdit()
        self.entry.setPlaceholderText(self.config['placeholder'])
        self.entry.textChanged.connect(self.update_list)
        
        self.list = QListWidget()
        self.list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.layout.addWidget(self.entry)
        self.layout.addWidget(self.list)
        self.setLayout(self.layout)

        self.update_list("")
        self.setFixedWidth(400)

        self.post_start()
    
    def style_ui(self):
        if not self.styleT:
            return

        self.setObjectName('MainWindow')
        self.entry.setObjectName('InputBar')
        self.list.setObjectName('ResultList')
        
        self.setStyleSheet(self.styleT)
    
    def post_start(self): # Post start tasks, like centering
        self.adjustSize()

        screen_geometry = QApplication.primaryScreen().availableGeometry()
        center_point = screen_geometry.center()
        frame_geometry = self.frameGeometry()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

        QApplication.instance().applicationStateChanged.connect(self.app_state_change)

        self.activateWindow()
        self.entry.setFocus()
        self.list.setCurrentRow(0)
    
    def update_list(self, filter_text):
        filtered_results: List[AxonEntry] = []
        filter_text = filter_text.lower().strip()

        for entry in self.entries:
            if filter_text == '' and 'NOTEMPTY' in entry.flags:
                continue
            
            try:
                if not filter_text or filter_text in process_string(entry.name.lower(), self.entry.text()):
                    filtered_results.append(entry)
            except Exception as e:
                pass

        self.list.clear()
        for entry in filtered_results:
            self.add_list_item(None, entry.name, entry.subtext, entry.id)
        
        self.adjustSize()
        self.list.setCurrentRow(0)
    
    def add_list_item(self, icon, name, subtitle, id):
        if '[AXON_TOKEN NOTSHOW]' in process_string(name, self.entry.text()):
            return

        name = process_string(name, self.entry.text())
        subtitle = process_string(subtitle, self.entry.text())

        item = QListWidgetItem()
        widget = AxonListItemWidget(name, subtitle)

        widget.setObjectName(f'itemWidget_{id}')

        # item.setData(Qt.UserRole, id)
        item._id = id
        item.setSizeHint(widget.sizeHint())
        self.list.addItem(item)
        self.list.setItemWidget(item, widget)
    
    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()

        if key == Qt.Key.Key_Escape:
            print('Exiting Axon with no launch :(')
            QApplication.instance().quit()

        # elif key == Qt.Key.Key_PageUp:
                # self.entry.setFocus()

        elif key in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_PageDown):
            if not self.list.hasFocus():
                self.list.setFocus()
            
            self.list.keyPressEvent(event)
            
            self.entry.setFocus()

        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.open_result()
        
        else:
            if not self.entry.hasFocus():
                self.entry.setFocus()
                QApplication.sendEvent(self.entry, event)
            else:
                super().keyPressEvent(event)

    def app_state_change(self, state):
        if state == Qt.ApplicationState.ApplicationInactive:
            print('Exiting axon because of loss focus :(')
            QApplication.instance().exit()
    
    def open_result(self):
        # First, we have to get the entry to... run, y' know?
        item_id = self.list.currentItem()._id
        action = self.entries[item_id].action
        if 'run' in action:
            process = subprocess.Popen(process_string(action['run'], self.entry.text()),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                    shell=True)

            print(f'Launched with PID {process.pid}')

        elif 'copy' in action:
            os.system(f'wl-copy {process_string(action['copy'], self.entry.text())}')

            print('Copied to clipboard!')

        QApplication.instance().exit()
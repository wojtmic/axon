import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QLabel
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent, QPalette, QColor
import subprocess
import re
import commentjson
from typing import List
import simpleeval
import math
import configparser
import json
import traceback

CONFIG_ROOT = os.path.join(os.path.expanduser('~'), '.config', 'axon')
CACHE_ROOT  = os.path.join(os.path.expanduser('~'), '.cache', 'axon')

if not os.path.exists(CONFIG_ROOT):
    os.makedirs(CONFIG_ROOT)

if not os.path.exists(CACHE_ROOT):
    os.makedirs(CACHE_ROOT)

if not os.path.exists(os.path.join(CONFIG_ROOT, 'launcher.jsonc')):
    with open(os.path.join(CONFIG_ROOT, 'launcher.jsonc'), 'w') as f:
        f.write('''{
    "placeholder": "Search...",
    "entries": [
        {
            "name": "$(playerctl metadata title)", // $() will run a command, like in Bash
            "action": {"run": "playerctl play-pause"}, // The run action runs a Bash command
            "icon": "$(playerctl metadata mpris:artUrl)", // This requires a URL path (tip: use file:// for local)
            "condition": "pgrep spotify" // Condition will run only if the command it runs finishes with a 0 escape code
        },
        {"autogen": "desktop_apps"}, // Autogen will populate the list with autogenerated entries
        { // Allows you to do math!
            "name": "%% = +(%%)", // +() will evaluate a math expression, %% gets replaced with input
            "action": {"copy": "+(%%)"}, // Copy of course copies to the clipboard (with wl-copy, if you wanna do anything else do a RUN)
            "icon": "text://", // The text:// protocol just uses a string to render as an image
            "flags": ["NOTEMPTY"] // Flags add special behavior to an entry. Usually you wont need them, but they may make your config 500% better!
        },
        { // For running commands
            "name": "Run %%",
            "action": {"run": "%%"},
            "icon": "text://",
            "flags": ["NOTEMPTY"]
        }
    ]}''')

def process_string(string, entry):
        if string == None:
            return ''

        processed = string
        processed = processed.replace("%%", entry)

        def run_cmd_sub(match):
            cmd = match.group(1).strip()
            if not cmd:
                return ""
            
            try:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=0.5
                )
                if result.returncode == 0:
                    return result.stdout.strip()
                else:
                    return f'[Cmd Failed] {result.returncode} [Axon Message]'
            except subprocess.TimeoutExpired:
                return f'[Cmd Timeout] Timeout is 0.5 [Axon Message]'
            except Exception as e:
                return f'[Code Error] {e} [Axon Message]'
        
        s_eval = simpleeval.SimpleEval(
                 functions={'sqrt': math.sqrt, 'pow': pow,
                        'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
                        'abs': abs, 'round': round})

        def math_wrapper(match: re.Match):
            expression = match.group(1).strip()
            if not expression:
                return ""
            
            try:
                result = s_eval.eval(expression)
                return f'{str(result)}'
            except:
                return '[AXON_TOKEN NOTSHOW]'

        processed = re.sub(r'\$\((.*?)\)', run_cmd_sub, processed)
        processed = re.sub(r'\+\((.*?)\)', math_wrapper, processed)
        return processed

class AxonEntry:
    def __init__(self, name, action=None, icon=None, condition=None, subtext=None, flags=None):
        self.name: str = name
        self.action = action
        self.icon = icon
        self.condition = condition
        self.subtext = subtext
        self.flags = flags

        self.id = 0
    
    @property
    def can_run(self):
        if not self.condition:
            return True
        
        try:
            result = subprocess.run(self.condition, shell=True, check=False,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    timeout=1)
            return result.returncode == 0
        except Exception as e:
            print(f"Warning! Condition {self.condition} didn't run because {e}.")
            return False
    
    def run(self):
        if not self.action:
            return
        
        if self.action[0] == 'run':
            print('run')
        elif self.action[0] == 'copy':
            print('copy')
        
def gen_entries(config):
    togen = config['entries']
    final = []

    for c in togen:
        try:
            if 'autogen' in c:
                if c['autogen'] == 'desktop_apps':
                    # Autogens are very lengthy, so they should be cached - especially this one
                    cache_file = os.path.join(CACHE_ROOT, 'desktop_apps.json')
                    if os.path.exists(cache_file) and os.path.getmtime(cache_file) >= os.path.getmtime('/usr/share/applications'):
                        print('Cached results detected, loading from cache for autogen')
                        with open(os.path.join(CACHE_ROOT, 'desktop_apps.json'), 'r') as f:
                            raw = f.read()
                        
                        data = json.loads(raw)
                        for e in data['entries']:
                            entry = AxonEntry(e['Name'], {'run': e['Exec']}, None, None, e['GenericName'], [])
                            # print(e['Name'], {'run': e['Exec']}, None, None, e['GenericName'], [])
                            entry.id = len(final)
                            final.append(entry)
                        
                        continue

                    print('Cached results non-existent or outdated, regenerating')
                    generated = []

                    appdirs = '/usr/share/applications', os.path.join(os.path.expanduser('~'), '.local/share/applications')

                    

                    for apps_dir in appdirs:
                        files = os.listdir(apps_dir)
                        for a in files:
                            if not a.endswith('.desktop'):
                                continue

                            parser = configparser.ConfigParser(interpolation=None, strict=False)
                            parser.read(f'{apps_dir}/{a}', encoding='utf-8')
                            p = parser['Desktop Entry']

                            genname = ''
                            if not p.get('Comment') == None: genname = p.get('Comment')
                            if not p.get('GenericName') == None: genname = p.get('GenericName')

                            entry = AxonEntry(p.get('Name'), {'run': p.get('Exec')}, None, None, genname, [])
                            entry.id = len(final)
                            final.append(entry)

                            generated.append(entry)
                    
                    print('List generated, now caching')

                    generated_jsoned = []

                    for e in generated:
                        print({
                            "Name": e.name,
                            "Exec": next(iter(e.action.values())),
                            "GenericName": e.subtext
                        })
                        generated_jsoned.append({
                            "Name": e.name,
                            "Exec": next(iter(e.action.values())), # I sincerly apologize for this line of spagetthi more than the entire code
                            "GenericName": e.subtext
                        })
                        

                    cache_object = {
                        "entries": generated_jsoned
                    }

                    with open(cache_file, 'w') as f:
                        f.write(json.dumps(cache_object))
                        print(f'Wrote autogen results to cache {cache_file}')

            else:
                if not 'condition' in c: c['condition'] = None
                if not 'flags' in c: c['flags'] = []
                if not 'icon' in c: c['icon'] = None
                if not 'action' in c: c['action'] = None
                if not 'subtext' in c: c['subtext'] = ''

                if 'condition' in c or True:
                    entry = AxonEntry(c['name'], c['action'], c['icon'], c['condition'], c['subtext'], c['flags'])
                    if entry.can_run:
                        entry.id = len(final)
                        final.append(entry)
                # else:
                #     entry = AxonEntry(c['name'], c['action'], c['icon'])
                #     entry.id = len(final)
                #     final.append(entry)
        except Exception as e:
            print(f'Error ocurred while parsing config. Check config for malformations. Error below:\n\n{e}')
            traceback.print_exc()
            sys.exit(1)
    
    return final

if not os.path.exists(os.path.join(CONFIG_ROOT, 'launcher.jsonc')):
    print("Cannot find launcher.jsonc in Axon config directory. Check https://github.com/wojtmic/axon/wiki/setup.md for more info.")
    sys.exit(1)

with open(os.path.join(CONFIG_ROOT, 'launcher.jsonc'), 'r') as f:
    config = commentjson.loads(f.read())

entries = gen_entries(config)

# UI
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

class AxonWindow(QWidget):
    def __init__(self, config=None):
        super().__init__()
        self.entries = entries
        self.config = config
        self.init_ui()

        if os.path.exists(os.path.join(CONFIG_ROOT, 'style.qss')):
            print('Style.qss file detected, applying QSS')
            self.style_ui()
    
    def init_ui(self): # Init of main ui
        self.setWindowTitle('Axon')
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.entry = QLineEdit()
        self.entry.setPlaceholderText(config['placeholder'])
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
        self.setObjectName('MainWindow')
        self.entry.setObjectName('InputBar')
        self.list.setObjectName('ResultList')
        
        with open(os.path.join(CONFIG_ROOT, 'style.qss'), 'r') as f:
            self.setStyleSheet(f.read())
    
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

        for entry in entries:
            if filter_text == '' and 'NOTEMPTY' in entry.flags:
                continue

            if not filter_text or filter_text in process_string(entry.name.lower(), self.entry.text()):
                filtered_results.append(entry)

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
        action = entries[item_id].action
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

        app.exit()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AxonWindow()
    window.show()
    sys.exit(app.exec())

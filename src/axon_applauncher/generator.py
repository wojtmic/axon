import subprocess
from .config import CACHE_ROOT
import os
import json
import configparser
import sys
import traceback

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

def gen_entries(config): # Will generate entries based on config
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
                    found_names = set()

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

                            if not p.get('Name') in found_names:
                                entry = AxonEntry(p.get('Name'), {'run': p.get('Exec')}, None, None, genname, [])
                                entry.id = len(final)
                                final.append(entry)
                                found_names.add(p.get('Name'))

                            generated.append(entry)
                    
                    print('List generated, now caching')

                    generated_jsoned = []

                    for e in generated:
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

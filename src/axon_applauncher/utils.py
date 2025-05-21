import math
import subprocess
import simpleeval
import re

def search(entries, filter_text):
    if not filter_text:
        return list(entries)

    processed_entries = []
    filter_text_lower = filter_text

    for i, entry in enumerate(entries):
        entry_text = entry.name

        if not isinstance(entry_text, str):
            continue

        entry_text_lower = entry_text.lower()
        
        score = 0
        match_start_index = float('inf')

        if filter_text_lower == entry_text_lower:
            score = 3
            match_start_index = 0
        elif entry_text_lower.startswith(filter_text_lower):
            score = 2
            match_start_index = 0
        elif filter_text_lower in entry_text_lower:
            score = 1
            match_start_index = entry_text_lower.find(filter_text_lower)
        
        if score > 0:
            processed_entries.append({
                'score': score,
                'match_start_index': match_start_index,
                'original_index': i,
                'entry': entry
            })

        elif "ALWAYSSHOW" in entry.flags:
            processed_entries.append({
                'score': -1,
                'match_start_index': match_start_index,
                'original_index': i,
                'entry': entry
            })

    processed_entries.sort(key=lambda x: (-x['score'], x['match_start_index'], x['original_index']))

    return [item['entry'] for item in processed_entries]

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
import math
import subprocess
import simpleeval
import re

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
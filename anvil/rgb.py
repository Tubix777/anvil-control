import re
import shlex


def parse_devices(output):
    result = []
    for line in output.splitlines():
        match = re.match(r'^(\d+): (.+)$', line)
        if match:
            result.append({'id':int(match[1]), 'name':match[2], 'modes':[]})
        elif result and line.strip().startswith('Modes:'):
            try:
                result[-1]['modes'] = [m.strip('*[]') for m in shlex.split(line.split('Modes:', 1)[1])]
            except ValueError:
                result[-1]['modes'] = []
    return result

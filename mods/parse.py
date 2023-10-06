import re

from flask import request as req

def mod_string(s):
  return [
    name[:1:-1] if name[:2] == 'r:' else name
    for name in re.split(r'\s+', s)
    if s
  ]

def in_request():
  file_mode = req.files and 'content' in req.files
  if file_mode:
    data = dict(
      (k, v[0]) if len(v) == 1 else (k, v)
      for k, v in req.form.items(multi=True)
    )
  else:
    data = req.get_json(force=True)

  if 'mods' in data and isinstance(data['mods'], str):
    return (mod_string(data['mods']), None)
  elif 'mods' in data and isinstance(data['mods'], list):
    return (data['mods'], None)
  elif 'mods' in data and isinstance(data['mods'], int):
    return (None, data['mods'])

  return None, None

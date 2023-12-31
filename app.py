import os
import json
import hashlib
from contextlib import contextmanager
import subprocess
import traceback

from flask import Flask, request as req
import requests

import mods

OSU_MODE_NAMES = ['osu', 'taiko', 'fruits', 'mania']

app = Flask(__name__)

def generate_generic_error_handler():
  @app.errorhandler(Exception)
  def error_handler_generic(error):
    for tb in traceback.extract_tb(error.__traceback__, limit=5):
      print(tb)
    return {'error': {'type': type(error).__name__, 'message': str(error)}}, 500

  def error_handler_for_code(code):
    @app.errorhandler(code)
    def error_handler_code(error):
      return {'error': {'type': type(error).__name__, 'message': str(error)}}, code
    return error_handler_code

  for code in (400, 401, 403, 404, 405, 406, 415):
    error_handler_for_code(code)

  del globals()['generate_generic_error_handler']

generate_generic_error_handler()

class OsuProcessException(Exception): pass

class DownloadedFile:
  __slots__ = (
    'path', 'hash', 'invalid',
  )

  def __init__(self, content):
    self.hash = hashlib.md5(content.encode()).hexdigest()
    self.path = os.path.join('tmp', 'downloads', f"{self.hash}")
    normalized_header = ''.join(
      chr(c) for c in content.splitlines()[0].encode()
      if c in (32, *range(48, 48 + 10), *range(97, 97 + 26))
    )
    self.invalid = False

    if normalized_header[:17] == 'osu file format v':
      self.path = self.path + '.osu'
    else:
      self.invalid = True
    print(normalized_header)

def fetch_difficulty_generic(mode_id: int):
  @contextmanager
  def downloaded_file(content):
    if not content:
      yield None
      return

    file = None
    try:
      file = DownloadedFile(content)
      if file.invalid:
        raise OsuProcessException("expected osu map file.")

      if not os.path.exists(file.path):
        with open(file.path, 'wb') as f:
          f.write(content.encode())
      yield file
    finally:
      if file is not None and file.invalid:
        os.unlink(file.path)

  validate_hash = False
  data_choice = [None, None]
  if req.files and 'content' in req.files:
    is_download = True
    data_choice[0] = req.files['content'].read()
  else:
    data = req.get_json(force=True)

    if 'url' in data:
      is_download = True
      data_choice[0] = requests.get(data['url']).text
    elif 'map_id' in data and (isinstance(data['map_id'], int) or data['map_id'].isdigit()):
      data_choice[1] = data['map_id']

    if 'map_hash' in data:
      validate_hash = data['map_hash']

  query_mods = []
  mod_names, mod_flags = mods.in_request()
  if mod_names is not None:
    query_mods[:] = mods.convert_preferred_to_community(mod_names)
  elif mod_flags is not None:
    query_mods[:] = mods.convert_classic_to_community(mod_flags)

  output_hash = None

  with downloaded_file(data_choice[0]) as dl:
    cmd = ['dotnet', 'PerformanceCalculator.dll', 'metadata', '-j']
    # cmd.append('--no-classic')
    cmd.append(f"-r:{mode_id}")
    for mod in query_mods:
      cmd.extend(['-m', mod])

    if dl:
      output_hash = dl.hash
      cmd.append(os.path.join(os.getcwd(), dl.path))
    else:
      cmd.append(data_choice[1])

    cmd[:] = [str(c) for c in cmd]
    # print(cmd)

    proc = subprocess.run(
      cmd,
      cwd=os.path.join(os.getcwd(), 'osu'),
      capture_output=True,
      text=True,
    )

    if not dl:
      map_file = os.path.join('tmp', 'cache', f'{data_choice[1]}.osu')
      map_content = open(map_file, 'rb').read()
      if not map_content:
        os.unlink(map_file)
      output_hash = hashlib.md5(map_content).hexdigest()

    if proc.returncode:
      raise OsuProcessException(next((line for line in proc.stderr.splitlines()), None))
    raw_output = proc if isinstance(proc, str) else proc.stdout
    output = json.loads(raw_output.splitlines()[-1])

  raw_stat = next(iter(output['results']), None)
  if raw_stat is not None:
    raw_stat['map_hash'] = output_hash

  if raw_stat is not None and validate_hash and \
     raw_stat.get('map_hash', validate_hash) != validate_hash:
    raw_stat = None

  map_stat_rating = {}
  if raw_stat is not None and mode_id == raw_stat['ruleset_id']:
    map_stat_rating["map_id"] = raw_stat['beatmap_id']
    response_mods = [raw_mod['acronym'] for raw_mod in raw_stat['mods']]
    response_replace = dict(zip(
      response_mods,
      mods.convert_community_to_preferred(response_mods)
    ))
    map_stat_rating['mods'] = {
      'classicFlags': mods.convert_community_to_classic(response_mods),
      'raw': dict(
        (
          response_replace[raw_mod['acronym']],
          raw_mod.get('settings', {})
        )
        for raw_mod in raw_stat['mods']
      ),
    }
    map_stat_rating['difficulty'] = raw_stat['difficulty']
    map_stat_rating['bpm'] = raw_stat['tempo']
    map_stat_rating['duration'] = raw_stat['duration']

  if map_stat_rating:
    return {"data": map_stat_rating}
  else:
    return {"error": {"type": "OsuProcessException", "message": "invalid game mode"}}, 404

@app.post('/stat/<int:mode_id>')
def fetch_difficulty_by_id(mode_id: int):
  return fetch_difficulty_generic(mode_id)

@app.post('/stat/<string:mode_name>')
def fetch_difficulty_by_name(mode_name: str):
  if mode_name in OSU_MODE_NAMES:
    return fetch_difficulty_generic(OSU_MODE_NAMES.index(mode_name))

if __name__ == '__main__':
  app.run(debug=False)

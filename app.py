import os
import json
import hashlib
from contextlib import contextmanager
import subprocess
import traceback

from flask import Flask, request as req
import requests

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

  data_choice = [None, None]
  if req.files and 'content' in req.files:
    is_download = True
    data_choice[0] = req.files['content'].read()
  else:
    data = req.get_json(force=True)
    if 'url' in data:
      is_download = True
      data_choice[0] = requests.get(data['url']).text
    else:
      data_choice[1] = data['map_id']

  with downloaded_file(data_choice[0]) as dl:
    cmd = ['dotnet', 'PerformanceCalculator.dll', 'difficulty', '-j']
    cmd.append('--no-classic')
    cmd.append(f"-r:{mode_id}")
    if dl:
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

    if proc.returncode:
      raise OsuProcessException(next((line for line in proc.stderr.splitlines()), None))
    raw_output = proc if isinstance(proc, str) else proc.stdout
    output = json.loads(raw_output.splitlines()[-1])

  raw_stat = next(iter(output['results']), None)
  map_stat_rating = {}
  if raw_stat is not None and mode_id == raw_stat['ruleset_id']:
    map_stat_rating["map_id"] = raw_stat['beatmap_id']
    map_stat_rating['mods_raw'] = raw_stat['mods']
    map_stat_rating['difficulty_star'] = raw_stat['attributes']['star_rating']

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

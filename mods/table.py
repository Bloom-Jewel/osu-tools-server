__all__ = []

def _wrapper_(g):
  import os
  import re
  import functools
  import itertools

  from .parse import mod_string as parse_mod_string

  class ParserNotFound(Exception): pass
  class NoModFound(Exception): pass

  # sanity notes
  # - preferred, means system preferred names
  # - community, means community preferred names
  #   only applicable that part of the gameplay, ignoring those aren't like Autoplay.
  # - classic,   integers.
  PREFERRED = parse_mod_string('NF EM TD HD HR SD DT RL HT NC FL AP SO ATP PF 4K 5K 6K 7K 8K SUD RAN CIN TRG 9K DP 1K 3K 2K V2 MIR')
  COMMUNITY = parse_mod_string('NF r:ZE TD HD HR SD DT r:XR HT NC FL AT SO AP PF 4K 5K 6K 7K 8K FI RD CIN TG 9K DS 1K 3K 2K V2 MR')
  CLASSIC   = [1 << i for i in range(31)]
  if 'STAT_SERVER_CUSTOM_MODS' in os.environ:
    CUSTOM    = parse_mod_string(os.environ.get('STAT_SERVER_CUSTOM_MODS'))

  MODERN_ADDITIONS = [
    ('HST', 'WU'),
    ('SLO', 'WD'),
  ]
  for prefer_name, community_name in MODERN_ADDITIONS:
    PREFERRED.extend(parse_mod_string(prefer_name))
    COMMUNITY.extend(parse_mod_string(community_name))

  MOD_NULL  = {
    'str': 'NM',
    'int': 0,
  }
  PARSER_TYPE = {
    'preferred': (list, True),
    'community': (list, True),
    'classic':   (int, False),
  }
  if 'STAT_SERVER_CUSTOM_MODS' in os.environ:
    PARSER_TYPE['custom'] = (list, True)

  loc = locals()
  PARSER = dict((k, loc[k.upper()]) for k in PARSER_TYPE)
  del loc

  def convert_from(key, value):
    if key not in PARSER_TYPE:
      raise ParserNotFound(key)
    target_type, keep = PARSER_TYPE[key]
    parsed, raw = [], []

    try:
      if target_type == int:
        if value == MOD_NULL['int']:
          raise NoModFound()

        parsed[:] = [i for i, bit in zip(range(len(PARSER[key])), PARSER[key]) if bit & value]
      elif target_type == list:
        if MOD_NULL['str'] in value:
          raise NoModFound()

        parsed[:] = [PARSER[key].index(entry) for entry in value if entry in PARSER[key]]
        raw[:]    = [entry for entry in value if entry not in PARSER[key]]
    except NoModFound:
      # discard any processed data
      parsed[:] = []
      keep = False

    if not keep:
      raw[:] = []

    return parsed, raw

  def convert_to(key, parsed):
    if key not in PARSER_TYPE:
      raise ParserNotFound(key)
    target_type, keep = PARSER_TYPE[key]
    value = target_type()

    if target_type == int:
      for i in parsed:
        value = value | (PARSER[key][i])
    elif target_type == list:
      value[:] = [PARSER[key][i] for i in parsed]

    return value

  def generic_parser(key_from, key_to, value):
    parsed, raw = convert_from(key_from, value)
    value_to = convert_to(key_to, parsed)
    if isinstance(value_to, list):
      value_to.extend(raw)

    return value_to

  # allow moving actual PREFERRED table into other table if needed
  if 'STAT_SERVER_PREFERRED' in os.environ and \
     os.environ['STAT_SERVER_PREFERRED'] in PARSER_TYPE and \
     PARSER_TYPE[os.environ['STAT_SERVER_PREFERRED']][0] == list:
    PARSER['preferred'] = PARSER.get(os.environ['STAT_SERVER_PREFERRED'])

  for key_from, key_to in itertools.permutations(PARSER_TYPE, 2):
    k = f'convert_{key_from}_to_{key_to}'
    if k in g:
      continue
    g[k] = functools.partial(generic_parser, key_from, key_to)
    __all__.append(k)

  __whitelist__ = (
    'generic_parser',
  )
  for k, v in locals().items():
    if k not in __whitelist__:
      continue

    g[k] = v
    __all__.append(k)


  del g['_wrapper_']

_wrapper_(globals())

__all__ = tuple(__all__)

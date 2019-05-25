from environs import Env

env = Env()
env.read_env()
DEFAULT_PASS = env.str('DEFAULT_PASS', default='admin123')
DEFAULT_USER = env.str('DEFAULT_USER', default='admin')
CALIBRE_PORT = env.int('CALIBRE_PORT', default=8083)

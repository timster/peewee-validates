import sys
import os

src_dir = os.path.realpath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, src_dir)

from peewee_validates import __version__

project = 'peewee-validates'
copyright = 'Tim Shaffer'
version = __version__
release = __version__

extensions = []

# templates_path = ['_templates']

source_suffix = '.rst'

master_doc = 'index'

exclude_patterns = ['_build']

pygments_style = 'pastie'

html_theme = 'default'

# html_static_path = ['_static']

htmlhelp_basename = 'peewee-validates'

man_pages = [
    ('index', 'peewee-validates', 'peewee-validates documentation', ['Tim Shaffer'], 1)
]
from setuptools import setup
from codecs import open
from os import path

root_dir = path.abspath(path.dirname(__file__))

with open(path.join(root_dir, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='peewee-validates',
    version='0.0.1',

    description='Simple and flexible model validator for Peewee ORM.',
    long_description=long_description,

    url='https://github.com/timster/peewee-validates',

    author='Tim Shaffer',
    author_email='timshaffer@me.com',

    license='MIT',

    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',
        'Topic :: Database :: Front-Ends',

        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],

    keywords='peewee orm database migration development',

    py_modules=['peewee_validates'],

    install_requires=['peewee>=2.8.0'],
)

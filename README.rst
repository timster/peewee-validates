peewee-validates
################

A simple and flexible model and data validator for `Peewee ORM <http://docs.peewee-orm.com/>`_.

.. image:: http://img.shields.io/travis/timster/peewee-validates.svg?style=flat
    :target: http://travis-ci.org/timster/peewee-validates
    :alt: Build Status

.. image:: http://img.shields.io/coveralls/timster/peewee-validates.svg?style=flat
    :target: https://coveralls.io/r/timster/peewee-validates
    :alt: Code Coverage

.. image:: http://img.shields.io/pypi/v/peewee-validates.svg?style=flat
    :target: https://pypi.python.org/pypi/peewee-validates
    :alt: Version

.. image:: http://img.shields.io/pypi/dm/peewee-validates.svg?style=flat
    :target: https://pypi.python.org/pypi/peewee-validates
    :alt: Downloads

.. image:: https://readthedocs.org/projects/peewee-validates/badge/?version=latest
    :target: https://peewee-validates.readthedocs.io
    :alt: Documentation

Requirements
============

* python >= 3.3
* peewee >= 2.8.2
* python-dateutil >= 2.5.0

Installation
============

This package can be installed using pip:

::

    pip install peewee-validates

Usage
=====

Here's a quick teaser of what you can do with peewee-validates:

.. code:: python

    import peewee
    from peewee_validates import ModelValidator

    class Category(peewee.Model):
        code = peewee.IntegerField(unique=True)
        name = peewee.CharField(null=False, max_length=250)

    obj = Category(code=42)

    validator = ModelValidator(obj)
    validator.validate()

    print(validator.errors)

    # {'name': 'This field is required.', 'code': 'Must be a unique value.'}

In fact, there is also a generic validator that does not even require a model:

.. code:: python

    from peewee_validates import Validator, StringField

    class SimpleValidator(Validator):
        name = StringField(required=True, max_length=250)
        code = StringField(required=True, max_length=4)

    validator = SimpleValidator(obj)
    validator.validate({'code': 'toolong'})

    print(validator.errors)

    # {'name': 'This field is required.', 'code': 'Must be at most 5 characters.'}

Documentation
=============

Check out the `Full Documentation <http://peewee-validates.readthedocs.io>`_ for more details.

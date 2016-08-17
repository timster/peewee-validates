Peewee Validates
################

A simple and flexible model and data validator for `Peewee ORM <http://docs.peewee-orm.com/>`_.

.. image:: http://img.shields.io/travis/timster/peewee-validates.svg?style=flat-square
    :target: http://travis-ci.org/timster/peewee-validates
    :alt: Build Status

.. image:: http://img.shields.io/coveralls/timster/peewee-validates.svg?style=flat-square
    :target: https://coveralls.io/r/timster/peewee-validates
    :alt: Code Coverage

.. image:: http://img.shields.io/pypi/v/peewee-validates.svg?style=flat-square
    :target: https://pypi.python.org/pypi/peewee-validates
    :alt: Version

.. image:: http://img.shields.io/pypi/dm/peewee-validates.svg?style=flat-square
    :target: https://pypi.python.org/pypi/peewee-validates
    :alt: Downloads

Requirements
============

* python >= 3.3
* peewee >= 2.8.0
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

    # {'name': 'required field', 'code': 'must be unique'}

In fact, there is also a generic validator that does not even require a model:

.. code:: python

    from peewee_validates import Validator, Field

    class SimpleValidator(Validator):
        name = Field(str, required=True, max_length=250)
        code = Field(str, required=True, max_length=4)

    validator = SimpleValidator(obj)
    validator.validate({'code': 'toolong'})

    print(validator.errors)

    # {'name': 'required field', 'code': 'must be at most 5 characters'}

Check out the `Usage documentation <USAGE.rst>`_ for more details.

Todo
====

* More documentation
* More examples

Feedback
========

This package is very immature. If you have any comments, suggestions, feedback, or issues, please
feel free to send me a message or submit an issue on Github.

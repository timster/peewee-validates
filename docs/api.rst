API Documentation
#################

Validator Classes
=================

.. autoclass:: peewee_validates.Validator
    :members:

.. autoclass:: peewee_validates.ModelValidator
    :members:

Fields
======

.. autoclass:: peewee_validates.Field
.. autoclass:: peewee_validates.StringField
.. autoclass:: peewee_validates.FloatField
.. autoclass:: peewee_validates.IntegerField
.. autoclass:: peewee_validates.DecimalField
.. autoclass:: peewee_validates.DateField
.. autoclass:: peewee_validates.TimeField
.. autoclass:: peewee_validates.DateTimeField
.. autoclass:: peewee_validates.BooleanField
.. autoclass:: peewee_validates.ModelChoiceField
.. autoclass:: peewee_validates.ManyModelChoiceField

Field Validators
================

This module includes some basic validators, but it's pretty easy to write your own if needed.

All validators return a function that can be used to validate a field. For example:

.. code-block:: python

    validator = peewee_validates.validate_required()

    # Raises ValidationError since no data was provided for this field.
    field = StringField()
    validator(field, {})

    # Does not raise any error since default data was provided.
    field = StringField(default='something')
    validator(field, {})

.. autofunction:: peewee_validates.validate_email
.. autofunction:: peewee_validates.validate_equal
.. autofunction:: peewee_validates.validate_function
.. autofunction:: peewee_validates.validate_length
.. autofunction:: peewee_validates.validate_matches
.. autofunction:: peewee_validates.validate_model_unique
.. autofunction:: peewee_validates.validate_none_of
.. autofunction:: peewee_validates.validate_not_empty
.. autofunction:: peewee_validates.validate_one_of
.. autofunction:: peewee_validates.validate_range
.. autofunction:: peewee_validates.validate_regexp
.. autofunction:: peewee_validates.validate_required

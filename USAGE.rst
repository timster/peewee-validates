Usage
#####

.. contents::

Basic Validator
===============

The very basic usage is a validator that looks like this:

.. code:: python

    from peewee_validates import Validator, Field, validates

    class SimpleValidator(Validator):
        first_name = Field(str, validators=[validates.required()])

    validator = SimpleValidator()

This tells us that we want to validate data for one field (first_name).

Each field has an associated data type (or coersion). In this case, the field will be
coerced to ``str``. Each field also has a list of data validators. That's about it.

When we call the ``validate()`` method on our validator, we pass the data that we want to
validate. The result we get back is an object with ``data`` and ``errors`` attributes.

.. code:: python

    data = {'first_name': ''}
    rv = validator.validate(data)
    print(rv)

    Result(data={}, errors={'first_name': 'required field'})

Both ``data`` and ``errors`` are plain ``dict`` instances. In this case we can see that
there was one error for ``first_name``. That's because we gave it the ``required()`` validator
but did not pass any data for that field.

When we pass good data, the validation passes and the output data is populated:

.. code:: python

    data = {'first_name': 'Tim'}
    rv = validator.validate(data)
    print(rv)

    Result(data={'first_name': 'Tim'}, errors={})

The data dictionary will contain the values after any validators, type coersions, and
any other custom modifiers.

Data Coersion
=============

One of the first processes that happens when data validation takes place is data coersion.
This is the first argument that is passed to ``Field()``.

The coersion method can be any method that accepts a value and returns a value. If the value
cannot be coerced, it should raise some type of exception. Don't get too fancy with the logic
in coersion, since the exception will be swallowed.

Here's an example of a custom coersion method. This just duplicates the functionality of ``int``
to show you an example.

.. code:: python

    def coerce_int(value):
        return int(value)

    class SimpleValidator(Validator):
        code = Field(coerce_int)

    rv = SimpleValidator().validate({'code': 'text'})
    print(rv)

    Result(data={}, errors={'code': 'invalid: coerce_coerce_int'})

That error message isn't very pretty, but I will show you later how to change that.

There are also several built-in coersions that you can call by name: date, time, and datetime.
These use python-dateutils to try to coerce text to a date instance.

.. code:: python

    class SimpleValidator(Validator):
        birthday = Field('date')

    rv = SimpleValidator().validate({'birthday': '22 jan 1980'})
    print(rv)

    Result(data={'birthday': datetime.date(1980, 1, 22)}, errors={})

Validators
==========

A validator is just a method with the signature ``validator(field, data)`` where field is a
``Field`` instance and ``data`` is the data dict that is passed to ``validate()``.

If we want to implement a validator that makes sure the name is always "tim" we could do it
like this:

.. code:: python

    def always_tim(field, data):
        if field.value and field.value != 'tim':
            raise ValidationError('not_tim')


    class SimpleValidator(Validator):
        name = Field(str, validators=[always_tim])

    data = {'name': 'bob'}
    rv = SimpleValidator().validate(data)
    print(rv)

    Result(data={}, errors={'name': 'invalid: not_tim'})

Now let's say you want to implement a validator that checks the length of the field.
The length should be configurable. So we can implement a validator that accepts a parameter
and returns the validator function. We basically wrap our actual validator function with
another function. That looks like this:

.. code:: python

    def length(value):
        def validator(field, data):
            if field.value and len(field.value) > value:
                raise ValidationError('too_long')
        return validator

    class SimpleValidator(Validator):
        name = Field(str, validators=[length(2)])

    data = {'name': 'bob'}
    rv = SimpleValidator().validate(data)
    print(rv)

    Result(data={}, errors={'name': 'invalid: too_long'})

Available Validators
--------------------

There are a bunch of built-in validators that can be accessed by importing
``peewee_validates.validates``.

* ``required()`` - validate that data is entered
* ``max_length(value)`` - validate that length is less than ``value``
* ``min_length(value)`` - validate that length is at least ``value``
* ``length(value)`` - validate that length is exactly ``value``
* ``choices(values)`` - validate that value is in ``values``. ``values`` can also be a callable that returns values when called
* ``exclude(values)`` - validate that value is not in ``values``. ``values`` can also be a callable that returns values when called
* ``range(low, high)`` - validate that value is between ``low`` and ``high``
* ``equal(value)`` - validate that value is equal to ``value``
* ``regexp(pattern, flags=0)`` - validate that value matches ``patten``
* ``function(method, \*\*kwargs)`` - runs ``method`` with field value as first argument and ``kwargs``. Validates that the result is Truthy

Field API
=========

The full field API looks like this:

.. code:: python

    Field(coerce=None, default=None, required=False, max_length=None, min_length=None, choices=None, range=None, validators=None)

We have already discussed ``coerce`` and ``validators``.

``default`` is a value that will be used if no data is provided to the field. This can also be
a callable that returns a value.

The other remaining fields:  ``required``, ``max_length``, ``min_length``, ``choices``, ``range``
are just shortcuts for the validators with the same name. So these two field declarations
are functionally identical:

.. code:: python

    name = Field(str, required=True, max_length=200)

    name = Field(str, validators=[validates.required(), validates.max_length(200)])

Custom Error Messages
=====================

In some of the previous examples, we saw that the default error messages are not always that
friendly. Error messages can be changed by settings the ``messages`` attribute on the ``Meta``
class. Error messages are looked up by a key, and optionally prefixed with the field name.

The key is the first argument passed to ``ValidationError`` when an error is raised.

.. code:: python

    class SimpleValidator(Validator):
        name = Field(str, required=True)

        class Meta:
            messages = {
                'required': 'please enter a value'
            }

Now any field that is required will have the error message "please enter a value".
We can also change this for specific fields:

.. code:: python

    class SimpleValidator(Validator):
        name = Field(str, required=True)
        color = Field(str, required=True)

        class Meta:
            messages = {
                'name.required': 'enter your name',
                'required': 'please enter a value',
            }

Now the ``name`` field will have the error message "enter your name" but all other
required fields will use the other error message.

Excluding/Limiting Fields
=========================

It's possible to limit or exclude fields from validation. This can be done at the class level
or when calling ``validate()``.

This will only validate the ``name`` and ``color`` fields when ``validate()`` is called:

.. code:: python

    class SimpleValidator(Validator):
        name = Field(str, required=True)
        color = Field(str, required=True)
        age = Field(int, required=True)

        class Meta:
            only = ('name', 'color')

And similarly, you can override this when ``validate()`` is called:

.. code:: python

    validator = SimpleValidator()
    validator.validate(data, only=('color', 'name'))

Now only ``color`` and ``name`` will be validated, ignoring the definition on the class.

There's also an ``exclude`` attribute to exclude specific fields from validation. It works
the same way that ``only`` does.

Model Validation
================

You may be wondering why this package is called peewee-validates when nothing we have discussed
so far has anything to do with Peewee. Well here is where you find out. This package includes a
ModelValidator class for using the validators we already talked about to validate model instances.

.. code:: python

    import peewee
    from peewee_validates import ModelValidator

    class Category(peewee.Model):
        code = peewee.IntegerField(unique=True)
        name = peewee.CharField(max_length=250)

    obj = Category(code=42)

    validator = ModelValidator(obj)
    validator.validate()

In this case, the ModelValidator has built a Validator class that looks like this:

.. code:: python

    class CategoryValidator(Validator):
        code = peewee.Field(int, required=True, validators=[validate_unique])
        name = peewee.Field(str, required=True, max_length=250)

We can then use the validator to validate data.

By default, it will validate the data directly on the model instance, but you can always pass
a dictionary to ``validates`` that will override any data on the instance.

.. code:: python

    obj = Category(code=42)
    data = {'code': 'notnum'}

    rv = ModelValidator(obj).validate(data)

    Result(data={}, errors={'code': 'must be a number'})

This fails validation because the data passed in was not a number, even though the data on the
instance was valid.

You can also create a subclass of ``ModelValidator`` to use all the other things we have
shown already:

.. code:: python

    import peewee
    from peewee_validates import ModelValidator

    class CategoryValidator(ModelValidator):
        class Meta:
            messages = {
                'name.required': 'enter your name',
                'required': 'please enter a value',
            }

    rv = ModelValidator(obj).validate(data)

When validations is successful for ModelValidator, the resulting data will be the model
instance with updated data, instead of a dict. A new instance is not created.
It's the same instance we passed to ModelValidator, just mutated.

.. code:: python

    rv = ModelValidator(obj).validate(data)
    print(rv)
    Result(data=<models.Category object at 0x10ff825f8>, errors={})

Field Validations
-----------------

Using the ModelValidator provides a couple extra goodies that are not found in the standard
Validator class.

*Unique*

If the Peewee field was defined with ``unique=True`` then a validator will be added to the
field that will look up the value in the database to make sure it's unique. This is smart enough
to know to exclude the current instance if it has already been saved to the database.

*Foreign Key*

If the Peewee field is a ``ForeignKeyField`` then a validator will be added to the field
that will look up the value in the related table to make sure it's valid.

*Index Validation*

If you have defined unique indexes on the model like the example below, they will also
be validated (after all the other field level validations have succeeded).

.. code:: python

    class Category(peewee.Model):
        code = peewee.IntegerField(unique=True)
        name = peewee.CharField(max_length=250)

        class Meta:
            indexes = (
                (('name', 'code'), True),
            )

Field Overrides
===============

If you need to change the way a model field is validated, you can simply override the field
in your custom class. Given the following model:

.. code:: python

    class Category(peewee.Model):
        code = peewee.IntegerField(required=True)

This would generate a field for ``code`` with a required validator.

    class CategoryValidator(ModelValidator):
        code = Field(int, required=False)

    validator = CategoryValidator(category).validate()

Now ``code`` will not be required when the call to ``validate`` happens.

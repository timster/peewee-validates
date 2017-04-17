Basic Validation
================

The very basic usage is a validator class that looks like this:

.. code:: python

    from peewee_validates import Validator, StringField, validate_not_empty

    class SimpleValidator(Validator):
        first_name = StringField(validators=[validate_not_empty()])

    validator = SimpleValidator()

This tells us that we want to validate data for one field (first_name).

Each field has an associated data type. In this case, using StringField will coerce the input data
to ``str``.

After creating an instance of our valitdator, then we call the ``validate()`` method and
pass the data that we want to validate. The result we get back is a boolean indicating whether
all validations were successful.

The validator then has two dictionaries that you mway want to access: ``data`` and ``errors``.

``data`` is the input data that may have been mutated after validations.

``errors`` is a dictionary of any error messages.

.. code:: python

    data = {'first_name': ''}
    validator.validate(data)

    print(validator.data)
    # {}

    print(validator.errors)
    # {'first_name': 'This field is required'}

In this case we can see that there was one error for ``first_name``.
That's because we gave it the ``validate_not_empty()`` validator but did not pass any data for
that field. Also notice that the ``data`` dict is empty because the validators did not pass.

When we pass data that matches all validators, the ``errors`` dict will be empty and the ``data``
dict will be populated:

.. code:: python

    data = {'first_name': 'Tim'}
    validator.validate(data)

    print(validator.data)
    # {'first_name': 'Tim'}

    print(validator.errors)
    # {}

The ``data`` dict will contain the values after any validators, type coersions, and
any other custom modifiers. Also notice that we are able to reuse the same validator instance
while passing a new data dict.

Data Type Coersion
------------------

One of the first processes that happens when data validation takes place is data type coersion.

There are a number of different fields built-in. Check out the full list in the API Documentation.

Here's an example of a field.
This just duplicates the functionality of ``IntegerField`` to show you an as example.

.. code:: python

    class CustomIntegerField(Field):
        def coerce(self, value):
            try:
                return int(value)
            except (TypeError, ValueError):
                raise ValidationError('coerce_int')

    class SimpleValidator(Validator):
        code = CustomIntegerField()

    validator = SimpleValidator()
    validator.validate({'code': 'text'})

    validator.data
    # {}

    validator.errors
    # {'code': 'Must be a valid integer.'}

Available Validators
====================

There are a bunch of built-in validators that can be accessed by importing from ``peewee_validates``.

* ``validate_email()`` - validate that data is an email address
* ``validate_equal(value)`` - validate that data is equal to ``value``
* ``validate_function(method, **kwargs)`` - runs ``method`` with field value as first argument and ``kwargs`` and alidates that the result is truthy
* ``validate_length(low, high, equal)`` - validate that length is between ``low`` and ``high`` or equal to ``equal``
* ``validate_none_of(values)`` - validate that value is not in ``values``. ``values`` can also be a callable that returns values when called
* ``validate_not_empty()`` - validate that data is not empty
* ``validate_one_of(values)`` - validate that value is in ``values``. ``values`` can also be a callable that returns values when called
* ``validate_range(low, high)`` - validate that value is between ``low`` and ``high``
* ``validate_regexp(pattern, flags=0)`` - validate that value matches ``patten``
* ``validate_required()`` - validate that the field is present

Custom Validators
=================

A field validator is just a method with the signature ``validator(field, data)`` where
field is a ``Field`` instance and ``data`` is the data dict that is passed to ``validate()``.

If we want to implement a validator that makes sure the name is always "tim" we could do it
like this:

.. code:: python

    def always_tim(field, data):
        if field.value and field.value != 'tim':
            raise ValidationError('not_tim')

    class SimpleValidator(Validator):
        name = StringField(validators=[always_tim])

    validator = SimpleValidator()
    validator.validate({'name': 'bob'})

    validator.errors
    # {'name': 'Validation failed.'}

That's not a very pretty error message, but I'll show you soon how to customize that.

Now let's say you want to implement a validator that checks the length of the field.
The length should be configurable. So we can implement a validator that accepts a parameter
and returns a validator function. We basically wrap our actual validator function with
another function. That looks like this:

.. code:: python

    def length(max_length):
        def validator(field, data):
            if field.value and len(field.value) > max_length:
                raise ValidationError('too_long')
        return validator

    class SimpleValidator(Validator):
        name = StringField(validators=[length(2)])

    validator = SimpleValidator()
    validator.validate({'name': 'bob'})

    validator.errors
    # {'name': 'Validation failed.'}

Custom Error Messages
=====================

In some of the previous examples, we saw that the default error messages are not always that
friendly. Error messages can be changed by settings the ``messages`` attribute on the ``Meta``
class. Error messages are looked up by a key, and optionally prefixed with the field name.

The key is the first argument passed to ``ValidationError`` when an error is raised.

.. code:: python

    class SimpleValidator(Validator):
        name = StringField(required=True)

        class Meta:
            messages = {
                'required': 'Please enter a value.'
            }

Now any field that is required will have the error message "please enter a value".
We can also change this for specific fields by prefixing with field name:

.. code:: python

    class SimpleValidator(Validator):
        name = StringField(required=True)
        color = StringField(required=True)

        class Meta:
            messages = {
                'name.required': 'Enter your name.',
                'required': 'Please enter a value.',
            }

Now the ``name`` field will have the error message "Enter your name." but all other
required fields will use the other error message.

Excluding/Limiting Fields
=========================

It's possible to limit or exclude fields from validation. This can be done at the class level
or when calling ``validate()``.

This will only validate the ``name`` and ``color`` fields when ``validate()`` is called:

.. code:: python

    class SimpleValidator(Validator):
        name = StringField(required=True)
        color = StringField(required=True)
        age = IntegerField(required=True)

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

    unique_code_validator = validate_model_unique(
        Category.code, Category.select(), pk_field=Category.id, pk_value=obj.id)

    class CategoryValidator(Validator):
        code = peewee.IntegerField(
            required=True,
            validators=[unique_code_validator])
        name = peewee.StringField(required=True, max_length=250)

Notice the many things that have been defined in our model that have been automatically converted
to validator attributes:

* name is required string
* name must be 250 character or less
* code is required integer
* code must be a unique value in the table

We can then use the validator to validate data.

By default, it will validate the data directly on the model instance, but you can always pass
a dictionary to ``validates`` that will override any data on the instance.

.. code:: python

    obj = Category(code=42)
    data = {'code': 'notnum'}

    validator = ModelValidator(obj)
    validator.validate(data)

    validator.errors
    # {'code': 'Must be a valid integer.'}

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
                'name.required': 'Enter your name.',
                'required': 'Please enter a value.',
            }

    validator = ModelValidator(obj)
    validator.validate(data)

When validations is successful for ModelValidator, the given model instance will have been mutated.

.. code:: python

    validator = ModelValidator(obj)

    obj.name
    # 'tim'

    validator.validate({'name': 'newname'})

    obj.name
    # 'newname'

Field Validations
-----------------

Using the ModelValidator provides a couple extra goodies that are not found in the standard
Validator class.

**Uniqueness**

If the Peewee field was defined with ``unique=True`` then a validator will be added to the
field that will look up the value in the database to make sure it's unique. This is smart enough
to know to exclude the current instance if it has already been saved to the database.

**Foreign Key**

If the Peewee field is a ``ForeignKeyField`` then a validator will be added to the field
that will look up the value in the related table to make sure it's a valid instance.

**Many to Many**

If the Peewee field is a ``ManyToManyField`` then a validator will be added to the field
that will look up the values in the related table to make sure it's valid list of instances.

**Index Validation**

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

.. code:: python

    class CategoryValidator(ModelValidator):
        code = IntegerField(required=False)

    validator = CategoryValidator(category)
    validator.validate()

Now ``code`` will not be required when the call to ``validate`` happens.

Overriding Behaviors
====================

Cleaning
--------

Once all field-level data has been validated during ``validate()``, the resulting data is
passed to the ``clean()`` method before being returned in the result. You can override this
method to perform any validations you like, or mutate the data before returning it.

.. code:: python

    class MyValidator(Validator):
        name1 = StringField()
        name2 = StringField()

        def clean(self, data):
            # make sure name1 is the same as name2
            if data['name1'] != data['name2']:
                raise ValidationError('name_different')
            # and if they are the same, uppercase them
            data['name1'] = data['name1'].upper()
            data['name2'] = data['name2'].upper()
            return data

        class Meta:
            messages = {
                'name_different': 'The names should be the same.'
            }

Adding Fields Dynamically
-------------------------

If you need to, you can dynamically add a field to a validator instance.
They are stored in the ``_meta.fields`` dict, which you can manipulate as much as you want.

.. code:: python

    validator = MyValidator()
    validator._meta.fields['newfield'] = IntegerField(required=True)

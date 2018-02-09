"""peewee-validates is a validator module designed to work with the Peewee ORM."""

import datetime
import re
from decimal import Decimal
from decimal import InvalidOperation
from inspect import isgeneratorfunction
from inspect import isgenerator
from collections import Iterable

import peewee
from dateutil.parser import parse as dateutil_parse
try:
    from playhouse.fields import ManyToManyField
except ImportError:
    from peewee import ManyToManyField

__version__ = '1.0.7'

__all__ = [
    'Field', 'Validator', 'ModelValidator', 'ValidationError', 'StringField', 'FloatField',
    'IntegerField', 'DecimalField', 'DateField', 'TimeField', 'DateTimeField', 'BooleanField',
    'ModelChoiceField', 'ManyModelChoiceField',
]

PEEWEE3 = peewee.__version__ >= '3.0.0'

DEFAULT_MESSAGES = {
    'required': 'This field is required.',
    'empty': 'This field must not be blank.',
    'one_of': 'Must be one of the choices: {choices}.',
    'none_of': 'Must not be one of the choices: {choices}.',
    'equal': 'Must be equal to {other}.',
    'regexp': 'Must match the pattern {pattern}.',
    'matches': 'Must match the field {other}.',
    'email': 'Must be a valid email address.',
    'function': 'Failed validation for {function}.',
    'length_high': 'Must be at most {high} characters.',
    'length_low': 'Must be at least {low} characters.',
    'length_between': 'Must be between {low} and {high} characters.',
    'length_equal': 'Must be exactly {equal} characters.',
    'range_high': 'Must be at most {high}.',
    'range_low': 'Must be at least {low}.',
    'range_between': 'Must be between {low} and {high}.',
    'coerce_decimal': 'Must be a valid decimal.',
    'coerce_date': 'Must be a valid date.',
    'coerce_time': 'Must be a valid time.',
    'coerce_datetime': 'Must be a valid datetime.',
    'coerce_float': 'Must be a valid float.',
    'coerce_int': 'Must be a valid integer.',
    'related': 'Unable to find object with {field} = {values}.',
    'list': 'Must be a list of values',
    'unique': 'Must be a unique value.',
    'index': 'Fields must be unique together.',
}


class ValidationError(Exception):
    """An exception class that should be raised when a validation error occurs on data."""
    def __init__(self, key, *args, **kwargs):
        self.key = key
        self.kwargs = kwargs
        super().__init__(*args)


def validate_required():
    """
    Validate that a field is present in the data.

    :raises: ``ValidationError('required')``
    """
    def required_validator(field, data):
        if field.value is None:
            raise ValidationError('required')
    return required_validator


def validate_not_empty():
    """
    Validate that a field is not empty (blank string).

    :raises: ``ValidationError('empty')``
    """
    def empty_validator(field, data):
        if isinstance(field.value, str) and not field.value.strip():
            raise ValidationError('empty')
    return empty_validator


def validate_length(low=None, high=None, equal=None):
    """
    Validate the length of a field with either low, high, or equal.
    Should work with anything that supports len().

    :param low: Smallest length required.
    :param high: Longest length required.
    :param equal: Exact length required.
    :raises: ``ValidationError('length_low')``
    :raises: ``ValidationError('length_high')``
    :raises: ``ValidationError('length_between')``
    :raises: ``ValidationError('length_equal')``
    """
    def length_validator(field, data):
        if field.value is None:
            return
        if equal is not None and len(field.value) != equal:
            raise ValidationError('length_equal', equal=equal)
        if low is not None and len(field.value) < low:
            key = 'length_low' if high is None else 'length_between'
            raise ValidationError(key, low=low, high=high)
        if high is not None and len(field.value) > high:
            key = 'length_high' if low is None else 'length_between'
            raise ValidationError(key, low=low, high=high)
    return length_validator


def validate_one_of(values):
    """
    Validate that a field is in one of the given values.

    :param values: Iterable of valid values.
    :raises: ``ValidationError('one_of')``
    """
    def one_of_validator(field, data):
        if field.value is None:
            return
        options = values
        if callable(options):
            options = options()
        if field.value not in options:
            raise ValidationError('one_of', choices=', '.join(map(str, options)))
    return one_of_validator


def validate_none_of(values):
    """
    Validate that a field is not in one of the given values.

    :param values: Iterable of invalid values.
    :raises: ``ValidationError('none_of')``
    """
    def none_of_validator(field, data):
        options = values
        if callable(options):
            options = options()
        if field.value in options:
            raise ValidationError('none_of', choices=str.join(', ', options))
    return none_of_validator


def validate_range(low=None, high=None):
    """
    Validate the range of a field with either low, high, or equal.
    Should work with anything that supports '>' and '<' operators.

    :param low: Smallest value required.
    :param high: Longest value required.
    :raises: ``ValidationError('range_low')``
    :raises: ``ValidationError('range_high')``
    :raises: ``ValidationError('range_between')``
    """
    def range_validator(field, data):
        if field.value is None:
            return
        if low is not None and field.value < low:
            key = 'range_low' if high is None else 'range_between'
            raise ValidationError(key, low=low, high=high)
        if high is not None and field.value > high:
            key = 'range_high' if high is None else 'range_between'
            raise ValidationError(key, low=low, high=high)
    return range_validator


def validate_equal(value):
    """
    Validate the field value is equal to the given value.
    Should work with anything that supports '==' operator.

    :param value: Value to compare.
    :raises: ``ValidationError('equal')``
    """
    def equal_validator(field, data):
        if field.value is None:
            return
        if not (field.value == value):
            raise ValidationError('equal', other=value)
    return equal_validator


def validate_matches(other):
    """
    Validate the field value is equal to another field in the data.
    Should work with anything that supports '==' operator.

    :param value: Field key to compare.
    :raises: ``ValidationError('matches')``
    """
    def matches_validator(field, data):
        if field.value is None:
            return
        if not (field.value == data.get(other)):
            raise ValidationError('matches', other=other)
    return matches_validator


def validate_regexp(pattern, flags=0):
    """
    Validate the field matches the given regular expression.
    Should work with anything that supports '==' operator.

    :param pattern: Regular expresion to match. String or regular expression instance.
    :param pattern: Flags for the regular expression.
    :raises: ``ValidationError('equal')``
    """
    regex = re.compile(pattern, flags) if isinstance(pattern, str) else pattern

    def regexp_validator(field, data):
        if field.value is None:
            return
        if regex.match(str(field.value)) is None:
            raise ValidationError('regexp', pattern=pattern)
    return regexp_validator


def validate_function(method, **kwargs):
    """
    Validate the field matches the result of calling the given method. Example::

        def myfunc(value, name):
            return value == name

        validator = validate_function(myfunc, name='tim')

    Essentially creates a validator that only accepts the name 'tim'.

    :param method: Method to call.
    :param kwargs: Additional keyword arguments passed to the method.
    :raises: ``ValidationError('function')``
    """
    def function_validator(field, data):
        if field.value is None:
            return
        if not method(field.value, **kwargs):
            raise ValidationError('function', function=method.__name__)
    return function_validator


def validate_email():
    """
    Validate the field is a valid email address.

    :raises: ``ValidationError('email')``
    """
    user_regex = re.compile(
        r"(^[-!#$%&'*+/=?^`{}|~\w]+(\.[-!#$%&'*+/=?^`{}|~\w]+)*$"
        r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]'
        r'|\\[\001-\011\013\014\016-\177])*"$)', re.IGNORECASE | re.UNICODE)

    domain_regex = re.compile(
        r'(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+'
        r'(?:[A-Z]{2,6}|[A-Z0-9-]{2,})$'
        r'|^\[(25[0-5]|2[0-4]\d|[0-1]?\d?\d)'
        r'(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}\]$', re.IGNORECASE | re.UNICODE)

    domain_whitelist = ('localhost',)

    def email_validator(field, data):
        if field.value is None:
            return

        value = str(field.value)

        if '@' not in value:
            raise ValidationError('email')

        user_part, domain_part = value.rsplit('@', 1)

        if not user_regex.match(user_part):
            raise ValidationError('email')

        if domain_part in domain_whitelist:
            return

        if not domain_regex.match(domain_part):
            raise ValidationError('email')

    return email_validator


def validate_model_unique(lookup_field, queryset, pk_field=None, pk_value=None):
    """
    Validate the field is a unique, given a queryset and lookup_field. Example::

        validator = validate_model_unique(User.email, User.select())

    Creates a validator that can validate the uniqueness of an email address.

    :param lookup_field: Peewee model field that should be used for checking existing values.
    :param queryset: Queryset to use for lookup.
    :param pk_field: Field instance to use when excluding existing instance.
    :param pk_value: Field value to use when excluding existing instance.
    :raises: ``ValidationError('unique')``
    """
    def unique_validator(field, data):
        # If we have a PK, ignore it because it represents the current record.
        query = queryset.where(lookup_field == field.value)
        if pk_field and pk_value:
            query = query.where(~(pk_field == pk_value))
        if query.count():
            raise ValidationError('unique')
    return unique_validator


def coerce_single_instance(lookup_field, value):
    """
    Convert from whatever value is given to a scalar value for lookup_field.
    If value is a dict, then lookup_field.name is used to get the value from the dict. Example:
        lookup_field.name = 'id'
        value = {'id': 123, 'name': 'tim'}
        returns = 123
    If value is a model, then lookup_field.name is extracted from the model. Example:
        lookup_field.name = 'id'
        value = <User id=123 name='tim'>
        returns = 123
    Otherwise the value is returned as-is.

    :param lookup_field: Peewee model field used for getting name from value.
    :param value: Some kind of value (usually a dict, Model instance, or scalar).
    """
    if isinstance(value, dict):
        return value.get(lookup_field.name)
    if isinstance(value, peewee.Model):
        return getattr(value, lookup_field.name)
    return value


def isiterable_notstring(value):
    """
    Returns True if the value is iterable but not a string. Otherwise returns False.

    :param value: Value to check.
    """
    if isinstance(value, str):
        return False
    return isinstance(value, Iterable) or isgeneratorfunction(value) or isgenerator(value)


class Field:
    """
    Base class from which all other fields should be derived.

    :param default: Is this field required?
    :param default: Default value to be used if no incoming value is provided.
    :param validators: List of validator functions to run.
    """

    __slots__ = ('value', 'required', 'default', 'validators')

    def __init__(self, required=False, default=None, validators=None):
        self.default = default
        self.value = None
        self.validators = validators or []
        if required:
            self.validators.append(validate_required())

    def coerce(self, value):
        """
        Coerce the given value into some type. By default a no-op.
        Used by sub-classes to enforce specific types.
        If there is a problem with the coersion, raise ValidationError.

        :param value: Value to coerce.
        :raises: ValidationError
        :return: The updated value.
        :rtype: any
        """
        return value

    def get_value(self, name, data):
        """
        Get the value of this field from the data.
        If there is a problem with the data, raise ValidationError.

        :param name: Name of this field (to retrieve from data).
        :param data: Dictionary of data for all fields.
        :raises: ValidationError
        :return: The value of this field.
        :rtype: any
        """
        if name in data:
            return data.get(name)
        if self.default:
            if callable(self.default):
                return self.default()
            return self.default
        return None

    def validate(self, name, data):
        """
        Check to make sure ths data for this field is valid.
        Usually runs all validators in self.validators list.
        If there is a problem with the data, raise ValidationError.

        :param name: The name of this field.
        :param data: Dictionary of data for all fields.
        :raises: ValidationError
        """
        self.value = self.get_value(name, data)
        if self.value is not None:
            self.value = self.coerce(self.value)
        for method in self.validators:
            method(self, data)


class StringField(Field):
    """
    A field that will try to coerce value to a string.

    :param required: Is this field required?
    :param default: Default value to be used if no incoming value is provided.
    :param validators: List of validator functions to run.
    :param max_length: Maximum length that should be enfocred.
    :param min_length: Minimum length that should be enfocred.
    """

    __slots__ = ('value', 'required', 'default', 'validators')

    def __init__(self, required=False, max_length=None, min_length=None, default=None, validators=None):
        validators = validators or []
        if max_length or min_length:
            validators.append(validate_length(high=max_length, low=min_length))
        super().__init__(required=required, default=default, validators=validators)

    def coerce(self, value):
        return str(value)


class FloatField(Field):
    """
    A field that will try to coerce value to a float.

    :param required: Is this field required?
    :param default: Default value to be used if no incoming value is provided.
    :param validators: List of validator functions to run.
    :param low: Lowest value that should be enfocred.
    :param high: Highest value that should be enfocred.
    """

    __slots__ = ('value', 'required', 'default', 'validators')

    def __init__(self, required=False, low=None, high=None, default=None, validators=None):
        validators = validators or []
        if low or high:
            validators.append(validate_range(low=low, high=high))
        super().__init__(required=required, default=default, validators=validators)

    def coerce(self, value):
        try:
            return float(value) if value else None
        except (TypeError, ValueError):
            raise ValidationError('coerce_float')


class IntegerField(Field):
    """
    A field that will try to coerce value to an integer.

    :param required: Is this field required?
    :param default: Default value to be used if no incoming value is provided.
    :param validators: List of validator functions to run.
    :param low: Lowest value that should be enfocred.
    :param high: Highest value that should be enfocred.
    """

    __slots__ = ('value', 'required', 'default', 'validators')

    def __init__(self, required=False, low=None, high=None, default=None, validators=None):
        validators = validators or []
        if low or high:
            validators.append(validate_range(low=low, high=high))
        super().__init__(required=required, default=default, validators=validators)

    def coerce(self, value):
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            raise ValidationError('coerce_int')


class DecimalField(Field):
    """
    A field that will try to coerce value to a decimal.

    :param required: Is this field required?
    :param default: Default value to be used if no incoming value is provided.
    :param validators: List of validator functions to run.
    :param low: Lowest value that should be enfocred.
    :param high: Highest value that should be enfocred.
    """

    __slots__ = ('value', 'required', 'default', 'validators')

    def __init__(self, required=False, low=None, high=None, default=None, validators=None):
        validators = validators or []
        if low or high:
            validators.append(validate_range(low=low, high=high))
        super().__init__(required=required, default=default, validators=validators)

    def coerce(self, value):
        try:
            return Decimal(value) if value else None
        except (TypeError, ValueError, InvalidOperation):
            raise ValidationError('coerce_decimal')


class DateField(Field):
    """
    A field that will try to coerce value to a date.
    Can accept a date object, string, or anything else that can be converted
    by `dateutil.parser.parse`.

    :param required: Is this field required?
    :param default: Default value to be used if no incoming value is provided.
    :param validators: List of validator functions to run.
    :param low: Lowest value that should be enfocred.
    :param high: Highest value that should be enfocred.
    """

    __slots__ = ('value', 'required', 'default', 'validators')

    def __init__(self, required=False, low=None, high=None, default=None, validators=None):
        validators = validators or []
        if low or high:
            validators.append(validate_range(low=low, high=high))
        super().__init__(required=required, default=default, validators=validators)

    def coerce(self, value):
        if not value or isinstance(value, datetime.date):
            return value
        try:
            return dateutil_parse(value).date()
        except (TypeError, ValueError):
            raise ValidationError('coerce_date')


class TimeField(Field):
    """
    A field that will try to coerce value to a time.
    Can accept a time object, string, or anything else that can be converted
    by `dateutil.parser.parse`.

    :param required: Is this field required?
    :param default: Default value to be used if no incoming value is provided.
    :param validators: List of validator functions to run.
    :param low: Lowest value that should be enfocred.
    :param high: Highest value that should be enfocred.
    """

    __slots__ = ('value', 'required', 'default', 'validators')

    def __init__(self, required=False, low=None, high=None, default=None, validators=None):
        validators = validators or []
        if low or high:
            validators.append(validate_range(low=low, high=high))
        super().__init__(required=required, default=default, validators=validators)

    def coerce(self, value):
        if not value or isinstance(value, datetime.time):
            return value
        try:
            return dateutil_parse(value).time()
        except (TypeError, ValueError):
            raise ValidationError('coerce_time')


class DateTimeField(Field):
    """
    A field that will try to coerce value to a datetime.
    Can accept a datetime object, string, or anything else that can be converted
    by `dateutil.parser.parse`.

    :param required: Is this field required?
    :param default: Default value to be used if no incoming value is provided.
    :param validators: List of validator functions to run.
    :param low: Lowest value that should be enfocred.
    :param high: Highest value that should be enfocred.
    """

    __slots__ = ('value', 'required', 'default', 'validators')

    def __init__(self, required=False, low=None, high=None, default=None, validators=None):
        validators = validators or []
        if low or high:
            validators.append(validate_range(low=low, high=high))
        super().__init__(required=required, default=default, validators=validators)

    def coerce(self, value):
        if not value or isinstance(value, datetime.datetime):
            return value
        try:
            return dateutil_parse(value)
        except (TypeError, ValueError):
            raise ValidationError('coerce_datetime')


class BooleanField(Field):
    """
    A field that will try to coerce value to a boolean.
    By default the values is converted to string first, then compared to these values:
    values which are considered False: ('0', '{}', 'none', 'false')
    And everything else is True.
    """

    __slots__ = ('value', 'required', 'default', 'validators')

    false_values = ('0', '{}', '[]', 'none', 'false')

    def coerce(self, value):
        return not str(value).lower() in self.false_values


class ModelChoiceField(Field):
    """
    A field that allows for a single value based on a model query and lookup field.

    :param query: Query to use for lookup.
    :param lookup_field: Field that will be queried for the value.
    """

    __slots__ = ('query', 'lookup_field', 'value', 'required', 'default', 'validators')

    def __init__(self, query, lookup_field, required=False, **kwargs):
        self.query = query
        self.lookup_field = lookup_field
        super().__init__(required=required, **kwargs)

    def coerce(self, value):
        """Convert from whatever is given to a scalar value for lookup_field."""
        return coerce_single_instance(self.lookup_field, value)

    def validate(self, name, data):
        """
        If there is a problem with the data, raise ValidationError.

        :param name: The name of this field.
        :param data: Dictionary of data for all fields.
        :raises: ValidationError
        """
        super().validate(name, data)
        if self.value is not None:
            try:
                self.value = self.query.get(self.lookup_field == self.value)
            except (AttributeError, ValueError, peewee.DoesNotExist):
                raise ValidationError('related', field=self.lookup_field.name, values=self.value)


class ManyModelChoiceField(Field):
    """
    A field that allows for multiple values based on a model query and lookup field.

    :param query: Query to use for lookup.
    :param lookup_field: Field that will be queried for the value.
    """

    __slots__ = ('query', 'lookup_field', 'value', 'required', 'default', 'validators')

    def __init__(self, query, lookup_field, required=False, **kwargs):
        self.query = query
        self.lookup_field = lookup_field
        super().__init__(required=required, **kwargs)

    def coerce(self, value):
        """Convert from whatever is given to a list of scalars for the lookup_field."""
        if isinstance(value, dict):
            value = [value]
        if not isiterable_notstring(value):
            value = [value]
        return [coerce_single_instance(self.lookup_field, v) for v in value]

    def validate(self, name, data):
        """
        If there is a problem with the data, raise ValidationError.

        :param name: The name of this field.
        :param data: Dictionary of data for all fields.
        :raises: ValidationError
        """
        super().validate(name, data)
        if self.value is not None:
            try:
                # self.query could be a query like "User.select()" or a model like "User"
                # so ".select().where()" handles both cases.
                self.value = [self.query.select().where(self.lookup_field == v).get() for v in self.value if v]
            except (AttributeError, ValueError, peewee.DoesNotExist):
                raise ValidationError('related', field=self.lookup_field.name, values=self.value)


class ValidatorOptions:
    def __init__(self, obj):
        self.fields = {}
        self.messages = {}
        self.only = []
        self.exclude = []


class Validator:
    """
    A validator class. Can have many fields attached to it to perform validation on data.
    """

    class Meta:
        """
        A meta class to specify options for the validator. Uses the following fields:

            ``messages = {}``

            ``only = []``

            ``exclues = []``
        """
        pass

    __slots__ = ('data', 'errors', '_meta')

    def __init__(self):
        self.errors = {}
        self.data = {}

        self._meta = ValidatorOptions(self)
        self._meta.__dict__.update(self.Meta.__dict__)

        self.initialize_fields()

    def add_error(self, name, error):
        message = self._meta.messages.get('{}.{}'.format(name, error.key))
        if not message:
            message = self._meta.messages.get(error.key)
        if not message:
            message = DEFAULT_MESSAGES.get(error.key, 'Validation failed.')
        self.errors[name] = message.format(**error.kwargs)

    def initialize_fields(self):
        """
        The dict self.base_fields is a model instance at this point.
        Turn it into an instance attribute on this meta class.
        Also intitialize any other special fields if needed in sub-classes.

        :return: None
        """
        for field in dir(self):
            obj = getattr(self, field)
            if isinstance(obj, Field):
                self._meta.fields[field] = obj

    def validate(self, data=None, only=None, exclude=None):
        """
        Validate the data for all fields and return whether the validation was successful.
        This method also retains the validated data in ``self.data`` so that it can be accessed later.

        This is usually the method you want to call after creating the validator instance.

        :param data: Dictionary of data to validate.
        :param only: List or tuple of fields to validate.
        :param exclude: List or tuple of fields to exclude from validation.
        :return: True if validation was successful. Otherwise False.
        """
        only = only or []
        exclude = exclude or []
        data = data or {}
        self.errors = {}
        self.data = {}

        # Validate individual fields.
        for name, field in self._meta.fields.items():
            if name in exclude or (only and name not in only):
                continue
            try:
                field.validate(name, data)
            except ValidationError as err:
                self.add_error(name, err)
                continue
            self.data[name] = field.value

        # Clean individual fields.
        if not self.errors:
            self.clean_fields(self.data)

        # Then finally clean the whole data dict.
        if not self.errors:
            try:
                self.data = self.clean(self.data)
            except ValidationError as err:
                self.add_error('__base__', err)

        return (not self.errors)

    def clean_fields(self, data):
        """
        For each field, check to see if there is a clean_<name> method.
        If so, run that method and set the returned value on the self.data dict.
        This happens after all validations so that each field can act on the
        cleaned data of other fields if needed.

        :param data: Dictionary of data to clean.
        :return: None
        """
        for name, value in data.items():
            try:
                method = getattr(self, 'clean_{}'.format(name), None)
                if method:
                    self.data[name] = method(value)
            except ValidationError as err:
                self.add_error(name, err)
                continue

    def clean(self, data):
        """
        Clean the data dictionary and return the cleaned values.

        :param data: Dictionary of data for all fields.
        :return: Dictionary of "clean" values.
        :rtype: dict
        """
        return data


class ModelValidator(Validator):
    """
    A validator class based on a Peewee model instance.
    Fields are automatically added based on the model instance, but can be customized.

    :param instance: Peewee model instance to use for data lookups and field generation.
    """

    __slots__ = ('data', 'errors', '_meta', 'instance', 'pk_field', 'pk_value')

    FIELD_MAP = {
        'smallint': IntegerField,
        'bigint': IntegerField,
        'bool': BooleanField,
        'date': DateField,
        'datetime': DateTimeField,
        'decimal': DecimalField,
        'double': FloatField,
        'float': FloatField,
        'int': IntegerField,
        'time': TimeField,
    }

    def __init__(self, instance):
        if not isinstance(instance, peewee.Model):
            message = 'First argument to {} must be an instance of peewee.Model.'
            raise AttributeError(message.format(type(self).__name__))

        self.instance = instance
        self.pk_field = self.instance._meta.primary_key
        if PEEWEE3:
            self.pk_value = self.instance.get_id()
        else:
            self.pk_value = self.instance._get_pk_value()

        super().__init__()

    def initialize_fields(self):
        """
        Convert all model fields to validator fields.
        Then call the parent so that overwrites can happen if necessary for manually defined fields.

        :return: None
        """
        # # Pull all the "normal" fields off the model instance meta.
        for name, field in self.instance._meta.fields.items():
            if getattr(field, 'primary_key', False):
                continue
            self._meta.fields[name] = self.convert_field(name, field)

        # Many-to-many fields are not stored in the meta fields dict.
        # Pull them directly off the class.
        for name in dir(type(self.instance)):
            field = getattr(type(self.instance), name, None)
            if isinstance(field, ManyToManyField):
                self._meta.fields[name] = self.convert_field(name, field)

        super().initialize_fields()

    def convert_field(self, name, field):
        """
        Convert a single field from a Peewee model field to a validator field.

        :param name: Name of the field as defined on this validator.
        :param name: Peewee field instance.
        :return: Validator field.
        """
        if PEEWEE3:
            field_type = field.field_type.lower()
        else:
            field_type = field.db_field

        pwv_field = ModelValidator.FIELD_MAP.get(field_type, StringField)

        print('pwv_field', field_type, pwv_field)

        validators = []
        required = not bool(getattr(field, 'null', True))
        choices = getattr(field, 'choices', ())
        default = getattr(field, 'default', None)
        max_length = getattr(field, 'max_length', None)
        unique = getattr(field, 'unique', False)

        if required:
            validators.append(validate_required())

        if choices:
            print('CHOICES', choices)
            validators.append(validate_one_of([c[0] for c in choices]))

        if max_length:
            validators.append(validate_length(high=max_length))

        if unique:
            validators.append(validate_model_unique(field, self.instance.select(), self.pk_field, self.pk_value))

        if isinstance(field, peewee.ForeignKeyField):
            if PEEWEE3:
                rel_field = field.rel_field
            else:
                rel_field = field.to_field
            return ModelChoiceField(field.rel_model, rel_field, default=default, validators=validators)

        if isinstance(field, ManyToManyField):
            return ManyModelChoiceField(
                field.rel_model, field.rel_model._meta.primary_key,
                default=default, validators=validators)

        return pwv_field(default=default, validators=validators)

    def validate(self, data=None, only=None, exclude=None):
        """
        Validate the data for all fields and return whether the validation was successful.
        This method also retains the validated data in ``self.data`` so that it can be accessed later.

        If data for a field is not provided in ``data`` then this validator will check against the
        provided model instance.

        This is usually the method you want to call after creating the validator instance.

        :param data: Dictionary of data to validate.
        :param only: List or tuple of fields to validate.
        :param exclude: List or tuple of fields to exclude from validation.
        :return: True if validation is successful, otherwise False.
        """
        data = data or {}
        only = only or self._meta.only
        exclude = exclude or self._meta.exclude

        for name, field in self.instance._meta.fields.items():
            if name in exclude or (only and name not in only):
                continue
            try:
                data.setdefault(name, getattr(self.instance, name, None))
            except (peewee.DoesNotExist):
                if PEEWEE3:
                    instance_data = self.instance.__data__
                else:
                    instance_data = self.instance._data
                data.setdefault(name, instance_data.get(name, None))

        # This will set self.data which we should use from now on.
        super().validate(data=data, only=only, exclude=exclude)

        if not self.errors:
            self.perform_index_validation(self.data)

        return (not self.errors)

    def perform_index_validation(self, data):
        """
        Validate any unique indexes specified on the model.
        This should happen after all the normal fields have been validated.
        This can add error messages to multiple fields.

        :return: None
        """
        # Build a list of dict containing query values for each unique index.
        index_data = []
        for columns, unique in self.instance._meta.indexes:
            if not unique:
                continue
            index_data.append({col: data.get(col, None) for col in columns})

        # Then query for each unique index to see if the value is unique.
        for index in index_data:
            query = self.instance.filter(**index)
            # If we have a primary key, need to exclude the current record from the check.
            if self.pk_field and self.pk_value:
                query = query.where(~(self.pk_field == self.pk_value))
            if query.count():
                err = ValidationError('index', fields=str.join(', ', index.keys()))
                for col in index.keys():
                    self.add_error(col, err)

    def save(self, force_insert=False):
        """
        Save the model and any related many-to-many fields.

        :param force_insert: Should the save force an insert?
        :return: Number of rows impacted, or False.
        """
        delayed = {}
        for field, value in self.data.items():
            model_field = getattr(type(self.instance), field, None)

            # If this is a many-to-many field, we cannot save it to the instance until the instance
            # is saved to the database. Collect these fields and delay the setting until after
            # the model instance is saved.
            if isinstance(model_field, ManyToManyField):
                if value is not None:
                    delayed[field] = value
                continue

            setattr(self.instance, field, value)

        rv = self.instance.save(force_insert=force_insert)

        for field, value in delayed.items():
            setattr(self.instance, field, value)

        return rv

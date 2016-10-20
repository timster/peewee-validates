from collections import namedtuple
from copy import deepcopy
from decimal import Decimal
import datetime as dt
import re

from dateutil.parser import parse as dateutil_parse
from playhouse.fields import ManyToManyField
import peewee

__all__ = ['ValidationError', 'Field', 'Validator', 'ModelValidator']


DB_FIELD_MAP = {
    'bigint': int,
    'bool': bool,
    'date': 'date',
    'datetime': 'datetime',
    'decimal': 'decimal',
    'double': float,
    'float': float,
    'int': int,
    'time': 'time',
}


class ValidationError(Exception):
    def __init__(self, key, *args, **kwargs):
        self.key = key
        self.kwargs = kwargs
        super().__init__(*args)


def date(value):
    if isinstance(value, dt.date):
        return value
    return dateutil_parse(value).date()


def time(value):
    if isinstance(value, dt.time):
        return value
    return dateutil_parse(value).time()


def datetime(value):
    if isinstance(value, dt.datetime):
        return value
    return dateutil_parse(value)


# def foreignkey(value):
#     """coerce from instance or str to integer id"""
#     if isinstance(value, (str, int, float)):
#         return int(value)
#     if isinstance(value, peewee.Model):
#         return value.get_id()
#     return value


# def manytomany(value):
#     """coerce from list of instances or list of str to integer id"""
#     if not isinstance(value, (list, tuple)):
#         value = [value]
#     if value and isinstance(value[0], (str, int, float)):
#         return [int(x) for x in value]
#     if value and isinstance(value[0], peewee.Model):
#         return [obj.get_id() for obj in value]
#     return value


COERCE = {
    'str': str,
    'int': int,
    'float': float,
    'bool': bool,
    'decimal': Decimal,
    'date': date,
    'time': time,
    'datetime': datetime,
    # 'foreignkey': foreignkey,
    # 'manytomany': manytomany,
    'null': lambda v: v,
    None: lambda v: v,
}

Result = namedtuple('Result', ('data', 'errors'))


def validate_required():
    def required_validator(field, data):
        if field.value is None:
            raise ValidationError('required')
    return required_validator


def validate_empty():
    def required_validator(field, data):
        if isinstance(field.value, str) and not field.value.strip():
            raise ValidationError('empty')
    return required_validator


def validate_max_length(value):
    def max_length_validator(field, data):
        if field.value and len(field.value) > value:
            raise ValidationError('max_length', length=value)
    return max_length_validator


def validate_min_length(value):
    def min_length_validator(field, data):
        if field.value and len(field.value) < value:
            raise ValidationError('min_length', length=value)
    return min_length_validator


def validate_length(value):
    def length_validator(field, data):
        if field.value and len(field.value) != value:
            raise ValidationError('length', length=value)
    return length_validator


def validate_choices(values):
    def choices_validator(field, data):
        options = values
        if callable(options):
            options = options()
        if field.value not in options:
            raise ValidationError('choices', choices=str.join(', ', options))
    return choices_validator


def validate_exclude(values):
    def exclude_validator(field, data):
        options = values
        if callable(options):
            options = options()
        if field.value in options:
            raise ValidationError('exclude', choices=str.join(', ', options))
    return exclude_validator


def validate_range(low, high):
    def range_validator(field, data):
        if field.value and not low < field.value < high:
            raise ValidationError('range', low=low, high=high)
    return range_validator


def validate_equal(other):
    def equal_validator(field, data):
        if field.value and field.value != other:
            raise ValidationError('equal', other=other)
    return equal_validator


def validate_regexp(pattern, flags=0):
    regex = re.compile(pattern, flags) if isinstance(pattern, str) else pattern

    def regexp_validator(field, data):
        if field.value and regex.match(str(field.value)) is None:
            raise ValidationError('regexp', pattern=pattern)
    return regexp_validator


def validate_function(method, **kwargs):
    def function_validator(field, data):
        if not method(field.value, **kwargs):
            raise ValidationError('function', function=method.__name__)
    return function_validator


def validate_email():
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
        if field.value and '@' not in field.value:
            raise ValidationError('email')

        user_part, domain_part = field.value.rsplit('@', 1)

        if not user_regex.match(user_part):
            raise ValidationError('email')

        if domain_part in domain_whitelist:
            return

        if not domain_regex.match(domain_part):
            raise ValidationError('email')

    return email_validator


class Field:

    def __init__(self, coerce=None, default=None, required=False, empty=True,
                 max_length=None, min_length=None, choices=None, range=None, validators=None):
        """
        Initialize a field, mostly used for validation and coersion purposes.

        :param coerce: Method (or name of predefined method) to coerce value.
        :param default: Default value to use if none is provided.
        :param required: Shortcut to add validate_required() validator.
        :param empty: Shortcut to add validate_empty() validator.
        :param max_length: Shortcut to add validate_max_length() validator.
        :param min_length: Shortcut to add validate_min_length() validator.
        :param choices: Shortcut to add validate_choices() validator.
        :param range: Shortcut to add validate_range() validator.
        :param validators: List or tuple of validators to run.
        """
        self.name = None
        self.provided = False
        self.value = None
        self.default = default
        self.validators = []

        if required:
            self.validators.append(validate_required())

        if not empty:
            self.validators.append(validate_empty())

        if max_length:
            self.validators.append(validate_max_length(int(max_length)))

        if min_length:
            self.validators.append(validate_min_length(int(min_length)))

        if choices:
            self.validators.append(validate_choices(choices))

        if range:
            self.validators.append(validate_range(range[0], range[1]))

        if validators:
            self.validators.extend(validators)

        if isinstance(coerce, str):
            coerce = COERCE.get(coerce, None)
        self.coerce = coerce

    def get_value(self, data):
        """
        Get the value of this field from the data.
        If there is a problem with the data, raise ValidationError.

        :param data: Dictionary of data for all fields.
        :raises: ValidationError
        :return: The value of this field.
        :rtype: any
        """
        if self.name in data:
            return data.get(self.name)
        if callable(self.default):
            return self.default()
        return self.default

    def to_python(self, value):
        """
        Convert the value from naive format to python format.

        :raises: ValidationError
        :return: The value of this field.
        :rtype: any
        """
        if self.coerce and value is not None:
            try:
                return self.coerce(value)
            except ValueError:
                raise ValidationError('coerce_{}'.format(self.coerce.__name__).lower())
        return value

    def validate(self, name, data):
        """
        Validate the data in this field and return the validated, cleaned value.
        If there is a problem with the data, raise ValidationError.

        :param name: The name of this field.
        :param data: Dictionary of data for all fields.
        :raises: ValidationError
        :return: None
        """
        self.name = name
        self.value = self.to_python(self.get_value(data))

        for method in self.validators:
            method(self, data)


class ValidatorOptions:
    def __init__(self, obj):
        self.fields = {}
        self.only = ()
        self.exclude = ()
        self.messages = {}
        self.default_messages = {
            'required': 'must be provided',
            'empty': 'must not be empty',
            'choices': 'must be one of the choices: {choices}',
            'exclude': 'must not be one of the choices: {choices}',
            'range': 'must be in the range {low} to {high}',
            'max_length': 'must be at most {length} characters',
            'min_length': 'must be at least {length} characters',
            'length': 'must be exactly {length} characters',
            'equal': 'must be equal to {other}',
            'regexp': 'must match the pattern {pattern}',
            'email': 'must be a valid email address',
            'function': 'failed validation for {function}',
            'unique': 'must be a unique value',
            'related': 'unable to find related object',
            'index': 'fields must be unique together',
            'coerce_decimal': 'must be a valid decimal',
            'coerce_date': 'must be a valid date',
            'coerce_time': 'must be a valid time',
            'coerce_datetime': 'must be a valid datetime',
            'coerce_str': 'must be a valid string',
            'coerce_float': 'must be a valid float',
            'coerce_int': 'must be a valid integer',
            'coerce_bool': 'must be a valid bool',
            # 'coerce_foreignkey': 'must be instance or foreign key',
            # 'coerce_manytomany': 'must be instance or foreign key',
        }


class MetaValidator(type):
    def __new__(mcs, name, bases, attrs):
        # Collect fields from current class.
        current_fields = {}
        for key, value in list(attrs.items()):
            if isinstance(value, Field):
                current_fields[key] = value
                attrs.pop(key)
        attrs['declared_fields'] = current_fields

        new_class = super().__new__(mcs, name, bases, attrs)

        # Walk through the MRO.
        declared_fields = {}
        for base in reversed(new_class.__mro__):
            # Collect fields from base class.
            if hasattr(base, 'declared_fields'):
                declared_fields.update(base.declared_fields)

        new_class.base_fields = declared_fields
        new_class.declared_fields = declared_fields

        return new_class


class Validator(metaclass=MetaValidator):
    class Meta:
        pass

    def __init__(self):
        """
        Initialize a validator instance.

        :param default: Dictionary of default values to use if no data is passed to validate().
        """
        self.data = {}
        self.errors = {}

        self._meta = ValidatorOptions(self)
        self._meta.__dict__.update(self.Meta.__dict__)

        self.initialize_fields()

    def initialize_fields(self):
        """
        The dict self.base_fields is a model instance at this point.
        Turn it into an instance attribute on this meta class.
        Also intitialize any other special fields if needed.

        :return: None
        """
        self._meta.fields.update(deepcopy(self.base_fields))

    def add_error(self, exc, field):
        """
        Add an error message for the given field and key.
        Key will use a lookup in the messages dict to figure out which message to add.

        :param exc: ValidationError instance.
        :param field: Field that threw the error.
        :return: None
        """
        key = exc.key
        message = self._meta.messages.get('{}.{}'.format(field, key), self._meta.messages.get(key))
        if not message:
            message = self._meta.default_messages.get(key, 'invalid: {}'.format(key))
        self.errors[field] = message.format(**exc.kwargs)

    def validate_fields(self, data=None, only=None, exclude=None):
        """
        Validate the data for all fields.
        Update the self.data dict and self.errors dict based on data and errors.

        :param data: Dictionary of data to validate.
        :param only: List or tuple of fields to validate.
        :param exclude: List or tuple of fields to exclude from validation.
        :return: None
        """
        data = data or {}
        only = only or self._meta.only
        exclude = exclude or self._meta.exclude

        # Loop through all fields so we can run validations on them.
        for name, field in self._meta.fields.items():
            if name in exclude or (only and name not in only):
                continue
            try:
                field.validate(name, data)
                self.data[name] = field.value
            except ValidationError as exc:
                self.add_error(exc, field.name)
                continue

    def clean_fields(self, data=None):
        """
        For each field, check to see if there is a clean_<name> method.
        If so, run that method and set the returned value on the self.data dict.
        This happens after all validations so that each field can act on the
        cleaned data of other fields if needed.

        :param data: Dictionary of data to clean.
        :return: None
        """
        data = data or {}

        if not self.errors:
            for name, value in data.items():
                try:
                    method = getattr(self, 'clean_{}'.format(name), None)
                    if method:
                        self.data[name] = method(value)
                except ValidationError as exc:
                    self.add_error(exc, name)
                    continue

    def clean(self, data):
        """
        Clean the data dictionary and return the cleaned values.

        :param data: Dictionary of data for all fields.
        :return: Dictionary of "clean" values.
        :rtype: dict
        """
        return data

    def validate(self, data=None, only=None, exclude=None):
        """
        Validate the data for all fields and return whether the validation was successful.
        This method also retains the data in `data` so that it can be accessed later.

        :param data: Dictionary of data to validate.
        :param only: List or tuple of fields to validate.
        :param exclude: List or tuple of fields to exclude from validation.
        :return: Tuple of (data, errors).
        """
        data = data or {}
        self.errors = {}
        self.data = {}

        self.validate_fields(data, only, exclude)
        self.clean_fields(data)

        # Clean data (not specific to one field).
        if not self.errors:
            try:
                self.data = self.clean(self.data)
            except ValidationError as exc:
                self.add_error(exc, '__base__')

        # return Result(self.data, self.errors)
        return (not self.errors)


def validate_unique(queryset, lookup_field, pk_field, pk_value):
    """Validate that the given lookup field is unique within the queryset."""
    def unique_validator(field, data):
        query = queryset.where(lookup_field == field.value)
        if pk_field and pk_value:
            query = query.where(pk_field != pk_value)
        if query.count():
            raise ValidationError('unique')
    return unique_validator


def validate_related(instance, lookup_field):
    def related_validator(field, data):
        if field.value is not None:
            try:
                lookup_field.rel_model.get(lookup_field.to_field == field.value)
            except lookup_field.rel_model.DoesNotExist:
                raise ValidationError('related')
    return related_validator


def validate_manytomany(instance, lookup_field):
    def related_validator(field, data):
        def get_id_list():
            """Construct a list of instance IDs."""
            id_list = field.value
            if not isinstance(id_list, (list, tuple)):
                id_list = [id_list]
            if id_list and isinstance(id_list[0], peewee.Model):
                id_list = [obj.get_id() for obj in id_list]
            return id_list

        if field.value is not None:
            related = lookup_field.rel_model
            for pk in get_id_list():
                try:
                    related.get(related._meta.primary_key == pk)
                except peewee.DoesNotExist:
                    raise ValidationError('related')
    return related_validator


class ModelValidator(Validator):
    def __init__(self, instance):
        """
        Initialize a validator instance based on a Peewee model instance.

        :param instance: Peewee model instance to use for data lookups.
        :param default: Dictionary of default values to use if no data is passed to validate().
        """
        if not isinstance(instance, peewee.Model):
            msg = 'First argument to {} must be an instance of peewee.Model.'
            raise AttributeError(msg.format(type(self).__name__))

        self.instance = instance
        self.pk_value = self.instance._get_pk_value()
        self.pk_field = self.instance._meta.primary_key

        super().__init__()

    def convert_field(self, name, field):
        """
        Convert a field from a Peewee field to the corresponding validator Field instance.

        :return: Converted field.
        :rtype: peewee_validates.Field
        """
        coerce = DB_FIELD_MAP.get(field.get_db_field(), str)
        required = not bool(getattr(field, 'null', True))
        empty = bool(getattr(field, 'null', True))
        max_length = getattr(field, 'max_length', None)
        default = getattr(field, 'default', None)
        validators = []

        choices = getattr(field, 'choices', ())
        if choices:
            choices = tuple(c[0] for c in choices)

        if getattr(field, 'unique', False):
            unique = validate_unique(self.instance.select(), field, self.pk_field, self.pk_value)
            validators.append(unique)

        if isinstance(field, peewee.ForeignKeyField):
            coerce = None  # 'foreignkey'
            validators.append(validate_related(self.instance, field))

        if isinstance(field, ManyToManyField):
            coerce = None  # 'manytomany'
            validators.append(validate_manytomany(self.instance, field))

        return Field(coerce=coerce, required=required, empty=empty, max_length=max_length,
                     default=default, choices=choices, validators=validators)

    def initialize_fields(self):
        """
        Convert all model fields to validator fields.
        Then call the parent so that overwrites can happen if necessary for manually defined fields.

        :return: None
        """
        # Pull all the "normal" fields off the model instance meta.
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

    def validate(self, data=None, only=None, exclude=None):
        """
        By default, use the value from the model instance and set that value in the data dict.

        :param data: Dictionary of data to validate.
        :param only: List or tuple of fields to validate.
        :param exclude: List or tuple of fields to exclude from validation.
        :return: Tuple of (data, errors).
        """
        data = data or {}
        only = only or self._meta.only
        exclude = exclude or self._meta.exclude

        for name, field in self.instance._meta.fields.items():
            if name in exclude or (only and name not in only):
                continue
            try:
                data.setdefault(name, getattr(self.instance, name, None))
            except (ValueError, peewee.DoesNotExist):
                data.setdefault(name, self.instance._data.get(name, None))

        return super().validate(data=data, only=only, exclude=exclude)

    def clean(self, data):
        """
        Clean the data dictionary and return the cleaned values.
        Turn the output back into the instance and return the instance instead of a dict!
        This is just like the normal clean method except it will also perform index validations
        and save the data to the Peewee instance.

        :param data: Dictionary of data for all fields.
        :return: Instance with updated values.
        :rtype: peewee.Model
        """
        data = super().clean(data)
        self.perform_index_validation(data)
        return self.data

    def perform_index_validation(self, data):
        """
        Validate any unique indexes specified on the model.
        This should happen after all the normal fields have been validated.
        This can add error messages to multiple fields.

        :return: None
        """
        # Build a dict containing query values for each unique index.
        indexdata = []
        for columns, unique in self.instance._meta.indexes:
            if not unique:
                continue
            data = {}
            for col in columns:
                colkey = col[:-3] if col.endswith('_id') else col
                data[colkey] = getattr(self.instance, col, None)
            indexdata.append(data)

        # Then query for each unique index to see if the value is unique.
        for index in indexdata:
            query = self.instance.filter(**index)
            # If we have an ID, need to exclude the current record from the check.
            if self.pk_field and self.pk_value:
                query = query.where(self.pk_field != self.pk_value)
            if query.count():
                for col in index.keys():
                    try:
                        raise ValidationError('index', fields=str.join(', ', index.keys()))
                    except ValidationError as exc:
                        self.add_error(exc, col)

    def save(self, force_insert=False):
        delayed = {}
        for field, value in self.data.items():
            model_field = getattr(type(self.instance), field, None)
            if isinstance(model_field, ManyToManyField):
                delayed[field] = value
                continue
            setattr(self.instance, field, value)

        self.instance.save(force_insert=force_insert)

        for field, value in delayed.items():
            setattr(self.instance, field, value)

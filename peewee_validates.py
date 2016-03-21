import decimal

from dateutil.parser import parse as dateutil_parse
import peewee

__all__ = ['ValidationError', 'Field', 'PeeweeField', 'Validator', 'ModelValidator']

COERCE_MAP = {
    'bool': bool,
    'decimal': decimal.Decimal,
    'float': float,
    'int': int,
    'str': str,
    'date': lambda v: dateutil_parse(v).date(),
    'time': lambda v: dateutil_parse(v).time(),
    'datetime': dateutil_parse,
    'null': lambda v: v,
}


class ValidationError(Exception):
    def __init__(self, key, *args, **kwargs):
        self.key = key
        super().__init__(*args, **kwargs)


class Field:
    def __init__(
            self, coerce,
            required=False, max_length=None, min_length=None, range=None, choices=None):
        """
        Initialize a validation field.

        :param coerce: Method (or name of predefined method) to coerce value.
        :param required: Boolean whether this field is required (default False).
        :param max_length: Maximum length (default None).
        :param min_length: Minimum length (default None).
        :param range: Range of valid values for numbers (default None).
        :param choices: List or tuple of valid choices (default None).
        """
        self.coerce = coerce
        self.required = required
        self.max_length = max_length
        self.min_length = min_length
        self.range = range
        self.choices = choices
        self.value = None

        if callable(self.coerce):
            self.coerce_func = self.coerce
        else:
            self.coerce_func = COERCE_MAP.get(self.coerce, None)

    def get_choices(self):
        """
        Get the choices for this field. If it's a callable, return the result of calling it.

        :return: List of choices for this field.
        :rtype: iterable
        """
        if callable(self.choices):
            return self.choices()
        return self.choices

    def get_value(self, name, data):
        """
        Get the value of this field from the data.
        If there is a problem with the data, raise ValidationError.

        :param name: Name of this field.
        :param data: Dictionary of data for all fields.
        :raises: ValidationError
        :return: The value of this field.
        :rtype: any
        """
        return data.get(name)

    def clean(self, value, data):
        """
        Perform any data cleansing and return the cleaned value of this field.
        If there is a problem with the data, raise ValidationError.

        :param value: The value of this field before cleaning.
        :param data: Dictionary of data for all fields.
        :raises: ValidationError
        :return: The value of this field.
        :rtype: any
        """
        return value

    def validate(self, name, data):
        """
        Validate the data in this field and return the validated, cleaned value.
        If there is a problem with the data, raise ValidationError.

        :param value: The value of this field before cleaning.
        :param data: Dictionary of data for all fields.
        :raises: ValidationError
        :return: The value of this field.
        :rtype: any
        """
        value = self.get_value(name, data)
        # Check to see if the field is present (required).
        if self.required and value is None:
            raise ValidationError('required')

        # Try to coerce the field to the correct type.
        try:
            if self.coerce_func and (self.required or value):
                value = self.coerce_func(value)
        except Exception:
            coerce_name = self.coerce
            if callable(coerce_name):
                coerce_name = coerce_name.__name__
            raise ValidationError('coerce_{}'.format(coerce_name))

        # If we have a max length or min length, enforce it.
        if self.max_length and (not value or len(value) > self.max_length):
            raise ValidationError('max_length')
        if self.min_length and (not value or len(value) < self.min_length):
            raise ValidationError('min_length')

        # If we have a range, enforce it.
        if self.range and (not value or not (self.range[0] < value < self.range[1])):
            raise ValidationError('range')

        # If we have choices, enforce them.
        if self.choices and value not in self.get_choices():
            raise ValidationError('choices')

        self.value = self.clean(value, data)
        return self.value


class PeeweeField(Field):
    """Just like a normal field except it's tied to a Peewee model instance."""

    DB_FIELD_MAP = {
        'int': 'int',
        'bigint': 'int',
        'float': 'float',
        'double': 'float',
        'decimal': 'decimal',
        'datetime': 'datetime',
        'date': 'date',
        'time': 'time',
        'bool': 'bool',
    }

    def __init__(self, instance, field):
        """
        Initialize a field based on a Peewee model's field.

        :param instance: Peewee model instance.
        :param field: Peewee field instance.
        """
        self.instance = instance
        self.field = field
        self.pk_value = self.instance._get_pk_value()
        self.pk_field = self.instance._meta.primary_key

        required = not field.null
        max_length = getattr(field, 'max_length', None)
        coerce = PeeweeField.DB_FIELD_MAP.get(field.get_db_field(), 'str')

        choices = getattr(field, 'choices', ())
        if choices:
            choices = tuple(c[0] for c in choices)

        def model_lookup(value):
            """If it's a model already, convert it to the value of the PK."""
            if isinstance(value, peewee.Model):
                return value._get_pk_value()
            return value

        if isinstance(field, peewee.ForeignKeyField):
            coerce = model_lookup

        super().__init__(coerce, choices=choices, required=required, max_length=max_length)

    def get_value(self, name, data):
        """
        Get the value of this field from the data.
        This tries to first get the value from the dictionary,
        but if it doesn't exist there, get it from the instance.
        If there is a problem with the data, raise ValidationError.

        :param name: Name of this field.
        :param data: Dictionary of data for all fields.
        :raises: ValidationError
        :return: The value of this field.
        :rtype: any
        """
        value = data.get(name)
        if value is None:
            value = getattr(self.instance, name, None)
        return value

    def clean(self, value, data):
        """
        Perform any data cleansing and return the cleaned value of this field.
        If there is a problem with the data, raise ValidationError.
        This method checks for any unique fields and any foreign key references.

        :param value: The value of this field before cleaning.
        :param data: Dictionary of data for all fields.
        :raises: ValidationError
        :return: The value of this field.
        :rtype: any
        """
        value = super().clean(value, data)

        # Validate that the field is unique.
        if getattr(self.field, 'unique', False):
            query = self.instance.select().where(self.field == value)
            # If we have an ID, need to exclude the current record from the check.
            if self.pk_field and self.pk_value:
                query = query.where(self.pk_field != self.pk_value)
            if query.count():
                raise ValidationError('unique')

        # Validate foreign key reference (and return the instance).
        if (value or not self.field.null) and isinstance(self.field, peewee.ForeignKeyField):
            try:
                return self.field.rel_model.get(self.field.to_field == value)
            except self.field.rel_model.DoesNotExist:
                raise ValidationError('related')

        return value


class ValidatorOptions:
    def __init__(self, obj):
        self.fields = {}
        self.only = ()
        self.exclude = ()
        self.default_messages = {
            'required': 'required',
            'max_length': 'too long',
            'min_length': 'too short',
            'choices': 'invalid choice',
            'range': 'invalid range',
            'unique': 'must be unique',
            'index': 'fields must be unique together',
            'related': 'could not find related object',
        }
        for kind in COERCE_MAP:
            self.default_messages['coerce_{}'.format(kind)] = 'must be {}'.format(kind)


class Validator:
    class Meta:
        messages = {}

    def __init__(self, default=None):
        """
        Initialize a validator instance.

        :param default: Dictionary of default values to use if no data is passed to validate().
        """
        self.data = {}
        self.default = default or {}
        self.errors = {}
        self._validated = False

        self._meta = ValidatorOptions(self)
        self._meta.__dict__.update(self.Meta.__dict__)

        self.initialize_fields()

    def initialize_fields(self):
        """
        Add any fields that are specified on this class.

        :return: None
        """
        for key, value in self.__class__.__dict__.items():
            if isinstance(value, Field):
                self._meta.fields[key] = value

    @property
    def valid(self):
        """
        Return bool representing data validity.
        Unvalidated data or invalid data returns False. Validated, valid data returns True.

        :return: Whether the field is valid.
        :rtype: bool
        """
        return self._validated and not self.errors

    def add_error(self, field, key):
        """
        Add an error message for the given field and key.
        Key will use a lookup in the messages dict to figure out which message to add.

        :return: None
        """
        msg = self._meta.messages.get('{}.{}'.format(field, key), self._meta.messages.get(key))
        if not msg:
            msg = self._meta.default_messages.get(key, 'validation failed: {}'.format(key))
        self.errors[field] = msg

    def clean(self):
        """
        Clean the data dictionary and return the cleaned values.

        :return: Dictionary of "clean" values.
        :rtype: dict
        """
        return self.data

    def validate(self, data=None, only=None, exclude=None):
        """
        Validate the data for all fields and return whether the validation was successful.
        This method also retains the data in `self.data` so that it can be accessed later.

        :param data: Dictionary of data to validate.
        :param only: List or tuple of fields to validate.
        :param exclude: List or tuple of fields to exclude from validation.
        :return: True if data is valid, otherwise False.
        """
        self._validated = True

        self.errors = {}
        self.data = self.default.copy()
        self.data.update(data or {})

        # Loop through all fields so we can run validations on them.
        for name, field in self._meta.fields.items():
            # If field is excluded or we have a list to only validate, check it for this field.
            only = only or self._meta.only
            exclude = exclude or self._meta.exclude
            if name in exclude or (only and name not in only):
                continue

            try:
                # Run the field validators and retain the cleaned, validated value.
                self.data[name] = field.validate(name, self.data)
            except ValidationError as exc:
                self.add_error(name, exc.key)
                continue

        # Now try to clean all the fields. This happens after all validations so that
        # each field can act on the cleaned data of other fields if needed.
        if self.valid:
            for name, value in self.data.items():
                try:
                    method = getattr(self, 'clean_{}'.format(name), None)
                    if method:
                        self.data[name] = method(value)
                except ValidationError as exc:
                    self.add_error(name, exc.key)
                    continue

        # Then finally clean all the data (not specific to one field).
        if self.valid:
            try:
                self.data = self.clean()
            except ValidationError as exc:
                self.add_error('__base__', exc.key)

        return self.valid


class ModelValidator(Validator):
    def __init__(self, instance, default=None):
        """
        Initialize a validator instance based on a Peewee model instance.

        :param instance: Peewee model instance to use for data lookups.
        :param default: Dictionary of default values to use if no data is passed to validate().
        """
        self.instance = instance
        self.pk_value = self.instance._get_pk_value()
        self.pk_field = self.instance._meta.primary_key
        super().__init__(default=default)

    def initialize_fields(self):
        """
        Auto create the fields from the instance, then call the super.
        This will use fields from the model instance, then override them with
        any fields specified directly on this class.

        :return: None
        """
        for key, field in self.instance._meta.fields.items():
            if isinstance(field, peewee.PrimaryKeyField):
                continue
            self._meta.fields[key] = PeeweeField(self.instance, field)
        super().initialize_fields()

    def clean(self):
        """
        Clean the data dictionary and return the cleaned values.
        This is just like the normal clean method except it will also perform index validations
        and save the data to the Peewee instance.

        :return: Dictionary of "clean" values.
        :rtype: dict
        """
        for key, value in self.data.items():
            setattr(self.instance, key, value)
        data = super().clean()
        self.perform_index_validation()
        return data

    def perform_index_validation(self):
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
                    self.add_error(col, 'index')

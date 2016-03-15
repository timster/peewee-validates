import datetime

import peewee

COERCED_FIELDS = (
    'int', 'bigint', 'float', 'double', 'decimal', 'string', 'text',
    'blob', 'uuid', 'datetime', 'date', 'time', 'bool'
)


class ValidationError(Exception):
    def __init__(self, key, *args, **kwargs):
        self.key = key
        super().__init__(*args, **kwargs)


class ValidatorOptions:
    def __init__(self, obj):
        self.model = None
        self.fields = {}
        self.only = ()
        self.exclude = ()
        self.default_messages = {
            'required': 'field is required',
            'max_length': 'value is too long',
            'unique': 'value must be unique',
            'choices': 'value must be valid choice',
            'related': 'could not find related value',
        }
        for kind in COERCED_FIELDS:
            self.default_messages['coerce_{}'.format(kind)] = 'value must be {}'.format(kind)


class ModelValidator:

    def __init__(self, instance=None):
        self.instance = instance
        self.errors = {}
        self.data = {}
        self._valid = False

        # Set meta options. Maybe a better way to do this, but it works.
        self._meta = ValidatorOptions(self)
        self._meta.__dict__.update(self.Meta.__dict__)

        # Default to using fields from the model.
        # But this can be overwritten by simply adding a field to this class!
        self._meta.fields = {}
        if self._meta.model:
            self._meta.fields = self._meta.model._meta.fields
        if self.instance:
            self._meta.fields = self.instance._meta.fields
        for key, value in self.__class__.__dict__.items():
            if isinstance(value, peewee.Field):
                self._meta.fields[key] = value

        # If we don't have an instance, create a default one based on the model.
        if not self.instance and self._meta.model:
            self.instance = self._meta.model()

    class Meta:
        messages = {}

    @property
    def valid(self):
        """
        Return bool representing data validity.
        Unvalidated data or invalid data returns False. Validated, valid data returns True.
        """
        return self._valid

    def add_error(self, field, key):
        """
        Add an error message for the given field and key.
        Key will use a lookup in the messages dict to figure out which message to add.
        """
        # Try custom messages dictionary, default dictionary, then a generic default message.
        msg = self._meta.messages.get('{}.{}'.format(field, key), self._meta.messages.get(key))
        if not msg:
            msg = self._meta.default_messages.get(key, 'validation failed: {}'.format(key))
        self.errors[field] = msg

    def perform_field_validation(self, name, field, value):
        """
        Perform validation for a single field value.
        If validation is successful, return the field value.
        If validation fails, raise ValidationError with an error message key.
        """
        # Validate required field.
        if not getattr(field, 'null', True):
            if not value and not field.default:
                raise ValidationError('required')

        # Validate type coersion.
        try:
            value = field.python_value(value)
        except:
            raise ValidationError('coerce_{}'.format(field.get_db_field()))

        # If it's a temporal field and the value is not a valid date or time,
        # it has failed coersion. Coersion does not raise an exception for these field types.
        if isinstance(field, (peewee.DateTimeField, peewee.DateField, peewee.TimeField)):
            if not isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
                raise ValidationError('coerce_{}'.format(field.get_db_field()))

        # Validate unique constraint.
        if getattr(field, 'unique', False) and self.instance:
            query = self.instance.select().where(field == value)
            # If we have an ID, need to exclude the current record from the check.
            pk_value = self.instance._get_pk_value()
            pk_field = self.instance._meta.primary_key
            if pk_field and pk_value:
                query = query.where(pk_field != pk_value)
            if query.count():
                raise ValidationError('unique')

        # Validate foreign key reference (and return the instance).
        if isinstance(field, peewee.ForeignKeyField):
            try:
                return field.rel_model.get(field.to_field == value)
            except field.rel_model.DoesNotExist:
                raise ValidationError('related')

        # Validate choice constraint.
        field_choices = getattr(field, 'choices', False)
        if field_choices:
            if value not in list(c[0] for c in field_choices):
                raise ValidationError('choices')

        # Validate max length.
        field_max_length = getattr(field, 'max_length', False)
        if field_max_length:
            if len(value) > field_max_length:
                raise ValidationError('max_length')

        return value

    def get_data(self, name, data):
        """
        Get data for field name from the given data dictionary.
        Calls an optional "get_<name>_data" method for custom data retrieval.
        """
        method = getattr(self, 'get_{}_data'.format(name), None)
        if method:
            return method(name, data)
        return data.get(name)

    def validate(self, data, only=None, exclude=None):
        """
        Validate all fields and return a bool indicating validation success.
        Call teh default validators for each field, then call any custom validator hooks
        for each field.
        """
        for name, field in self._meta.fields.items():
            # If field is excluded or we have a list to only valudate, check it for this field.
            only = only or self._meta.only
            exclude = exclude or self._meta.exclude
            if name in exclude or (only and name not in only):
                continue

            # Do not validate default primary keys!
            if isinstance(field, peewee.PrimaryKeyField):
                continue

            try:
                # Get value from the input data.
                value = self.get_data(name, data) or getattr(self.instance, name, '')
                # Run it through validation methods.
                value = self.perform_field_validation(name, field, value)
                # Run it through validation hook.
                method = getattr(self, 'validate_{}'.format(name), None)
                if method:
                    value = method(name, field, value)
            except ValidationError as exc:
                # Add the error for this field and continue to the next field.
                self.add_error(name, exc.key)
                continue

            # Data is valid for this field, retain the value here and in the model.
            self.data[name] = value
            if self.instance:
                setattr(self.instance, name, value)

        self._valid = (not len(self.errors))
        return self.valid

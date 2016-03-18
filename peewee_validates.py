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
            'required': 'is required',
            'max_length': 'is too long',
            'unique': 'must be unique',
            'choices': 'must be valid choice',
            'related': 'could not find related value',
            'index': 'fields must be unique together',
        }
        for kind in COERCED_FIELDS:
            self.default_messages['coerce_{}'.format(kind)] = 'value must be {}'.format(kind)


class ModelValidator:

    def __init__(self, instance=None):
        self.instance = instance
        self.errors = {}
        self._valid = False

        self.pk_value = self.instance._get_pk_value()
        self.pk_field = self.instance._meta.primary_key

        # Set meta options. Maybe a better way to do this, but it works.
        self._meta = ValidatorOptions(self)
        self._meta.__dict__.update(self.Meta.__dict__)

        # Check to make sure we have something to work with.
        if not self.instance and not self._meta.model:
            raise AttributeError('Must specify either an instance or Meta.model.')

        # If we don't have an instance, create a default one based on the model.
        if not self.instance:
            self.instance = self._meta.model()

        # Default to using fields from the model.
        # But this can be overwritten by simply adding a field to this class!
        self._meta.fields = {}
        self._meta.fields = self.instance._meta.fields
        for key, value in self.__class__.__dict__.items():
            if isinstance(value, peewee.Field):
                self._meta.fields[key] = value

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
            if self.pk_field and self.pk_value:
                query = query.where(self.pk_field != self.pk_value)
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

    def perform_index_validation(self):
        """
        Validate any unique indexes specified on the model.
        This should happen after all the normal fields have been validated.
        This can add error messages to multiple fields.
        """
        indexdata = []
        for columns, unique in self.instance._meta.indexes:
            if not unique:
                continue
            data = {}
            for col in columns:
                colkey = col[:-3] if col.endswith('_id') else col
                data[colkey] = getattr(self.instance, col, None)
                indexdata.append(data)

        for index in indexdata:
            query = self.instance.filter(**index)
            # If we have an ID, need to exclude the current record from the check.
            if self.pk_field and self.pk_value:
                query = query.where(self.pk_field != self.pk_value)
            if query.count():
                for col in index.keys():
                    self.add_error(col, 'index')

    def validate(self, data=None, only=None, exclude=None):
        """
        Validate all fields and return a bool indicating validation success.
        Call teh default validators for each field, then call any custom validator hooks
        for each field.
        """
        if not data:
            data = {}

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
                try:
                    # Get value from the input data.
                    # If there's no value in the input data, try and get it from the instance.
                    # This could raise an exception if it's a foreign key.
                    value = self.get_data(name, data)
                    if value is None:
                        value = getattr(self.instance, name, '')
                except peewee.DoesNotExist:
                    value = ''
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

            # Data is valid for this field, retain the value in the model.
            setattr(self.instance, name, value)

        self.perform_index_validation()

        self._valid = (not len(self.errors))
        return self.valid

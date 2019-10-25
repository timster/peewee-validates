from datetime import date
from datetime import datetime
from datetime import time

from peewee_validates import DEFAULT_MESSAGES
from peewee_validates import Field
from peewee_validates import Validator
from peewee_validates import ValidationError
from peewee_validates import StringField
from peewee_validates import FloatField
from peewee_validates import IntegerField
from peewee_validates import validate_length
from peewee_validates import DecimalField
from peewee_validates import DateField
from peewee_validates import TimeField
from peewee_validates import DateTimeField
from peewee_validates import BooleanField
from peewee_validates import validate_not_empty
from peewee_validates import validate_one_of
from peewee_validates import validate_none_of
from peewee_validates import validate_equal
from peewee_validates import validate_regexp
from peewee_validates import validate_email
from peewee_validates import validate_function


def test_raw_field():
    class TestValidator(Validator):
        field1 = Field()

    validator = TestValidator()
    valid = validator.validate({'field1': 'thing'})
    assert valid
    assert validator.data['field1'] == 'thing'


def test_required():
    class TestValidator(Validator):
        bool_field = BooleanField(required=True)
        decimal_field = DecimalField(required=True)
        float_field = FloatField(required=True, low=10.0, high=50.0)
        int_field = IntegerField(required=True)
        str_field = StringField(required=True)
        date_field = DateField(required=True, low='jan 1, 2010', high='dec 1, 2010')
        time_field = TimeField(required=True, low='9 am', high='10 am')
        datetime_field = DateTimeField(required=True, low='jan 1, 2010', high='dec 1, 2010')

    validator = TestValidator()
    valid = validator.validate()
    assert not valid
    assert validator.errors['bool_field'] == DEFAULT_MESSAGES['required']
    assert validator.errors['decimal_field'] == DEFAULT_MESSAGES['required']
    assert validator.errors['float_field'] == DEFAULT_MESSAGES['required']
    assert validator.errors['int_field'] == DEFAULT_MESSAGES['required']
    assert validator.errors['str_field'] == DEFAULT_MESSAGES['required']
    assert validator.errors['date_field'] == DEFAULT_MESSAGES['required']
    assert validator.errors['time_field'] == DEFAULT_MESSAGES['required']
    assert validator.errors['datetime_field'] == DEFAULT_MESSAGES['required']


def test_integerfield():
    class TestValidator(Validator):
        int_field = IntegerField(required=True)

    data = {'int_field': 0}
    validator = TestValidator()
    valid = validator.validate(data)
    assert valid


def test_coerce_fails():
    class TestValidator(Validator):
        float_field = FloatField()
        int_field = IntegerField(required=True)
        decimal_field = DecimalField(required=True)
        boolean_field = BooleanField()

    validator = TestValidator()
    data = {'int_field': 'a', 'float_field': 'a', 'decimal_field': 'a', 'boolean_field': 'false'}
    valid = validator.validate(data)
    assert not valid
    assert validator.errors['decimal_field'] == DEFAULT_MESSAGES['coerce_decimal']
    assert validator.errors['float_field'] == DEFAULT_MESSAGES['coerce_float']
    assert validator.errors['int_field'] == DEFAULT_MESSAGES['coerce_int']


def test_decimal():
    class TestValidator(Validator):
        low_field = DecimalField(low=-42.0)
        high_field = DecimalField(high=42.0)
        low_high_field = DecimalField(low=-42.0, high=42.0)

    validator = TestValidator()
    data = {'low_field': '-99.99', 'high_field': '99.99', 'low_high_field': '99.99'}
    valid = validator.validate(data)
    assert not valid
    assert validator.errors['low_field'] == 'Must be at least -42.0.'
    assert validator.errors['high_field'] == 'Must be between None and 42.0.'
    assert validator.errors['low_high_field'] == 'Must be between -42.0 and 42.0.'


def test_required_empty():
    class TestValidator(Validator):
        field1 = StringField(required=False, validators=[validate_not_empty()])

    validator = TestValidator()

    valid = validator.validate()
    assert valid

    valid = validator.validate({'field1': ''})
    assert not valid
    assert validator.errors['field1'] == DEFAULT_MESSAGES['empty']


def test_dates_empty():
    class TestValidator(Validator):
        date_field = DateField()
        time_field = TimeField()
        datetime_field = DateTimeField()

    data = {
        'date_field': '',
        'time_field': '',
        'datetime_field': '',
    }

    validator = TestValidator()
    valid = validator.validate(data)

    print(validator.errors)
    assert valid
    assert not validator.data['datetime_field']
    assert not validator.data['date_field']
    assert not validator.data['time_field']


def test_dates_coersions():
    class TestValidator(Validator):
        date_field = DateField(required=True)
        time_field = TimeField(required=True)
        datetime_field = DateTimeField(required=True)

    data = {
        'date_field': 'jan 1, 2015',
        'time_field': 'jan 1, 2015 3:20 pm',
        'datetime_field': 'jan 1, 2015 3:20 pm',
    }

    validator = TestValidator()
    valid = validator.validate(data)

    assert valid
    assert validator.data['datetime_field'] == datetime(2015, 1, 1, 15, 20)
    assert validator.data['date_field'] == date(2015, 1, 1)
    assert validator.data['time_field'] == time(15, 20)


def test_dates_native():
    class TestValidator(Validator):
        date_field = DateField(required=True)
        time_field = TimeField(required=True)
        datetime_field = DateTimeField(required=True)

    data = {
        'date_field': date(2015, 1, 1),
        'time_field': time(15, 20),
        'datetime_field': datetime(2015, 1, 1, 15, 20),
    }

    validator = TestValidator()
    valid = validator.validate(data)

    assert valid
    assert validator.data['datetime_field'] == datetime(2015, 1, 1, 15, 20)
    assert validator.data['date_field'] == date(2015, 1, 1)
    assert validator.data['time_field'] == time(15, 20)


def test_date_coerce_fail():
    class TestValidator(Validator):
        date_field = DateField(required=True)
        time_field = TimeField(required=True)
        datetime_field = DateTimeField(required=True)

    data = {
        'date_field': 'failure',
        'time_field': 'failure',
        'datetime_field': 'failure',
    }

    validator = TestValidator()
    valid = validator.validate(data)

    assert not valid
    assert validator.errors['datetime_field'] == DEFAULT_MESSAGES['coerce_datetime']
    assert validator.errors['date_field'] == DEFAULT_MESSAGES['coerce_date']
    assert validator.errors['time_field'] == DEFAULT_MESSAGES['coerce_time']


def test_default():
    class TestValidator(Validator):
        str_field = StringField(required=True, default='timster')

    validator = TestValidator()
    valid = validator.validate()
    assert valid
    assert validator.data['str_field'] == 'timster'


def test_callable_default():
    def getname():
        return 'timster'

    class TestValidator(Validator):
        str_field = StringField(required=True, default=getname)

    validator = TestValidator()
    valid = validator.validate()
    assert valid
    assert validator.data['str_field'] == 'timster'


def test_lengths():
    class TestValidator(Validator):
        max_field = StringField(max_length=5)
        min_field = StringField(min_length=5)
        len_field = StringField(validators=[validate_length(equal=10)])

    validator = TestValidator()
    valid = validator.validate({'min_field': 'shrt', 'max_field': 'toolong', 'len_field': '3'})
    assert not valid
    assert validator.errors['min_field'] == DEFAULT_MESSAGES['length_low'].format(low=5)
    assert validator.errors['max_field'] == DEFAULT_MESSAGES['length_high'].format(high=5)
    assert validator.errors['len_field'] == DEFAULT_MESSAGES['length_equal'].format(equal=10)


def test_range():
    class TestValidator(Validator):
        range1 = IntegerField(low=1, high=5)
        range2 = IntegerField(low=1, high=5)

    validator = TestValidator()
    valid = validator.validate({'range1': '44', 'range2': '3'})
    assert not valid
    assert validator.errors['range1'] == DEFAULT_MESSAGES['range_between'].format(low=1, high=5)
    assert 'range2' not in validator.errors


def test_coerce_error():
    class TestValidator(Validator):
        date_field = DateField()

    validator = TestValidator()
    valid = validator.validate({'date_field': 'not a real date'})
    assert not valid
    assert validator.errors['date_field'] == DEFAULT_MESSAGES['coerce_date']


def test_choices():
    class TestValidator(Validator):
        first_name = StringField(validators=[validate_one_of(('tim', 'bob'))])

    validator = TestValidator()
    valid = validator.validate()
    assert valid

    validator = TestValidator()
    valid = validator.validate({'first_name': 'tim'})
    assert valid

    validator = TestValidator()
    valid = validator.validate({'first_name': 'asdf'})
    assert not valid
    assert validator.errors['first_name'] == DEFAULT_MESSAGES['one_of'].format(choices='tim, bob')


def test_choices_integers():
    class TestValidator(Validator):
        int_field = IntegerField(validators=[validate_one_of((1, 2, 3))])

    validator = TestValidator()
    valid = validator.validate({'int_field': 4})
    assert not valid


def test_exclude():
    class TestValidator(Validator):
        first_name = StringField(validators=[validate_none_of(('tim', 'bob'))])

    validator = TestValidator()
    valid = validator.validate({'first_name': 'tim'})
    assert not valid
    assert validator.errors['first_name'] == DEFAULT_MESSAGES['none_of'].format(choices='tim, bob')

    validator = TestValidator()
    valid = validator.validate({'first_name': 'asdf'})
    assert valid


def test_callable_choices():
    def getchoices():
        return ('tim', 'bob')

    class TestValidator(Validator):
        first_name = StringField(validators=[validate_one_of(getchoices)])

    validator = TestValidator()
    valid = validator.validate({'first_name': 'asdf'})
    assert not valid
    assert validator.errors['first_name'] == DEFAULT_MESSAGES['one_of'].format(choices='tim, bob')

    validator = TestValidator()
    valid = validator.validate({'first_name': 'tim'})
    assert valid


def test_callable_exclude():
    def getchoices():
        return ('tim', 'bob')

    class TestValidator(Validator):
        first_name = StringField(validators=[validate_none_of(getchoices)])

    validator = TestValidator()
    valid = validator.validate({'first_name': 'tim'})
    assert not valid
    assert validator.errors['first_name'] == DEFAULT_MESSAGES['none_of'].format(choices='tim, bob')

    validator = TestValidator()
    valid = validator.validate({'first_name': 'asdf'})
    assert valid


def test_equal():
    class TestValidator(Validator):
        first_name = StringField(validators=[validate_equal('tim')])

    validator = TestValidator()
    valid = validator.validate({'first_name': 'tim'})
    assert valid

    validator = TestValidator()
    valid = validator.validate({'first_name': 'asdf'})
    assert not valid
    assert validator.errors['first_name'] == DEFAULT_MESSAGES['equal'].format(other='tim')


def test_regexp():
    class TestValidator(Validator):
        first_name = StringField(validators=[validate_regexp('^[i-t]+$')])

    validator = TestValidator()
    valid = validator.validate({'first_name': 'tim'})
    assert valid

    validator = TestValidator()
    valid = validator.validate({'first_name': 'asdf'})
    assert not valid
    assert validator.errors['first_name'] == DEFAULT_MESSAGES['regexp'].format(pattern='^[i-t]+$')


def test_email():
    class TestValidator(Validator):
        email = StringField(validators=[validate_email()])

    validator = TestValidator()
    valid = validator.validate({'email': 'bad-domain@asdfasdf'})
    assert not valid
    assert validator.errors['email'] == DEFAULT_MESSAGES['email']


def test_function():
    def alwaystim(value):
        if value == 'tim':
            return True

    class TestValidator(Validator):
        first_name = StringField(validators=[validate_function(alwaystim)])

        class Meta:
            messages = {
                'function': 'your name must be tim'
            }

    validator = TestValidator()
    valid = validator.validate({'first_name': 'tim'})
    assert valid

    validator = TestValidator()
    valid = validator.validate({'first_name': 'asdf'})
    assert not valid
    assert validator.errors['first_name'] == validator._meta.messages['function']


def test_only_exclude():
    class TestValidator(Validator):
        field1 = StringField(required=True)
        field2 = StringField(required=True)

    validator = TestValidator()
    valid = validator.validate({'field1': 'shrt'}, only=['field1'])
    assert valid

    valid = validator.validate({'field1': 'shrt'}, exclude=['field2'])
    assert valid


def test_clean_field():
    class TestValidator(Validator):
        field1 = StringField(required=True)

        def clean_field1(self, value):
            return value + '-awesome'

    validator = TestValidator()
    valid = validator.validate({'field1': 'tim'})
    assert valid
    assert validator.data['field1'] == 'tim-awesome'


def test_clean_field_error():
    class TestValidator(Validator):
        field1 = StringField(required=True)

        def clean_field1(self, value):
            raise ValidationError('required')

    validator = TestValidator()
    valid = validator.validate({'field1': 'tim'})
    assert not valid
    assert validator.data['field1'] == 'tim'
    assert validator.errors['field1'] == DEFAULT_MESSAGES['required']


def test_clean():
    class TestValidator(Validator):
        field1 = StringField(required=True)

        def clean(self, data):
            data['field1'] += 'awesome'
            return data

    validator = TestValidator()
    valid = validator.validate({'field1': 'tim'})
    assert valid
    assert validator.data['field1'] == 'timawesome'


def test_clean_error():
    class TestValidator(Validator):
        field1 = StringField(required=True)

        def clean(self, data):
            raise ValidationError('required')

    validator = TestValidator()
    valid = validator.validate({'field1': 'tim'})
    assert not valid
    assert validator.data['field1'] == 'tim'
    assert validator.errors['__base__'] == DEFAULT_MESSAGES['required']


def test_custom_messages():
    class TestValidator(Validator):
        field1 = StringField(required=True)
        field2 = StringField(required=True)
        field3 = IntegerField(required=True)

        class Meta:
            messages = {
                'required': 'enter value',
                'field2.required': 'field2 required',
                'field3.coerce_int': 'pick a number',
            }

    validator = TestValidator()
    valid = validator.validate({'field3': 'asdfasdf'})
    assert not valid
    assert validator.errors['field1'] == 'enter value'
    assert validator.errors['field2'] == 'field2 required'
    assert validator.errors['field3'] == 'pick a number'


def test_subclass():
    class ParentValidator(Validator):
        field1 = StringField(required=True)
        field2 = StringField(required=False)

    class TestValidator(ParentValidator):
        field2 = StringField(required=True)
        field3 = StringField(required=True)

    validator = TestValidator()
    valid = validator.validate({})
    assert not valid
    assert validator.errors['field1'] == DEFAULT_MESSAGES['required']
    assert validator.errors['field2'] == DEFAULT_MESSAGES['required']
    assert validator.errors['field3'] == DEFAULT_MESSAGES['required']

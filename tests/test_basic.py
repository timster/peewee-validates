from datetime import date
from datetime import datetime
from datetime import time

from peewee_validates import Field
from peewee_validates import validate_equal
from peewee_validates import validate_exclude
from peewee_validates import validate_function
from peewee_validates import validate_length
from peewee_validates import validate_regexp
from peewee_validates import ValidationError
from peewee_validates import Validator


def test_required():
    class TestValidator(Validator):
        bool_field = Field(bool, required=True)
        decimal_field = Field('decimal', required=True)
        float_field = Field(float, required=True)
        int_field = Field(int, required=True)
        str_field = Field(str, required=True)
        date_field = Field('date', required=True)
        time_field = Field('time', required=True)
        datetime_field = Field('datetime', required=True)

    validator = TestValidator()
    valid = validator.validate()
    assert not valid
    assert validator.errors['bool_field'] == 'required field'
    assert validator.errors['decimal_field'] == 'required field'
    assert validator.errors['float_field'] == 'required field'
    assert validator.errors['int_field'] == 'required field'
    assert validator.errors['str_field'] == 'required field'
    assert validator.errors['date_field'] == 'required field'
    assert validator.errors['time_field'] == 'required field'
    assert validator.errors['datetime_field'] == 'required field'


def test_data_coersions():
    class TestValidator(Validator):
        date_field = Field('date', required=True)
        time_field = Field('time', required=True)
        datetime_field = Field('datetime', required=True)

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


def test_callable_default():
    def getname():
        return 'timster'

    class TestValidator(Validator):
        str_field = Field(str, required=True, default=getname)

    validator = TestValidator()
    valid = validator.validate()
    assert valid
    assert validator.data['str_field'] == 'timster'


def test_lengths():
    class TestValidator(Validator):
        max_field = Field(str, max_length=5)
        min_field = Field(str, min_length=5)
        len_field = Field(str, validators=[validate_length(10)])

    validator = TestValidator()
    valid = validator.validate({'min_field': 'shrt', 'max_field': 'toolong', 'len_field': '3'})
    assert not valid
    assert validator.errors['min_field'] == 'must be at least 5 characters'
    assert validator.errors['max_field'] == 'must be at most 5 characters'
    assert validator.errors['len_field'] == 'must be exactly 10 characters'


def test_range():
    class TestValidator(Validator):
        range1 = Field(int, range=(1, 5))
        range2 = Field(int, range=(1, 5))

    validator = TestValidator()
    valid = validator.validate({'range1': '44', 'range2': '3'})
    assert not valid
    assert validator.errors['range1'] == 'must be in the range 1 to 5'
    assert 'range2' not in validator.errors


def test_coerce_error():
    class TestValidator(Validator):
        date_field = Field('date')

    validator = TestValidator()
    valid = validator.validate({'date_field': 'another'})
    assert not valid
    assert validator.errors['date_field'] == 'must be a valid date'


def test_callable_coerse():
    def alwaystim(value):
        return 'tim'

    class TestValidator(Validator):
        first_name = Field(alwaystim, choices=('tim', 'bob'))

    validator = TestValidator()
    valid = validator.validate({'first_name': 'another'})
    assert valid


def test_callable_coerce_error():
    def mydate(value):
        raise ValueError

    class TestValidator(Validator):
        date_field = Field(mydate)

    validator = TestValidator()
    valid = validator.validate({'date_field': 'another'})
    assert not valid
    assert validator.errors['date_field'] == 'invalid: coerce_mydate'


def test_choices():
    class TestValidator(Validator):
        first_name = Field(str, choices=('tim', 'bob'))

    validator = TestValidator()
    valid = validator.validate()
    assert not valid
    assert validator.errors['first_name'] == 'must be one of the choices: tim, bob'

    validator = TestValidator()
    valid = validator.validate({'first_name': 'tim'})
    assert valid


def test_exclude():
    class TestValidator(Validator):
        first_name = Field(str, validators=[validate_exclude(('tim', 'bob'))])

    validator = TestValidator()
    valid = validator.validate({'first_name': 'tim'})
    assert not valid
    assert validator.errors['first_name'] == 'must not be one of the choices: tim, bob'

    validator = TestValidator()
    valid = validator.validate({'first_name': 'asdf'})
    assert valid


def test_callable_choices():
    def getchoices():
        return ('tim', 'bob')

    class TestValidator(Validator):
        first_name = Field(str, choices=getchoices)

    validator = TestValidator()
    valid = validator.validate()
    assert not valid
    assert validator.errors['first_name'] == 'must be one of the choices: tim, bob'

    validator = TestValidator()
    valid = validator.validate({'first_name': 'tim'})
    assert valid


def test_callable_exclude():
    def getchoices():
        return ('tim', 'bob')

    class TestValidator(Validator):
        first_name = Field(str, validators=[validate_exclude(getchoices)])

    validator = TestValidator()
    valid = validator.validate({'first_name': 'tim'})
    assert not valid
    assert validator.errors['first_name'] == 'must not be one of the choices: tim, bob'

    validator = TestValidator()
    valid = validator.validate({'first_name': 'asdf'})
    assert valid


def test_equal():
    class TestValidator(Validator):
        first_name = Field(str, validators=[validate_equal('tim')])

    validator = TestValidator()
    valid = validator.validate({'first_name': 'tim'})
    assert valid

    validator = TestValidator()
    valid = validator.validate({'first_name': 'asdf'})
    assert not valid
    assert validator.errors['first_name'] == 'must be equal to tim'


def test_regexp():
    class TestValidator(Validator):
        first_name = Field(str, validators=[validate_regexp('^[i-t]+$')])

    validator = TestValidator()
    valid = validator.validate({'first_name': 'tim'})
    assert valid

    validator = TestValidator()
    valid = validator.validate({'first_name': 'asdf'})
    assert not valid
    assert validator.errors['first_name'] == 'must match the pattern ^[i-t]+$'


def test_function():
    def alwaystim(value):
        if value == 'tim':
            return True

    class TestValidator(Validator):
        first_name = Field(str, validators=[validate_function(alwaystim)])

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
    assert validator.errors['first_name'] == 'your name must be tim'


def test_only_exclude():
    class TestValidator(Validator):
        field1 = Field(str, required=True)
        field2 = Field(str, required=True)

    validator = TestValidator()
    valid = validator.validate({'field1': 'shrt'}, only=['field1'])
    assert valid

    valid = validator.validate({'field1': 'shrt'}, exclude=['field2'])
    assert valid


def test_clean_field():
    class TestValidator(Validator):
        field1 = Field(str, required=True)

        def clean_field1(self, value):
            return value + 'awesome'

    validator = TestValidator()
    valid = validator.validate({'field1': 'tim'})
    assert valid
    assert validator.data['field1'] == 'timawesome'


def test_clean_field_error():
    class TestValidator(Validator):
        field1 = Field(str, required=True)

        def clean_field1(self, value):
            raise ValidationError('required')

    validator = TestValidator()
    valid = validator.validate({'field1': 'tim'})
    assert not valid
    assert validator.data['field1'] == 'tim'
    assert validator.errors['field1'] == 'required field'


def test_clean():
    class TestValidator(Validator):
        field1 = Field(str, required=True)

        def clean(self, data):
            data['field1'] += 'awesome'
            return data

    validator = TestValidator()
    valid = validator.validate({'field1': 'tim'})
    assert valid
    assert validator.data['field1'] == 'timawesome'


def test_clean_error():
    class TestValidator(Validator):
        field1 = Field(str, required=True)

        def clean(self, data):
            raise ValidationError('required')

    validator = TestValidator()
    valid = validator.validate({'field1': 'tim'})
    assert not valid
    assert validator.data['field1'] == 'tim'
    assert validator.errors['__base__'] == 'required field'


def test_custom_messages():
    class TestValidator(Validator):
        field1 = Field(str, required=True)
        field2 = Field(str, required=True)
        field3 = Field(int, required=True, max_length=4)

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

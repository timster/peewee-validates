from datetime import date
from datetime import datetime
from datetime import time

from peewee_validates import Validator
from peewee_validates import ValidationError
from peewee_validates import Field
from peewee_validates import validates


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
    rv = validator.validate()
    assert rv.errors['bool_field'] == 'required field'
    assert rv.errors['decimal_field'] == 'required field'
    assert rv.errors['float_field'] == 'required field'
    assert rv.errors['int_field'] == 'required field'
    assert rv.errors['str_field'] == 'required field'
    assert rv.errors['date_field'] == 'required field'
    assert rv.errors['time_field'] == 'required field'
    assert rv.errors['datetime_field'] == 'required field'


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
    rv = validator.validate(data)

    assert rv.data['datetime_field'] == datetime(2015, 1, 1, 15, 20)
    assert rv.data['date_field'] == date(2015, 1, 1)
    assert rv.data['time_field'] == time(15, 20)


def test_callable_default():
    def getname():
        return 'timster'

    class TestValidator(Validator):
        str_field = Field(str, required=True, default=getname)

    validator = TestValidator()
    rv = validator.validate()
    assert not rv.errors
    assert rv.data['str_field'] == 'timster'


def test_lengths():
    class TestValidator(Validator):
        max_field = Field(str, max_length=5)
        min_field = Field(str, min_length=5)
        len_field = Field(str, validators=[validates.length(10)])

    validator = TestValidator()
    rv = validator.validate({'min_field': 'shrt', 'max_field': 'toolong', 'len_field': '3'})
    assert rv.errors['min_field'] == 'must be at least 5 characters'
    assert rv.errors['max_field'] == 'must be less than 5 characters'
    assert rv.errors['len_field'] == 'must be exactly 10 characters'


def test_range():
    class TestValidator(Validator):
        range1 = Field(int, range=(1, 5))
        range2 = Field(int, range=(1, 5))

    validator = TestValidator()
    rv = validator.validate({'range1': '44', 'range2': '3'})
    assert rv.errors['range1'] == 'must be in the range 1 to 5'
    assert 'range2' not in rv.errors


def test_coerce_error():
    class TestValidator(Validator):
        date_field = Field('date')

    validator = TestValidator()
    rv = validator.validate({'date_field': 'another'})
    assert rv.errors['date_field'] == 'must be a valid date'


def test_callable_coerse():
    def alwaystim(value):
        return 'tim'

    class TestValidator(Validator):
        first_name = Field(alwaystim, choices=('tim', 'bob'))

    validator = TestValidator()
    rv = validator.validate({'first_name': 'another'})
    assert not rv.errors


def test_callable_coerce_error():
    def mydate(value):
        raise ValueError

    class TestValidator(Validator):
        date_field = Field(mydate)

    validator = TestValidator()
    rv = validator.validate({'date_field': 'another'})
    assert rv.errors['date_field'] == 'invalid: coerce_mydate'


def test_choices():
    class TestValidator(Validator):
        first_name = Field(str, choices=('tim', 'bob'))

    validator = TestValidator()
    rv = validator.validate()
    assert rv.errors['first_name'] == 'must be one of the choices: tim, bob'

    validator = TestValidator()
    rv = validator.validate({'first_name': 'tim'})
    assert not rv.errors


def test_exclude():
    class TestValidator(Validator):
        first_name = Field(str, validators=[validates.exclude(('tim', 'bob'))])

    validator = TestValidator()
    rv = validator.validate({'first_name': 'tim'})
    assert rv.errors['first_name'] == 'must not be one of the choices: tim, bob'

    validator = TestValidator()
    rv = validator.validate({'first_name': 'asdf'})
    assert not rv.errors


def test_callable_choices():
    def getchoices():
        return ('tim', 'bob')

    class TestValidator(Validator):
        first_name = Field(str, choices=getchoices)

    validator = TestValidator()
    rv = validator.validate()
    assert rv.errors['first_name'] == 'must be one of the choices: tim, bob'

    validator = TestValidator()
    rv = validator.validate({'first_name': 'tim'})
    assert not rv.errors


def test_callable_exclude():
    def getchoices():
        return ('tim', 'bob')

    class TestValidator(Validator):
        first_name = Field(str, validators=[validates.exclude(getchoices)])

    validator = TestValidator()
    rv = validator.validate({'first_name': 'tim'})
    assert rv.errors['first_name'] == 'must not be one of the choices: tim, bob'

    validator = TestValidator()
    rv = validator.validate({'first_name': 'asdf'})
    assert not rv.errors


def test_equal():
    class TestValidator(Validator):
        first_name = Field(str, validators=[validates.equal('tim')])

    validator = TestValidator()
    rv = validator.validate({'first_name': 'tim'})
    assert not rv.errors

    validator = TestValidator()
    rv = validator.validate({'first_name': 'asdf'})
    assert rv.errors['first_name'] == 'must be equal to tim'


def test_regexp():
    class TestValidator(Validator):
        first_name = Field(str, validators=[validates.regexp('^[i-t]+$')])

    validator = TestValidator()
    rv = validator.validate({'first_name': 'tim'})
    assert not rv.errors

    validator = TestValidator()
    rv = validator.validate({'first_name': 'asdf'})
    assert rv.errors['first_name'] == 'must match the pattern ^[i-t]+$'


def test_function():
    def alwaystim(value):
        if value == 'tim':
            return True

    class TestValidator(Validator):
        first_name = Field(str, validators=[validates.function(alwaystim)])

        class Meta:
            messages = {
                'function': 'your name must be tim'
            }

    validator = TestValidator()
    rv = validator.validate({'first_name': 'tim'})
    assert not rv.errors

    validator = TestValidator()
    rv = validator.validate({'first_name': 'asdf'})
    assert rv.errors['first_name'] == 'your name must be tim'


def test_only_exclude():
    class TestValidator(Validator):
        field1 = Field(str, required=True)
        field2 = Field(str, required=True)

    validator = TestValidator()
    rv = validator.validate({'field1': 'shrt'}, only=['field1'])
    assert not rv.errors

    rv = validator.validate({'field1': 'shrt'}, exclude=['field2'])
    assert not rv.errors


def test_clean_field():
    class TestValidator(Validator):
        field1 = Field(str, required=True)

        def clean_field1(self, value):
            return value + 'awesome'

    validator = TestValidator()
    rv = validator.validate({'field1': 'tim'})
    assert rv.data['field1'] == 'timawesome'
    assert not rv.errors


def test_clean_field_error():
    class TestValidator(Validator):
        field1 = Field(str, required=True)

        def clean_field1(self, value):
            raise ValidationError('required')

    validator = TestValidator()
    rv = validator.validate({'field1': 'tim'})
    assert rv.data['field1'] == 'tim'
    assert rv.errors['field1'] == 'required field'


def test_clean():
    class TestValidator(Validator):
        field1 = Field(str, required=True)

        def clean(self, data):
            data['field1'] += 'awesome'
            return data

    validator = TestValidator()
    rv = validator.validate({'field1': 'tim'})
    assert rv.data['field1'] == 'timawesome'
    assert not rv.errors


def test_clean_error():
    class TestValidator(Validator):
        field1 = Field(str, required=True)

        def clean(self, data):
            raise ValidationError('required')

    validator = TestValidator()
    rv = validator.validate({'field1': 'tim'})
    assert rv.data['field1'] == 'tim'
    assert rv.errors['__base__'] == 'required field'


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
    rv = validator.validate({'field3': 'asdfasdf'})
    assert rv.errors['field1'] == 'enter value'
    assert rv.errors['field2'] == 'field2 required'
    assert rv.errors['field3'] == 'pick a number'

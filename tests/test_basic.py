from peewee_validates import Validator
from peewee_validates import ValidationError
from peewee_validates import Field


def test_required():
    class TestValidator(Validator):
        bool_field = Field('bool', required=True)
        decimal_field = Field('decimal', required=True)
        float_field = Field('float', required=True)
        int_field = Field('int', required=True)
        str_field = Field('str', required=True)
        date_field = Field('date', required=True)
        time_field = Field('time', required=True)
        datetime_field = Field('datetime', required=True)

    validator = TestValidator()
    validator.validate()
    assert validator.errors['bool_field'] == 'required'
    assert validator.errors['decimal_field'] == 'required'
    assert validator.errors['float_field'] == 'required'
    assert validator.errors['int_field'] == 'required'
    assert validator.errors['str_field'] == 'required'
    assert validator.errors['date_field'] == 'required'
    assert validator.errors['time_field'] == 'required'
    assert validator.errors['datetime_field'] == 'required'


def test_lengths():
    class TestValidator(Validator):
        max_field = Field('str', max_length=5)
        min_field = Field('str', min_length=5)

    validator = TestValidator()
    validator.validate({'min_field': 'shrt', 'max_field': 'toolong'})
    assert validator.errors['min_field'] == 'too short'
    assert validator.errors['max_field'] == 'too long'


def test_range():
    class TestValidator(Validator):
        range1 = Field('int', range=(1, 5))
        range2 = Field('int', range=(1, 5))

    validator = TestValidator()
    validator.validate({'range1': '44', 'range2': '3'})
    assert validator.errors['range1'] == 'invalid range'
    assert 'range2' not in validator.errors


def test_coerce_error():
    class TestValidator(Validator):
        date_field = Field('date')

    validator = TestValidator()
    validator.validate({'date_field': 'another'})
    assert validator.errors['date_field'] == 'must be date'


def test_callable_coerse():
    def alwaystim(value):
        return 'tim'

    class TestValidator(Validator):
        first_name = Field(alwaystim, choices=('tim', 'bob'))

    validator = TestValidator()
    validator.validate({'first_name': 'another'})
    assert not validator.errors


def test_callable_coerce_error():
    def mydate(value):
        raise ValueError

    class TestValidator(Validator):
        date_field = Field(mydate)

    validator = TestValidator()
    validator.validate({'date_field': 'another'})
    assert validator.errors['date_field'] == 'validation failed: coerce_mydate'


def test_choices():
    class TestValidator(Validator):
        first_name = Field('str', choices=('tim', 'bob'))

    validator = TestValidator()
    validator.validate()
    assert validator.errors['first_name'] == 'invalid choice'

    validator = TestValidator()
    validator.validate({'first_name': 'tim'})
    assert not validator.errors


def test_callable_choices():
    def getchoices():
        return ('tim', 'bob')

    class TestValidator(Validator):
        first_name = Field('str', choices=getchoices)

    validator = TestValidator()
    validator.validate()
    assert validator.errors['first_name'] == 'invalid choice'

    validator = TestValidator()
    validator.validate({'first_name': 'tim'})
    assert not validator.errors


def test_only_exclude():
    class TestValidator(Validator):
        field1 = Field('str', required=True)
        field2 = Field('str', required=True)

    validator = TestValidator()
    validator.validate({'field1': 'shrt'}, only=['field1'])
    assert not validator.errors

    validator.validate({'field1': 'shrt'}, exclude=['field2'])
    assert not validator.errors


def test_clean_field():
    class TestValidator(Validator):
        field1 = Field('str', required=True)

        def clean_field1(self, value):
            return value + 'awesome'

    validator = TestValidator()
    validator.validate({'field1': 'tim'})
    assert validator.data['field1'] == 'timawesome'
    assert not validator.errors


def test_clean_field_error():
    class TestValidator(Validator):
        field1 = Field('str', required=True)

        def clean_field1(self, value):
            raise ValidationError('required')

    validator = TestValidator()
    validator.validate({'field1': 'tim'})
    assert validator.data['field1'] == 'tim'
    assert validator.errors['field1'] == 'required'


def test_clean():
    class TestValidator(Validator):
        field1 = Field('str', required=True)

        def clean(self):
            self.data['field1'] += 'awesome'
            return self.data

    validator = TestValidator()
    validator.validate({'field1': 'tim'})
    assert validator.data['field1'] == 'timawesome'
    assert not validator.errors


def test_clean_error():
    class TestValidator(Validator):
        field1 = Field('str', required=True)

        def clean(self):
            raise ValidationError('required')

    validator = TestValidator()
    validator.validate({'field1': 'tim'})
    assert validator.data['field1'] == 'tim'
    assert validator.errors['__base__'] == 'required'


def test_custom_messages():
    class TestValidator(Validator):
        field1 = Field('str', required=True)
        field2 = Field('str', required=True)
        field3 = Field('int', required=True, max_length=4)

        class Meta:
            messages = {
                'required': 'enter value',
                'field2.required': 'field2 required',
                'field3.coerce_int': 'pick a number',
            }

    validator = TestValidator()
    validator.validate({'field3': 'asdfasdf'})
    assert validator.errors['field1'] == 'enter value'
    assert validator.errors['field2'] == 'field2 required'
    assert validator.errors['field3'] == 'pick a number'

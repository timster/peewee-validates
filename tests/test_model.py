from peewee_validates import ModelValidator
from peewee_validates import ValidationError

from tests.models import BasicFields
from tests.models import ComplexPerson
from tests.models import Person


def test_required():
    validator = ModelValidator(Person())
    validator.validate()
    assert validator.errors['name'] == 'required'


def test_clean():
    class TestValidator(ModelValidator):
        def clean(self):
            super().clean()
            self.data['name'] += 'awesome'
            return self.data

    validator = TestValidator(Person())
    validator.validate({'name': 'tim'})
    assert validator.data['name'] == 'timawesome'
    assert not validator.errors


def test_clean_error():
    class TestValidator(ModelValidator):
        def clean(self):
            raise ValidationError('required')

    validator = TestValidator(Person())
    validator.validate({'name': 'tim'})
    assert validator.data['name'] == 'tim'
    assert validator.errors['__base__'] == 'required'


def test_choices():
    validator = ModelValidator(ComplexPerson(name='tim'))

    validator.validate({'organization': 1, 'gender': 'S'})
    assert validator.errors['gender'] == 'invalid choice'
    assert 'name' not in validator.errors

    validator.validate({'organization': 1, 'gender': 'M'})
    validator.validate({'gender': 'M'})
    assert not validator.errors


def test_missing_relation():
    validator = ModelValidator(ComplexPerson(name='tim'))

    validator.validate()
    assert validator.errors['gender'] == 'required'
    assert 'name' not in validator.errors


def test_unique():
    person = Person(name='tim')
    person.save()

    validator = ModelValidator(Person(name='tim'))
    validator.validate({'gender': 'M'})
    assert validator.errors['name'] == 'must be unique'

    validator = ModelValidator(person)
    validator.validate({'gender': 'M'})
    assert not validator.errors


def test_unique_index():
    obj = BasicFields(field1='one', field2='two', field3='three')
    obj.save()

    validator = ModelValidator(BasicFields(field1='one', field2='two', field3='three'))
    validator.validate()
    assert validator.errors['field1'] == 'fields must be unique together'
    assert validator.errors['field2'] == 'fields must be unique together'

    validator = ModelValidator(obj)
    validator.validate()
    assert not validator.errors

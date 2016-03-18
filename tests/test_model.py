import peewee

from peewee_validates import ModelValidator
from peewee_validates import ValidationError


class Organization(peewee.Model):
    name = peewee.CharField(null=False)

    class Meta:
        database = peewee.SqliteDatabase(':memory:')


class Person(peewee.Model):
    name = peewee.CharField(null=False, max_length=5, unique=True)

    class Meta:
        database = peewee.SqliteDatabase(':memory:')


class ComplexPerson(Person):
    GENDER_CHOICES = (('M', 'Male'), ('F', 'Female'))
    gender = peewee.CharField(choices=GENDER_CHOICES)

    organization = peewee.ForeignKeyField(Organization, null=True)

    class Meta:
        indexes = (
            (('gender', 'name'), True),
            (('name', 'organization'), False),
        )


class IndexModel(peewee.Model):
    field1 = peewee.CharField()
    field2 = peewee.CharField()
    field3 = peewee.CharField()

    class Meta:
        database = peewee.SqliteDatabase(':memory:')
        indexes = (
            (('field1', 'field2'), True),
            (('field3',), False),
        )

Organization.create_table(fail_silently=True)
ComplexPerson.create_table(fail_silently=True)
Person.create_table(fail_silently=True)
IndexModel.create_table(fail_silently=True)

organization = Organization(name='main')
organization.save()


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
    obj = IndexModel(field1='one', field2='two', field3='three')
    obj.save()

    validator = ModelValidator(IndexModel(field1='one', field2='two', field3='three'))
    validator.validate()
    assert validator.errors['field1'] == 'fields must be unique together'
    assert validator.errors['field2'] == 'fields must be unique together'

    validator = ModelValidator(obj)
    validator.validate()
    assert not validator.errors

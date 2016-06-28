sga-lti
=========================
:sga-lti: LTI implementation of Staff Graded Assignments
:Version: 0.4.1
:Author: MIT Office of Digital Learning
:Homepage: http://odl.mit.edu
:License: BSD

.. image:: https://img.shields.io/travis/mitodl/sga-lti.svg
    :target: https://travis-ci.org/mitodl/sga-lti
.. image:: https://img.shields.io/coveralls/mitodl/sga-lti.svg
    :target: https://coveralls.io/r/mitodl/sga-lti
.. image:: https://img.shields.io/github/issues/mitodl/sga-lti.svg
    :target: https://github.com/mitodl/sga-lti/issues
.. image:: https://img.shields.io/badge/license-BSD-blue.svg
    :target: https://github.com/mitodl/sga-lti/blob/master/LICENSE

an LTI implementation of Staff Graded Assignments, for use with edX

Getting Started
===============

You can either run this locally with a default sqlite database after
installing the requirements.txt file, or if you have Docker and
prefer a cleaner environment, install docker-compose with ``pip
install docker-compose`` and run ``docker-compose up``. This will set
up
a near production-ready containerized development environment that
runs migrations, with the django development server running on
port 8071.

To run one-off commands, like shell, you can run
``docker-compose run web python manage.py shell`` or to create root
user, etc.

Environment/Local Variables
===========================

The following variables need to be created in environment or in local
settings ("sga-lti.yml"):

```python
# Media files (for uploaded files)
AWS_STORAGE_BUCKET_NAME  # S3 bucket name
AWS_ACCESS_KEY_ID:  # S3 access key id credential
AWS_SECRET_ACCESS_KEY:  # S3 secret access key credential
MEDIAFILES_LOCATION:  # Optional S3 subfolder within AWS_STORAGE_BUCKET_NAME
```


Adding an application
=====================

To add an application to this, add it to the requirements file, add
its needed settings, include its URLs, and provide any needed template
overrides.


Testing
=======

The project is set up with
`tox<https://tox.readthedocs.org/en/latest/>`_ and
`py.test<http://pytest.org/latest/>`_. It will run pylint, pep8, and
py.test tests with coverage. It will also generate an HTML coverage
report. To run them all inside the docker image, run ``docker-compose
run web tox``, or if you are running locally, after installing the
requirements file, just run ``tox``.

Continuous Testing
~~~~~~~~~~~~~~~~~~

If you want test to run on file changes, the ``test_requirements.txt``
adds pytest-watcher, which can be started with ``ptw``. This
unfortunately will not work well in the Docker container because the
file events it uses are fired on the host OS, and not the docker OS. I
have corrected it upstream with
`issue<https://github.com/joeyespo/pytest-watch/issues/9>`_ to the
`pytest-watch repo<https://github.com/joeyespo/pytest-watch>`_, but it
has not been released to pypi as of this writing.

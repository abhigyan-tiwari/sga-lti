"""
Backend logic for file uploads and downloads
"""

import os
import re
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

from django.http import HttpResponse

from sga.backend.constants import INVALID_S3_CHARACTERS_REGEX
from django.http.response import StreamingHttpResponse


def convert_illegal_S3_chars(path, replace_with="_"):
    """
    Converts illegal S3 characters to replace_with
    """
    return re.sub(INVALID_S3_CHARACTERS_REGEX, replace_with, path)


def serve_zip_file(submissions, zipname="zipfile"):
    """
    Takes a list of submissions and generates a streaming response from them
    """
    resp = StreamingHttpResponse(submissions_zip_generator(submissions), content_type="application/zip")
    resp["Content-Disposition"] = "attachment; filename={zipname}.zip".format(zipname=zipname)
    return resp


def submissions_zip_generator(submissions):
    """ Generator to create the streaming response from the submissions """
    bytes_io = BytesIO()
    with ZipFile(bytes_io, mode="w", compression=ZIP_DEFLATED, allowZip64=True) as zip_file:
        for submission in submissions:
            zip_file.writestr(submission.student_document, submission.student_document.read())
            yield bytes_io.getvalue()
            bytes_io.empty()
    yield bytes_io.getvalue()


def student_submission_file_path(instance, filename):
    """
    Returns the upload destination path (including filename) for a student submission
    """
    path = "{course_id}/student-uploads/{assignment_id}/{username}-{assignment_name}{extension}".format(
        course_id=instance.assignment.course.edx_id,
        assignment_id=instance.assignment.edx_id,
        username=instance.student.username,
        assignment_name=instance.assignment.name,
        extension=os.path.splitext(filename)[1]
    )
    return convert_illegal_S3_chars(path)


def grader_submission_file_path(instance, filename):
    """
    Returns the upload destination path (including filename) for a grader submission
    """
    path = "{course_id}/grader-uploads/{assignment_id}/{username}-{assignment_name}{extension}".format(
        course_id=instance.assignment.course.edx_id,
        assignment_id=instance.assignment.edx_id,
        username=instance.student.username,
        assignment_name=instance.assignment.name,
        extension=os.path.splitext(filename)[1]
    )
    return convert_illegal_S3_chars(path)

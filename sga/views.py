"""
sga views
"""
import json

from datetime import datetime
from django.conf import settings
from django.contrib.auth import login, authenticate
from django.core.urlresolvers import reverse
from django.http import Http404
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

from sga.backend.authentication import allowed_roles
from sga.constants import Roles
from sga.forms import StudentAssignmentSubmissionForm, GraderAssignmentSubmissionForm
from sga.models import Assignment, Submission, Course, Grader, Student


def index(request):
    """
    The index view. Display available programs
    """
    course = Course.objects.first()
    return render(request, "sga/index.html", context={
        "course": course
    })


@allowed_roles([Roles.student])
def view_submission_as_student(request, assignment_id):
    """
    Submission view for students
    """
    try:
        assignment = Assignment.objects.get(edx_id=assignment_id)
        submission, created = Submission.objects.get_or_create(student=request.user, assignment=assignment)
    except:
        raise Http404()
    if request.method == "POST":
        submission_form = StudentAssignmentSubmissionForm(request.POST, request.FILES, instance=submission)
        if submission_form.is_valid():
            submission_form.save()
            submission.submitted = True
            submission.submitted_at = datetime.utcnow()
            submission.save()
            redirect("view_submission_as_student", assignment_id=assignment_id)
    else:
        submission_form = StudentAssignmentSubmissionForm(instance=submission)
    return render(request, "sga/view_submission_as_student.html", context={
        "submission_form": submission_form,
        "submission": submission,
        "assignment": assignment,
    })


@allowed_roles([Roles.grader, Roles.admin])
def view_submission_as_staff(request, assignment_id, student_user_id):
    """
    Submission view for staff
    """
    try:
        assignment = Assignment.objects.get(edx_id=assignment_id)
        student = Student.objects.get(user__username=student_user_id)
        submission, created = Submission.objects.get_or_create(student=student.user, assignment=assignment)
    except:
        raise Http404()
    next_not_graded_submission = Submission.objects.filter(assignment=assignment, submitted=True,
                                                           graded_at=None).exclude(pk=submission.pk).first()
    if next_not_graded_submission:
        next_not_graded_submission_url = reverse("view_submission_as_staff", kwargs={
            "assignment_id": assignment_id,
            "student_user_id": next_not_graded_submission.student.username
        })
    else:
        next_not_graded_submission_url = None
    if request.method == "POST":
        submission_form = GraderAssignmentSubmissionForm(request.POST, request.FILES, instance=submission)
        if submission_form.is_valid():
            submission_form.save()
            submission.graded_at = datetime.utcnow()
            submission.graded_by = request.user
            submission.graded = True
            submission.save()
            redirect("view_submission_as_staff", assignment_id=assignment_id, student_user_id=student.user.username)
        else:
            # Clear changes made to submission instance since form is invalid (form field values are untouched)
            submission = Submission.objects.get(pk=submission.pk)
    else:
        submission_form = GraderAssignmentSubmissionForm(instance=submission)
    return render(request, "sga/view_submission_as_staff.html", context={
        "submission_form": submission_form,
        "next_not_graded_submission_url": next_not_graded_submission_url,
        "submission": submission,
        "assignment": assignment,
        "student_user": student.user,
    })


@allowed_roles([Roles.admin])
def unsubmit_submission(request, assignment_id, student_user_id):
    try:
        assignment = Assignment.objects.get(edx_id=assignment_id)
        student = Student.objects.get(user__username=student_user_id)
        submission, created = Submission.objects.get_or_create(student=student.user, assignment=assignment)
    except:
        raise Http404()
    submission.submitted = False
    submission.graded = False
    submission.save()
    return redirect("view_submission_as_staff", assignment_id=assignment_id, student_user_id=student_user_id)


@allowed_roles([Roles.grader, Roles.admin])
def view_assignment(request, assignment_id):
    """
    Assignment view for graders
    """
    try:
        assignment = Assignment.objects.get(edx_id=assignment_id)
        course = assignment.course
    except:
        raise Http404()
    student_users = course.students.all()
    for student_user in student_users:
        submission, created = Submission.objects.get_or_create(student=student_user, assignment=assignment)
        student_user.submitted = "Yes" if submission.submitted else "No"
        student_user.graded = "Yes" if submission.graded() else "No"
    return render(request, "sga/view_assignment.html", context={
        "student_users": student_users,
        "course": course,
        "assignment": assignment
    })


@allowed_roles([Roles.grader, Roles.admin])
def view_student_list(request, course_id):
    """
    Student list view for graders
    """
    try:
        course = Course.objects.get(edx_id=course_id)
    except:
        raise Http404()
    student_users = course.students.all()
    for student_user in student_users:
        student_user.not_graded_submissions_count = course.not_graded_submissions_count_by_user(student_user)
    return render(request, "sga/view_student_list.html", context={
        "course": course,
        "student_users": student_users
    })


@allowed_roles([Roles.grader, Roles.admin])
def view_assignment_list(request, course_id):
    """
    Assignment list view for graders
    """
    try:
        course = Course.objects.get(edx_id=course_id)
    except:
        raise Http404()
    assignments = course.assignments.all()
    return render(request, "sga/view_assignment_list.html", context={
        "course": course,
        "assignments": assignments
    })


@allowed_roles([Roles.student, Roles.grader, Roles.admin])
def view_student(request, course_id, student_user_id):
    """
    Student view for graders
    """
    try:
        course = Course.objects.get(edx_id=course_id)
        student_user = Student.objects.get(user__username=student_user_id).user
    except:
        raise Http404()
    assignments = course.assignments.all()
    for assignment in assignments:
        assignment.submission, created = assignment.submissions.get_or_create(student=student_user)
    return render(request, "sga/view_student.html", context={
        "course": course,
        "student_user": student_user,
        "assignments": assignments
    })


@allowed_roles([Roles.grader, Roles.admin])
def view_grader(request, course_id, grader_user_id):
    """
    Student view for graders
    """
    try:
        course = Course.objects.get(edx_id=course_id)
        grader = Grader.objects.get(user__username=grader_user_id)
    except:
        raise Http404()
    graded_submissions = grader.user.graded_submissions.all()
    return render(request, "sga/view_grader.html", context={
        "course": course,
        "grader": grader,
        "graded_submissions": graded_submissions,
    })

@allowed_roles([Roles.admin])
def view_grader_list(request, course_id):
    """
    Grader list view for admins
    """
    try:
        course = Course.objects.get(edx_id=course_id)
    except:
        raise Http404()
    graders = course.grader_set.all()
    # for grader_user in grader_users:
    #     grader_user.not_graded_submissions = course.not_graded_submissions_by_user(grader_user)
    return render(request, "sga/view_grader_list.html", context={
        "course": course,
        "graders": graders
    })


def dev_start(request, username):
    """
    For local development only - sets session variables and authenticates user
    """
    if settings.DEVELOPMENT:
        user = authenticate(username=username, password=" ")
        login(request, user)
        SESSION = {
            "user_id": username,  # Edx user id
            "resource_link_title": "Assignment Title",  # Assignment title
            "resource_link_id": "assignment1id",  # Assignment Edx id
            "context_label": "Course Title",  # Course title
            "context_id": "courseid",  # Course Edx id
            "roles": "student",  # User role
        }
        for var, val in SESSION.items():
            request.session[var] = val
    return redirect("sga-index")

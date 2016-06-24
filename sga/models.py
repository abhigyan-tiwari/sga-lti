"""
Model definitions
"""

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from sga.backend.files import student_submission_file_path, grader_submission_file_path
from sga.backend.validators import validate_file_extension
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied


class TimeStampedModel(models.Model):
    """
    Base model for create/update timestamps
    """
    created_on = models.DateTimeField(auto_now_add=True)  # UTC
    updated_on = models.DateTimeField(auto_now=True)  # UTC

    def update(self, **kwargs):
        """
        Automatically update updated_on timestamp
        """
        update_fields = {"updated_on"}
        for k, v in kwargs.items():
            setattr(self, k, v)
            update_fields.add(k)
        self.save(update_fields=update_fields)

    class Meta:
        abstract = True

class CourseModel(TimeStampedModel):
    """
    Base model for models relating to the course to allow authentication checks
    """
    @classmethod
    def get_or_404_check_course(cls, course_id, **kwargs):
        obj = get_object_or_404(cls, **kwargs)
        if obj.course_id != course_id:
            raise PermissionDenied()
        return obj

    class Meta:
        abstract = True


class Grader(CourseModel):
    """
    Grader model (intermediate between Course and User)
    """
    max_students = models.IntegerField(default=10)
    user = models.ForeignKey(User)
    course = models.ForeignKey("Course")

    def __str__(self):  # pragma: no cover
        return self.user.get_full_name()

    def graded_submissions_count(self):
        """
        Returns a count of submission that are graded by this grader
        """
        return Submission.objects.filter(
            graded_by=self.user,
            assignment__course=self.course,
            submitted=True,
            graded=True
        ).count()

    def not_graded_submissions_count(self):
        """
        Returns a count of submission that are submitted but not graded by this grader
        """
        student_users = [s.user for s in self.students.all()]
        return Submission.objects.filter(
            student__in=student_users,
            assignment__course=self.course,
            submitted=True,
            graded=False
        ).count()

    def available_student_slots_count(self):
        """
        Returns a count of the number of students this grader can still accept
        """
        return self.max_students - self.students.count()

    class Meta():
        unique_together = (("user", "course"),)


class Student(CourseModel):
    """
    Student model (intermediate between Course and User)
    """
    grader = models.ForeignKey(Grader, null=True, related_name="students", on_delete=models.SET_NULL)
    user = models.ForeignKey(User)
    course = models.ForeignKey("Course")

    def __str__(self):  # pragma: no cover
        return self.user.get_full_name()

    class Meta():
        unique_together = (("user", "course"),)


class Course(TimeStampedModel):
    """
    Course model
    """
    edx_id = models.CharField(max_length=128, unique=True)
    administrators = models.ManyToManyField(User, related_name="administrator_courses")
    graders = models.ManyToManyField(User, through=Grader, related_name="grader_courses")
    students = models.ManyToManyField(User, through=Student, related_name="student_courses")

    def has_student(self, user):
        """
        Returns a boolean of whether or not user is a Student in this course
        """
        return self.students.filter(pk=user.pk).exists() and not self.has_grader(user)

    def has_grader(self, user):
        """
        Returns a boolean of whether or not user is a Grader in this course
        """
        return self.graders.filter(pk=user.pk).exists()

    def has_admin(self, user):
        """
        Returns a boolean of whether or not user is an administrator in this course
        """
        return self.administrators.filter(pk=user.pk).exists()

    def not_graded_submissions_count_by_student(self, student):
        """
        Returns a count of submissions by this student that are submitted but not graded
        """
        return Submission.objects.filter(
            assignment__course=self,
            student=student.user,
            submitted=True,
            graded=False
        ).count()


class Assignment(CourseModel):
    """
    Assignment model
    """
    edx_id = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=128)
    due_date = models.DateTimeField(null=True)
    grace_period = models.IntegerField(default=0)
    course = models.ForeignKey(Course, related_name="assignments")

    def graded_submissions_count(self):
        """
        Returns a count of submissions for this assignment that are graded
        """
        return self.submissions.filter(submitted=True, graded=True).count()

    def graded_submissions_count_by_grader(self, grader=None, grader_user=None):
        """
        Returns a count of submissions for this assignment for this grader that are graded
        """
        if not grader_user:
            grader_user = grader.user
        return Submission.objects.filter(
            graded_by=grader_user,
            assignment=self,
            submitted=True,
            graded=True
        ).count()

    def not_graded_submissions_count(self):
        """
        Returns a count of submissions for this assignment that are submitted but not graded
        """
        return self.submissions.filter(submitted=True, graded=False).count()

    def not_graded_submissions_count_by_grader(self, grader=None, grader_user=None):
        """
        Returns a count of submissions for this assignment for this grader that are submitted but not graded
        """
        if not grader:
            grader = Grader.objects.get(user=grader_user, course=self.course)
        student_users = [s.user for s in grader.students.all()]
        return Submission.objects.filter(
            student__in=student_users,
            assignment=self,
            submitted=True,
            graded=False
        ).count()

    def not_submitted_submissions_count(self):
        """
        Returns a count of submissions for this assignment that are not submitted
        """
        # Graders all have student objects
        students_in_course = self.course.students.count() - self.course.graders.count()
        return students_in_course - self.graded_submissions_count() - self.not_graded_submissions_count()

    def not_submitted_submissions_count_by_grader(self, grader=None, grader_user=None):
        """
        Returns a count of submissions for this assignment for this grader that are not submitted
        """
        if not grader:
            grader = Grader.objects.get(user=grader_user, course=self.course)
        return (grader.students.count()
                - self.graded_submissions_count_by_grader(grader_user=grader.user)
                - self.not_graded_submissions_count_by_grader(grader=grader))


class Submission(TimeStampedModel):
    """
    Submission model
    """
    assignment = models.ForeignKey(Assignment, related_name="submissions")
    student = models.ForeignKey(User, related_name="submitted_submissions")
    graded_by = models.ForeignKey(User, null=True, related_name="graded_submissions")

    description = models.TextField(null=True)
    feedback = models.TextField(null=True)
    grade = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)], null=True)  # 0-100
    submitted_at = models.DateTimeField(null=True)  # UTC
    graded_at = models.DateTimeField(null=True)  # UTC
    submitted = models.BooleanField(default=False)
    graded = models.BooleanField(default=False)

    student_document = models.FileField(
        upload_to=student_submission_file_path,
        null=True,
        validators=[validate_file_extension]
    )
    grader_document = models.FileField(
        upload_to=grader_submission_file_path,
        null=True,
        validators=[validate_file_extension]
    )

    def grade_display(self):
        """
        Human-readable display of this submission's grade
        """
        if self.grade:
            return "{grade}/100 ({percent}%)".format(grade=self.grade, percent=self.grade)
        else:
            return "(Not Graded)"

    class Meta:
        unique_together = (("assignment", "student"),)

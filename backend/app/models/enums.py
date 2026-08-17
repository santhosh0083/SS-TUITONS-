"""Enumerations shared across the schema.

These are created as native PostgreSQL enum types so the database itself
rejects invalid values, not just the application layer.
"""

import enum


class RoleCode(str, enum.Enum):
    ADMIN = "ADMIN"
    TUTOR = "TUTOR"
    PARENT = "PARENT"
    STUDENT = "STUDENT"


class UserStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class Grade(str, enum.Enum):
    """Grades 1-12.

    Grades 1-10 were added in migration 0002 when the business expanded from
    Grade 11-12 exam coaching to home and online tuition across all school
    years. Enum order matches numeric order, so sorting works naturally.
    """

    GRADE_1 = "1"
    GRADE_2 = "2"
    GRADE_3 = "3"
    GRADE_4 = "4"
    GRADE_5 = "5"
    GRADE_6 = "6"
    GRADE_7 = "7"
    GRADE_8 = "8"
    GRADE_9 = "9"
    GRADE_10 = "10"
    GRADE_11 = "11"
    GRADE_12 = "12"


class ClassMode(str, enum.Enum):
    BATCH = "batch"
    ONE_TO_ONE = "one_to_one"


class EnrolmentStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    WITHDRAWN = "withdrawn"


class ClassSessionStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MeetingIntegrationStatus(str, enum.Enum):
    """How a class session's meeting link came to exist.

    NOT_CONFIGURED means no link exists and none may be stored — a database
    CHECK enforces that, so the platform can never invent one.

    MANUAL means a person created a real link inside Google Meet and pasted it
    in. Genuine link, no Workspace required.
    """

    NOT_CONFIGURED = "not_configured"
    MANUAL = "manual"
    PENDING = "pending"
    ACTIVE = "active"
    FAILED = "failed"


class ClassReportStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    REVIEWED = "reviewed"


class AttendanceMark(str, enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    EXCUSED = "excused"


class ContentType(str, enum.Enum):
    WORKSHEET = "worksheet"
    NOTES = "notes"
    PYQ = "pyq"
    ASSIGNMENT = "assignment"
    REFERENCE = "reference"


class AccessScopeType(str, enum.Enum):
    BATCH = "batch"
    COURSE = "course"
    EXAM_GRADE = "exam_grade"
    STUDENT = "student"


class VirusScanStatus(str, enum.Enum):
    PENDING = "pending"
    CLEAN = "clean"
    INFECTED = "infected"
    SKIPPED = "skipped"


class QuestionType(str, enum.Enum):
    MCQ_SINGLE = "mcq_single"
    MCQ_MULTI = "mcq_multi"
    NUMERICAL = "numerical"
    SHORT_ANSWER = "short_answer"


class Difficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuestionSource(str, enum.Enum):
    MANUAL = "manual"
    AI_GENERATED = "ai_generated"
    PYQ = "pyq"


class ReviewStatus(str, enum.Enum):
    """AI-generated questions enter as PENDING_REVIEW and cannot be served
    to a student until an admin approves them."""

    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class TestType(str, enum.Enum):
    TOPIC = "topic"
    MOCK = "mock"
    ASSIGNMENT = "assignment"


class AttemptStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    EVALUATED = "evaluated"
    ABANDONED = "abandoned"


class BillingCycle(str, enum.Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ONE_TIME = "one_time"


class InvoiceStatus(str, enum.Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    WAIVED = "waived"
    CANCELLED = "cancelled"


class PaymentMethod(str, enum.Enum):
    UPI = "upi"
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"


class SubmissionStatus(str, enum.Enum):
    """A payment_submission is an unverified CLAIM. Only an admin moving it to
    VERIFIED creates a row in `payments`."""

    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class ConversationType(str, enum.Enum):
    PARENT_TUTOR = "parent_tutor"
    PARENT_ADMIN = "parent_admin"


class NotificationChannel(str, enum.Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"


class NotificationType(str, enum.Enum):
    CLASS_UPCOMING = "class_upcoming"
    CLASS_REMINDER = "class_reminder"
    TEST_REMINDER = "test_reminder"
    ASSIGNMENT = "assignment"
    FEE_REMINDER = "fee_reminder"
    PAYMENT_CONFIRMED = "payment_confirmed"
    MESSAGE_RECEIVED = "message_received"
    PERFORMANCE_ALERT = "performance_alert"
    AI_RECOMMENDATION = "ai_recommendation"
    ATTENDANCE_DISCREPANCY = "attendance_discrepancy"


class AISessionMode(str, enum.Enum):
    TUTOR = "tutor"
    HOMEWORK_SCAN = "homework_scan"


class RecommendationKind(str, enum.Enum):
    TOPIC = "topic"
    WORKSHEET = "worksheet"
    TEST = "test"
    REVISION = "revision"


class RecommendationSource(str, enum.Enum):
    ML_MODEL = "ml_model"
    HEURISTIC = "heuristic"


class MLTask(str, enum.Enum):
    PERFORMANCE_PREDICTION = "performance_prediction"
    RISK_DETECTION = "risk_detection"
    WEAKNESS_DETECTION = "weakness_detection"


class ConsentType(str, enum.Enum):
    DATA_PROCESSING = "data_processing"
    CLASS_RECORDING = "class_recording"
    AI_TUTOR_USE = "ai_tutor_use"

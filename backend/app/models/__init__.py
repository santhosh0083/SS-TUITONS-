"""All ORM models.

Every model must be imported here. Alembic's autogenerate compares
`Base.metadata` against the live database, and a model that is never imported
is invisible to that comparison — it would be silently dropped from migrations.
"""

from app.db.base import Base
from app.models.academics import (
    Batch,
    BatchStudent,
    Course,
    CourseSubject,
    Exam,
    FeePlan,
    Subject,
    TutorAssignment,
)
from app.models.ai_ml import (
    AIMessage,
    AIRecommendation,
    AISession,
    DocumentChunk,
    MLFeatureSnapshot,
    MLModel,
    MLPrediction,
)
from app.models.assessment import (
    Question,
    QuestionNumericAnswer,
    QuestionOption,
    StudentTopicPerformance,
    Test,
    TestAnswer,
    TestAttempt,
    TestQuestion,
)
from app.models.content import (
    Chapter,
    ContentAccessRule,
    ContentItem,
    StoredFile,
    Topic,
)
from app.models.finance import Invoice, Payment, PaymentSubmission
from app.models.identity import (
    Parent,
    RefreshToken,
    Role,
    Student,
    StudentParent,
    Tutor,
    User,
    UserRole,
)
from app.models.messaging import (
    Conversation,
    ConversationMember,
    Message,
    MessageAttachment,
    Notification,
)
from app.models.ops import AuditLog, ConsentRecord
from app.models.scheduling import Attendance, ClassReport, ClassSession

__all__ = [
    "Base",
    # identity
    "User",
    "Role",
    "UserRole",
    "Student",
    "Parent",
    "Tutor",
    "StudentParent",
    "RefreshToken",
    # academics
    "Exam",
    "Subject",
    "Course",
    "CourseSubject",
    "Batch",
    "BatchStudent",
    "TutorAssignment",
    "FeePlan",
    # scheduling
    "ClassSession",
    "ClassReport",
    "Attendance",
    # content
    "Chapter",
    "Topic",
    "StoredFile",
    "ContentItem",
    "ContentAccessRule",
    # assessment
    "Question",
    "QuestionOption",
    "QuestionNumericAnswer",
    "Test",
    "TestQuestion",
    "TestAttempt",
    "TestAnswer",
    "StudentTopicPerformance",
    # finance
    "Invoice",
    "PaymentSubmission",
    "Payment",
    # messaging
    "Conversation",
    "ConversationMember",
    "Message",
    "MessageAttachment",
    "Notification",
    # ai/ml
    "AISession",
    "AIMessage",
    "DocumentChunk",
    "AIRecommendation",
    "MLModel",
    "MLFeatureSnapshot",
    "MLPrediction",
    # ops
    "AuditLog",
    "ConsentRecord",
]

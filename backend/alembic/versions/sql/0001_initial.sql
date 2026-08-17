CREATE TYPE grade AS ENUM ('11', '12');

CREATE TYPE class_mode AS ENUM ('batch', 'one_to_one');

CREATE TYPE enrolment_status AS ENUM ('active', 'completed', 'withdrawn');

CREATE TYPE billing_cycle AS ENUM ('monthly', 'quarterly', 'one_time');

CREATE TYPE ai_session_mode AS ENUM ('tutor', 'homework_scan');

CREATE TYPE recommendation_kind AS ENUM ('topic', 'worksheet', 'test', 'revision');

CREATE TYPE recommendation_source AS ENUM ('ml_model', 'heuristic');

CREATE TYPE ml_task AS ENUM ('performance_prediction', 'risk_detection', 'weakness_detection');

CREATE TYPE question_type AS ENUM ('mcq_single', 'mcq_multi', 'numerical', 'short_answer');

CREATE TYPE difficulty AS ENUM ('easy', 'medium', 'hard');

CREATE TYPE question_source AS ENUM ('manual', 'ai_generated', 'pyq');

CREATE TYPE review_status AS ENUM ('pending_review', 'approved', 'rejected');

CREATE TYPE test_type AS ENUM ('topic', 'mock', 'assignment');

CREATE TYPE attempt_status AS ENUM ('in_progress', 'submitted', 'evaluated', 'abandoned');

CREATE TYPE virus_scan_status AS ENUM ('pending', 'clean', 'infected', 'skipped');

CREATE TYPE content_type AS ENUM ('worksheet', 'notes', 'pyq', 'assignment', 'reference');

CREATE TYPE access_scope_type AS ENUM ('batch', 'course', 'exam_grade', 'student');

CREATE TYPE invoice_status AS ENUM ('pending', 'partial', 'paid', 'overdue', 'waived', 'cancelled');

CREATE TYPE payment_method AS ENUM ('upi', 'bank_transfer', 'cash');

CREATE TYPE submission_status AS ENUM ('pending', 'verified', 'rejected');

CREATE TYPE user_status AS ENUM ('pending', 'active', 'suspended');

CREATE TYPE role_code AS ENUM ('ADMIN', 'TUTOR', 'PARENT', 'STUDENT');

CREATE TYPE conversation_type AS ENUM ('parent_tutor', 'parent_admin');

CREATE TYPE notification_type AS ENUM ('class_upcoming', 'class_reminder', 'test_reminder', 'assignment', 'fee_reminder', 'payment_confirmed', 'message_received', 'performance_alert', 'ai_recommendation', 'attendance_discrepancy');

CREATE TYPE notification_channel AS ENUM ('in_app', 'email', 'sms', 'whatsapp');

CREATE TYPE consent_type AS ENUM ('data_processing', 'class_recording', 'ai_tutor_use');

CREATE TYPE class_session_status AS ENUM ('scheduled', 'ongoing', 'completed', 'cancelled');

CREATE TYPE meeting_integration_status AS ENUM ('not_configured', 'pending', 'active', 'failed');

CREATE TYPE class_report_status AS ENUM ('draft', 'submitted', 'reviewed');

CREATE TYPE attendance_mark AS ENUM ('present', 'absent', 'late', 'excused');

CREATE TABLE exams (
	code VARCHAR(20) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	description TEXT, 
	is_active BOOLEAN NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_exams PRIMARY KEY (id), 
	CONSTRAINT uq_exams_code UNIQUE (code)
);

CREATE TABLE subjects (
	code VARCHAR(20) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_subjects PRIMARY KEY (id), 
	CONSTRAINT uq_subjects_code UNIQUE (code)
);

CREATE TABLE ml_models (
	name VARCHAR(100) NOT NULL, 
	task ml_task NOT NULL, 
	algorithm VARCHAR(80) NOT NULL, 
	version VARCHAR(30) NOT NULL, 
	trained_at TIMESTAMP WITH TIME ZONE, 
	training_rows INTEGER, 
	metrics JSONB, 
	feature_list JSONB, 
	artifact_path VARCHAR(500), 
	is_active BOOLEAN NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_ml_models PRIMARY KEY (id), 
	CONSTRAINT uq_ml_models_name_version UNIQUE (name, version)
);

CREATE TABLE users (
	email CITEXT NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	full_name VARCHAR(200) NOT NULL, 
	phone VARCHAR(20), 
	status user_status NOT NULL, 
	is_superadmin BOOLEAN NOT NULL, 
	failed_login_count INTEGER NOT NULL, 
	locked_until TIMESTAMP WITH TIME ZONE, 
	last_login_at TIMESTAMP WITH TIME ZONE, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_users PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE roles (
	code role_code NOT NULL, 
	name VARCHAR(50) NOT NULL, 
	description TEXT, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_roles PRIMARY KEY (id), 
	CONSTRAINT uq_roles_code UNIQUE (code)
);

CREATE TABLE courses (
	name VARCHAR(150) NOT NULL, 
	exam_id UUID NOT NULL, 
	grade grade NOT NULL, 
	mode class_mode NOT NULL, 
	description TEXT, 
	duration_months INTEGER, 
	classes_per_week INTEGER, 
	class_duration_minutes INTEGER, 
	max_batch_size INTEGER, 
	is_active BOOLEAN NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_courses PRIMARY KEY (id), 
	CONSTRAINT fk_courses_exam_id_exams FOREIGN KEY(exam_id) REFERENCES exams (id) ON DELETE RESTRICT
);

CREATE TABLE chapters (
	subject_id UUID NOT NULL, 
	exam_id UUID NOT NULL, 
	grade grade NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	sequence INTEGER NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_chapters PRIMARY KEY (id), 
	CONSTRAINT uq_chapters_subject_id_exam_id_grade_name UNIQUE (subject_id, exam_id, grade, name), 
	CONSTRAINT fk_chapters_subject_id_subjects FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE CASCADE, 
	CONSTRAINT fk_chapters_exam_id_exams FOREIGN KEY(exam_id) REFERENCES exams (id) ON DELETE CASCADE
);

CREATE TABLE files (
	bucket VARCHAR(100) NOT NULL, 
	object_path VARCHAR(500) NOT NULL, 
	original_filename VARCHAR(300) NOT NULL, 
	mime_type VARCHAR(120) NOT NULL, 
	size_bytes BIGINT NOT NULL, 
	checksum_sha256 VARCHAR(64), 
	virus_scan_status virus_scan_status NOT NULL, 
	uploaded_by UUID NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_files PRIMARY KEY (id), 
	CONSTRAINT uq_files_bucket_object_path UNIQUE (bucket, object_path), 
	CONSTRAINT fk_files_uploaded_by_users FOREIGN KEY(uploaded_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE TABLE user_roles (
	user_id UUID NOT NULL, 
	role_id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_user_roles PRIMARY KEY (user_id, role_id), 
	CONSTRAINT fk_user_roles_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	CONSTRAINT fk_user_roles_role_id_roles FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE RESTRICT
);

CREATE TABLE students (
	user_id UUID NOT NULL, 
	admission_no VARCHAR(30) NOT NULL, 
	grade grade NOT NULL, 
	target_exam_id UUID, 
	date_of_birth DATE, 
	school_name VARCHAR(200), 
	joined_on DATE NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_students PRIMARY KEY (id), 
	CONSTRAINT uq_students_user_id UNIQUE (user_id), 
	CONSTRAINT fk_students_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	CONSTRAINT uq_students_admission_no UNIQUE (admission_no), 
	CONSTRAINT fk_students_target_exam_id_exams FOREIGN KEY(target_exam_id) REFERENCES exams (id) ON DELETE SET NULL
);

CREATE TABLE parents (
	user_id UUID NOT NULL, 
	occupation VARCHAR(120), 
	preferred_contact VARCHAR(20), 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_parents PRIMARY KEY (id), 
	CONSTRAINT uq_parents_user_id UNIQUE (user_id), 
	CONSTRAINT fk_parents_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE tutors (
	user_id UUID NOT NULL, 
	qualification VARCHAR(200), 
	experience_years INTEGER, 
	bio TEXT, 
	is_contact_public BOOLEAN NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_tutors PRIMARY KEY (id), 
	CONSTRAINT uq_tutors_user_id UNIQUE (user_id), 
	CONSTRAINT fk_tutors_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE refresh_tokens (
	user_id UUID NOT NULL, 
	token_hash VARCHAR(128) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	user_agent VARCHAR(400), 
	ip_address VARCHAR(45), 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_refresh_tokens PRIMARY KEY (id), 
	CONSTRAINT fk_refresh_tokens_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	CONSTRAINT uq_refresh_tokens_token_hash UNIQUE (token_hash)
);

CREATE INDEX ix_refresh_tokens_user_id ON refresh_tokens (user_id);

CREATE TABLE notifications (
	user_id UUID NOT NULL, 
	notification_type notification_type NOT NULL, 
	channel notification_channel NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	body TEXT, 
	link_url VARCHAR(500), 
	related_entity_type VARCHAR(50), 
	related_entity_id UUID, 
	is_read BOOLEAN NOT NULL, 
	read_at TIMESTAMP WITH TIME ZONE, 
	sent_at TIMESTAMP WITH TIME ZONE, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_notifications PRIMARY KEY (id), 
	CONSTRAINT fk_notifications_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_notifications_user_id ON notifications (user_id);

CREATE TABLE audit_logs (
	actor_user_id UUID, 
	action VARCHAR(100) NOT NULL, 
	entity_type VARCHAR(60) NOT NULL, 
	entity_id UUID, 
	before_state JSONB, 
	after_state JSONB, 
	ip_address VARCHAR(45), 
	user_agent VARCHAR(400), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	CONSTRAINT pk_audit_logs PRIMARY KEY (id), 
	CONSTRAINT fk_audit_logs_actor_user_id_users FOREIGN KEY(actor_user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_audit_logs_entity_id ON audit_logs (entity_id);

CREATE INDEX ix_audit_logs_action ON audit_logs (action);

CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);

CREATE INDEX ix_audit_logs_actor_user_id ON audit_logs (actor_user_id);

CREATE TABLE course_subjects (
	course_id UUID NOT NULL, 
	subject_id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_course_subjects PRIMARY KEY (course_id, subject_id), 
	CONSTRAINT fk_course_subjects_course_id_courses FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE, 
	CONSTRAINT fk_course_subjects_subject_id_subjects FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE RESTRICT
);

CREATE TABLE batches (
	code VARCHAR(40) NOT NULL, 
	course_id UUID NOT NULL, 
	capacity INTEGER NOT NULL, 
	start_date DATE, 
	end_date DATE, 
	is_active BOOLEAN NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_batches PRIMARY KEY (id), 
	CONSTRAINT uq_batches_code UNIQUE (code), 
	CONSTRAINT fk_batches_course_id_courses FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE RESTRICT
);

CREATE TABLE fee_plans (
	course_id UUID NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	amount INTEGER, 
	registration_fee INTEGER, 
	currency VARCHAR(3) NOT NULL, 
	billing_cycle billing_cycle NOT NULL, 
	due_day_of_month INTEGER, 
	grace_days INTEGER NOT NULL, 
	late_fee INTEGER, 
	is_active BOOLEAN NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_fee_plans PRIMARY KEY (id), 
	CONSTRAINT fk_fee_plans_course_id_courses FOREIGN KEY(course_id) REFERENCES courses (id) ON DELETE CASCADE
);

CREATE TABLE ai_sessions (
	student_id UUID NOT NULL, 
	mode ai_session_mode NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	ended_at TIMESTAMP WITH TIME ZONE, 
	total_tokens_in INTEGER NOT NULL, 
	total_tokens_out INTEGER NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_ai_sessions PRIMARY KEY (id), 
	CONSTRAINT fk_ai_sessions_student_id_students FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE CASCADE
);

CREATE INDEX ix_ai_sessions_student_id ON ai_sessions (student_id);

CREATE TABLE ai_recommendations (
	student_id UUID NOT NULL, 
	kind recommendation_kind NOT NULL, 
	target_id UUID, 
	reason TEXT NOT NULL, 
	confidence FLOAT, 
	source recommendation_source NOT NULL, 
	generated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	acted_on_at TIMESTAMP WITH TIME ZONE, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_ai_recommendations PRIMARY KEY (id), 
	CONSTRAINT fk_ai_recommendations_student_id_students FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE CASCADE
);

CREATE INDEX ix_ai_recommendations_student_id ON ai_recommendations (student_id);

CREATE TABLE ml_feature_snapshots (
	student_id UUID NOT NULL, 
	snapshot_date DATE NOT NULL, 
	features JSONB NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_ml_feature_snapshots PRIMARY KEY (id), 
	CONSTRAINT uq_ml_feature_snapshots_student_id_snapshot_date UNIQUE (student_id, snapshot_date), 
	CONSTRAINT fk_ml_feature_snapshots_student_id_students FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE CASCADE
);

CREATE INDEX ix_ml_feature_snapshots_snapshot_date ON ml_feature_snapshots (snapshot_date);

CREATE INDEX ix_ml_feature_snapshots_student_id ON ml_feature_snapshots (student_id);

CREATE TABLE ml_predictions (
	student_id UUID NOT NULL, 
	model_id UUID, 
	task ml_task NOT NULL, 
	predicted_value FLOAT, 
	probability FLOAT, 
	explanation JSONB, 
	is_heuristic BOOLEAN NOT NULL, 
	generated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_ml_predictions PRIMARY KEY (id), 
	CONSTRAINT fk_ml_predictions_student_id_students FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE CASCADE, 
	CONSTRAINT fk_ml_predictions_model_id_ml_models FOREIGN KEY(model_id) REFERENCES ml_models (id) ON DELETE SET NULL
);

CREATE INDEX ix_ml_predictions_student_id ON ml_predictions (student_id);

CREATE TABLE topics (
	chapter_id UUID NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	sequence INTEGER NOT NULL, 
	difficulty_hint difficulty, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_topics PRIMARY KEY (id), 
	CONSTRAINT uq_topics_chapter_id_name UNIQUE (chapter_id, name), 
	CONSTRAINT fk_topics_chapter_id_chapters FOREIGN KEY(chapter_id) REFERENCES chapters (id) ON DELETE CASCADE
);

CREATE INDEX ix_topics_chapter_id ON topics (chapter_id);

CREATE TABLE student_parents (
	student_id UUID NOT NULL, 
	parent_id UUID NOT NULL, 
	relationship_type VARCHAR(20) NOT NULL, 
	is_primary BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_student_parents PRIMARY KEY (student_id, parent_id), 
	CONSTRAINT uq_student_parents_student_id_parent_id UNIQUE (student_id, parent_id), 
	CONSTRAINT fk_student_parents_student_id_students FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE CASCADE, 
	CONSTRAINT fk_student_parents_parent_id_parents FOREIGN KEY(parent_id) REFERENCES parents (id) ON DELETE CASCADE
);

CREATE TABLE conversations (
	conversation_type conversation_type NOT NULL, 
	student_id UUID NOT NULL, 
	subject_line VARCHAR(200), 
	last_message_at TIMESTAMP WITH TIME ZONE, 
	is_archived BOOLEAN NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_conversations PRIMARY KEY (id), 
	CONSTRAINT fk_conversations_student_id_students FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE CASCADE
);

CREATE INDEX ix_conversations_student_id ON conversations (student_id);

CREATE INDEX ix_conversations_last_message_at ON conversations (last_message_at);

CREATE TABLE consent_records (
	student_id UUID NOT NULL, 
	parent_id UUID, 
	consent_type consent_type NOT NULL, 
	granted BOOLEAN NOT NULL, 
	granted_at TIMESTAMP WITH TIME ZONE, 
	revoked_at TIMESTAMP WITH TIME ZONE, 
	evidence_note TEXT, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_consent_records PRIMARY KEY (id), 
	CONSTRAINT fk_consent_records_student_id_students FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE CASCADE, 
	CONSTRAINT fk_consent_records_parent_id_parents FOREIGN KEY(parent_id) REFERENCES parents (id) ON DELETE SET NULL
);

CREATE INDEX ix_consent_records_student_id ON consent_records (student_id);

CREATE TABLE batch_students (
	batch_id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	enrolled_on DATE NOT NULL, 
	left_on DATE, 
	status enrolment_status NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_batch_students PRIMARY KEY (batch_id, student_id), 
	CONSTRAINT uq_batch_students_batch_id_student_id UNIQUE (batch_id, student_id), 
	CONSTRAINT fk_batch_students_batch_id_batches FOREIGN KEY(batch_id) REFERENCES batches (id) ON DELETE CASCADE, 
	CONSTRAINT fk_batch_students_student_id_students FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE CASCADE
);

CREATE TABLE tutor_assignments (
	tutor_id UUID NOT NULL, 
	batch_id UUID NOT NULL, 
	subject_id UUID NOT NULL, 
	assigned_on DATE NOT NULL, 
	revoked_on DATE, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_tutor_assignments PRIMARY KEY (id), 
	CONSTRAINT uq_tutor_assignments_tutor_id_batch_id_subject_id UNIQUE (tutor_id, batch_id, subject_id), 
	CONSTRAINT fk_tutor_assignments_tutor_id_tutors FOREIGN KEY(tutor_id) REFERENCES tutors (id) ON DELETE CASCADE, 
	CONSTRAINT fk_tutor_assignments_batch_id_batches FOREIGN KEY(batch_id) REFERENCES batches (id) ON DELETE CASCADE, 
	CONSTRAINT fk_tutor_assignments_subject_id_subjects FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE RESTRICT
);

CREATE INDEX ix_tutor_assignments_tutor_id ON tutor_assignments (tutor_id);

CREATE INDEX ix_tutor_assignments_batch_id ON tutor_assignments (batch_id);

CREATE TABLE ai_messages (
	session_id UUID NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	content TEXT NOT NULL, 
	model VARCHAR(80), 
	tokens_in INTEGER, 
	tokens_out INTEGER, 
	is_flagged BOOLEAN NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_ai_messages PRIMARY KEY (id), 
	CONSTRAINT fk_ai_messages_session_id_ai_sessions FOREIGN KEY(session_id) REFERENCES ai_sessions (id) ON DELETE CASCADE
);

CREATE INDEX ix_ai_messages_session_id ON ai_messages (session_id);

CREATE TABLE questions (
	subject_id UUID NOT NULL, 
	chapter_id UUID, 
	topic_id UUID, 
	question_type question_type NOT NULL, 
	stem TEXT NOT NULL, 
	difficulty difficulty NOT NULL, 
	marks NUMERIC(6, 2) NOT NULL, 
	negative_marks NUMERIC(6, 2) NOT NULL, 
	solution_text TEXT, 
	source question_source NOT NULL, 
	ai_model VARCHAR(80), 
	review_status review_status NOT NULL, 
	reviewed_by UUID, 
	reviewed_at TIMESTAMP WITH TIME ZONE, 
	created_by UUID NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_questions PRIMARY KEY (id), 
	CONSTRAINT fk_questions_subject_id_subjects FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_questions_chapter_id_chapters FOREIGN KEY(chapter_id) REFERENCES chapters (id) ON DELETE SET NULL, 
	CONSTRAINT fk_questions_topic_id_topics FOREIGN KEY(topic_id) REFERENCES topics (id) ON DELETE SET NULL, 
	CONSTRAINT fk_questions_reviewed_by_users FOREIGN KEY(reviewed_by) REFERENCES users (id) ON DELETE SET NULL, 
	CONSTRAINT fk_questions_created_by_users FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_questions_topic_id ON questions (topic_id);

CREATE INDEX ix_questions_review_status ON questions (review_status);

CREATE TABLE tests (
	title VARCHAR(300) NOT NULL, 
	test_type test_type NOT NULL, 
	exam_id UUID, 
	grade grade, 
	subject_id UUID, 
	chapter_id UUID, 
	topic_id UUID, 
	difficulty difficulty, 
	duration_minutes INTEGER NOT NULL, 
	total_marks NUMERIC(8, 2) NOT NULL, 
	negative_marking_ratio NUMERIC(4, 3) NOT NULL, 
	available_from TIMESTAMP WITH TIME ZONE, 
	available_until TIMESTAMP WITH TIME ZONE, 
	is_published BOOLEAN NOT NULL, 
	created_by UUID NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_tests PRIMARY KEY (id), 
	CONSTRAINT ck_tests_duration_positive CHECK (duration_minutes > 0), 
	CONSTRAINT ck_tests_availability_window_valid CHECK (available_until IS NULL OR available_from IS NULL OR available_until > available_from), 
	CONSTRAINT fk_tests_exam_id_exams FOREIGN KEY(exam_id) REFERENCES exams (id) ON DELETE SET NULL, 
	CONSTRAINT fk_tests_subject_id_subjects FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE SET NULL, 
	CONSTRAINT fk_tests_chapter_id_chapters FOREIGN KEY(chapter_id) REFERENCES chapters (id) ON DELETE SET NULL, 
	CONSTRAINT fk_tests_topic_id_topics FOREIGN KEY(topic_id) REFERENCES topics (id) ON DELETE SET NULL, 
	CONSTRAINT fk_tests_created_by_users FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE TABLE student_topic_performance (
	student_id UUID NOT NULL, 
	topic_id UUID NOT NULL, 
	questions_attempted INTEGER NOT NULL, 
	questions_correct INTEGER NOT NULL, 
	accuracy_pct FLOAT, 
	avg_time_seconds FLOAT, 
	mastery_level VARCHAR(20), 
	last_attempted_at TIMESTAMP WITH TIME ZONE, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_student_topic_performance PRIMARY KEY (id), 
	CONSTRAINT uq_student_topic_performance_student_id_topic_id UNIQUE (student_id, topic_id), 
	CONSTRAINT fk_student_topic_performance_student_id_students FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE CASCADE, 
	CONSTRAINT fk_student_topic_performance_topic_id_topics FOREIGN KEY(topic_id) REFERENCES topics (id) ON DELETE CASCADE
);

CREATE INDEX ix_student_topic_performance_student_id ON student_topic_performance (student_id);

CREATE TABLE content_items (
	title VARCHAR(300) NOT NULL, 
	content_type content_type NOT NULL, 
	description TEXT, 
	exam_id UUID, 
	grade grade, 
	subject_id UUID, 
	chapter_id UUID, 
	topic_id UUID, 
	file_id UUID, 
	created_by UUID NOT NULL, 
	is_published BOOLEAN NOT NULL, 
	published_at TIMESTAMP WITH TIME ZONE, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_content_items PRIMARY KEY (id), 
	CONSTRAINT fk_content_items_exam_id_exams FOREIGN KEY(exam_id) REFERENCES exams (id) ON DELETE SET NULL, 
	CONSTRAINT fk_content_items_subject_id_subjects FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE SET NULL, 
	CONSTRAINT fk_content_items_chapter_id_chapters FOREIGN KEY(chapter_id) REFERENCES chapters (id) ON DELETE SET NULL, 
	CONSTRAINT fk_content_items_topic_id_topics FOREIGN KEY(topic_id) REFERENCES topics (id) ON DELETE SET NULL, 
	CONSTRAINT fk_content_items_file_id_files FOREIGN KEY(file_id) REFERENCES files (id) ON DELETE SET NULL, 
	CONSTRAINT fk_content_items_created_by_users FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_content_items_content_type ON content_items (content_type);

CREATE INDEX ix_content_items_topic_id ON content_items (topic_id);

CREATE TABLE invoices (
	student_id UUID NOT NULL, 
	fee_plan_id UUID, 
	period_start DATE NOT NULL, 
	period_end DATE NOT NULL, 
	amount_due INTEGER NOT NULL, 
	discount INTEGER NOT NULL, 
	amount_payable INTEGER NOT NULL, 
	due_date DATE NOT NULL, 
	status invoice_status NOT NULL, 
	issued_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	note TEXT, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_invoices PRIMARY KEY (id), 
	CONSTRAINT ck_invoices_amount_due_non_negative CHECK (amount_due >= 0), 
	CONSTRAINT ck_invoices_discount_non_negative CHECK (discount >= 0), 
	CONSTRAINT ck_invoices_amount_payable_non_negative CHECK (amount_payable >= 0), 
	CONSTRAINT ck_invoices_period_valid CHECK (period_end >= period_start), 
	CONSTRAINT fk_invoices_student_id_students FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_invoices_fee_plan_id_fee_plans FOREIGN KEY(fee_plan_id) REFERENCES fee_plans (id) ON DELETE SET NULL
);

CREATE INDEX ix_invoices_status ON invoices (status);

CREATE INDEX ix_invoices_student_id ON invoices (student_id);

CREATE INDEX ix_invoices_due_date ON invoices (due_date);

CREATE TABLE conversation_members (
	conversation_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	last_read_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_conversation_members PRIMARY KEY (conversation_id, user_id), 
	CONSTRAINT uq_conversation_members_conversation_id_user_id UNIQUE (conversation_id, user_id), 
	CONSTRAINT fk_conversation_members_conversation_id_conversations FOREIGN KEY(conversation_id) REFERENCES conversations (id) ON DELETE CASCADE, 
	CONSTRAINT fk_conversation_members_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE messages (
	conversation_id UUID NOT NULL, 
	sender_user_id UUID NOT NULL, 
	body TEXT NOT NULL, 
	sent_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	edited_at TIMESTAMP WITH TIME ZONE, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_messages PRIMARY KEY (id), 
	CONSTRAINT fk_messages_conversation_id_conversations FOREIGN KEY(conversation_id) REFERENCES conversations (id) ON DELETE CASCADE, 
	CONSTRAINT fk_messages_sender_user_id_users FOREIGN KEY(sender_user_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_messages_sent_at ON messages (sent_at);

CREATE INDEX ix_messages_conversation_id ON messages (conversation_id);

CREATE TABLE class_sessions (
	batch_id UUID NOT NULL, 
	tutor_id UUID NOT NULL, 
	subject_id UUID NOT NULL, 
	scheduled_date DATE NOT NULL, 
	scheduled_start TIME WITHOUT TIME ZONE NOT NULL, 
	scheduled_end TIME WITHOUT TIME ZONE NOT NULL, 
	status class_session_status NOT NULL, 
	integration_status meeting_integration_status NOT NULL, 
	meeting_url VARCHAR(500), 
	google_event_id VARCHAR(200), 
	google_conference_id VARCHAR(200), 
	created_by UUID NOT NULL, 
	cancellation_reason TEXT, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_class_sessions PRIMARY KEY (id), 
	CONSTRAINT fk_class_sessions_batch_id_batches FOREIGN KEY(batch_id) REFERENCES batches (id) ON DELETE CASCADE, 
	CONSTRAINT fk_class_sessions_tutor_id_tutors FOREIGN KEY(tutor_id) REFERENCES tutors (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_class_sessions_subject_id_subjects FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_class_sessions_created_by_users FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_class_sessions_tutor_id ON class_sessions (tutor_id);

CREATE INDEX ix_class_sessions_scheduled_date ON class_sessions (scheduled_date);

CREATE INDEX ix_class_sessions_batch_id ON class_sessions (batch_id);

CREATE TABLE document_chunks (
	content_item_id UUID NOT NULL, 
	chunk_index INTEGER NOT NULL, 
	chunk_text TEXT NOT NULL, 
	token_count INTEGER, 
	embedding VECTOR(1024), 
	exam_id UUID, 
	grade grade, 
	subject_id UUID, 
	topic_id UUID, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_document_chunks PRIMARY KEY (id), 
	CONSTRAINT uq_document_chunks_content_item_id_chunk_index UNIQUE (content_item_id, chunk_index), 
	CONSTRAINT fk_document_chunks_content_item_id_content_items FOREIGN KEY(content_item_id) REFERENCES content_items (id) ON DELETE CASCADE, 
	CONSTRAINT fk_document_chunks_exam_id_exams FOREIGN KEY(exam_id) REFERENCES exams (id) ON DELETE SET NULL, 
	CONSTRAINT fk_document_chunks_subject_id_subjects FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE SET NULL, 
	CONSTRAINT fk_document_chunks_topic_id_topics FOREIGN KEY(topic_id) REFERENCES topics (id) ON DELETE SET NULL
);

CREATE INDEX ix_document_chunks_exam_id ON document_chunks (exam_id);

CREATE INDEX ix_document_chunks_content_item_id ON document_chunks (content_item_id);

CREATE INDEX ix_document_chunks_grade ON document_chunks (grade);

CREATE INDEX ix_document_chunks_subject_id ON document_chunks (subject_id);

CREATE TABLE question_options (
	question_id UUID NOT NULL, 
	label VARCHAR(5) NOT NULL, 
	body TEXT NOT NULL, 
	is_correct BOOLEAN NOT NULL, 
	sequence INTEGER NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_question_options PRIMARY KEY (id), 
	CONSTRAINT fk_question_options_question_id_questions FOREIGN KEY(question_id) REFERENCES questions (id) ON DELETE CASCADE
);

CREATE INDEX ix_question_options_question_id ON question_options (question_id);

CREATE TABLE question_numeric_answers (
	question_id UUID NOT NULL, 
	correct_value NUMERIC(18, 6) NOT NULL, 
	tolerance NUMERIC(18, 6) NOT NULL, 
	unit VARCHAR(30), 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_question_numeric_answers PRIMARY KEY (id), 
	CONSTRAINT uq_question_numeric_answers_question_id UNIQUE (question_id), 
	CONSTRAINT fk_question_numeric_answers_question_id_questions FOREIGN KEY(question_id) REFERENCES questions (id) ON DELETE CASCADE
);

CREATE TABLE test_questions (
	test_id UUID NOT NULL, 
	question_id UUID NOT NULL, 
	sequence INTEGER NOT NULL, 
	marks_override NUMERIC(6, 2), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_test_questions PRIMARY KEY (test_id, question_id), 
	CONSTRAINT fk_test_questions_test_id_tests FOREIGN KEY(test_id) REFERENCES tests (id) ON DELETE CASCADE, 
	CONSTRAINT fk_test_questions_question_id_questions FOREIGN KEY(question_id) REFERENCES questions (id) ON DELETE RESTRICT
);

CREATE TABLE test_attempts (
	test_id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	submitted_at TIMESTAMP WITH TIME ZONE, 
	status attempt_status NOT NULL, 
	score NUMERIC(8, 2), 
	max_score NUMERIC(8, 2), 
	accuracy_pct FLOAT, 
	time_taken_seconds INTEGER, 
	is_auto_submitted BOOLEAN NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_test_attempts PRIMARY KEY (id), 
	CONSTRAINT fk_test_attempts_test_id_tests FOREIGN KEY(test_id) REFERENCES tests (id) ON DELETE CASCADE, 
	CONSTRAINT fk_test_attempts_student_id_students FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE CASCADE
);

CREATE INDEX ix_test_attempts_student_id ON test_attempts (student_id);

CREATE INDEX ix_test_attempts_test_id ON test_attempts (test_id);

CREATE TABLE content_access_rules (
	content_item_id UUID NOT NULL, 
	scope_type access_scope_type NOT NULL, 
	scope_id UUID, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_content_access_rules PRIMARY KEY (id), 
	CONSTRAINT fk_content_access_rules_content_item_id_content_items FOREIGN KEY(content_item_id) REFERENCES content_items (id) ON DELETE CASCADE
);

CREATE INDEX ix_content_access_rules_content_item_id ON content_access_rules (content_item_id);

CREATE TABLE payment_submissions (
	invoice_id UUID NOT NULL, 
	submitted_by UUID NOT NULL, 
	method payment_method NOT NULL, 
	reference_id VARCHAR(120), 
	amount_claimed INTEGER NOT NULL, 
	proof_file_id UUID, 
	note TEXT, 
	status submission_status NOT NULL, 
	submitted_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	reviewed_by UUID, 
	reviewed_at TIMESTAMP WITH TIME ZONE, 
	rejection_reason TEXT, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_payment_submissions PRIMARY KEY (id), 
	CONSTRAINT ck_payment_submissions_amount_claimed_positive CHECK (amount_claimed > 0), 
	CONSTRAINT fk_payment_submissions_invoice_id_invoices FOREIGN KEY(invoice_id) REFERENCES invoices (id) ON DELETE CASCADE, 
	CONSTRAINT fk_payment_submissions_submitted_by_users FOREIGN KEY(submitted_by) REFERENCES users (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_payment_submissions_proof_file_id_files FOREIGN KEY(proof_file_id) REFERENCES files (id) ON DELETE SET NULL, 
	CONSTRAINT fk_payment_submissions_reviewed_by_users FOREIGN KEY(reviewed_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_payment_submissions_invoice_id ON payment_submissions (invoice_id);

CREATE INDEX ix_payment_submissions_status ON payment_submissions (status);

CREATE TABLE message_attachments (
	message_id UUID NOT NULL, 
	file_id UUID NOT NULL, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_message_attachments PRIMARY KEY (id), 
	CONSTRAINT fk_message_attachments_message_id_messages FOREIGN KEY(message_id) REFERENCES messages (id) ON DELETE CASCADE, 
	CONSTRAINT fk_message_attachments_file_id_files FOREIGN KEY(file_id) REFERENCES files (id) ON DELETE RESTRICT
);

CREATE INDEX ix_message_attachments_message_id ON message_attachments (message_id);

CREATE TABLE class_reports (
	class_session_id UUID NOT NULL, 
	tutor_id UUID NOT NULL, 
	subject_id UUID NOT NULL, 
	topics_covered TEXT NOT NULL, 
	actual_start_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	actual_end_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	homework_assigned TEXT, 
	notes TEXT, 
	status class_report_status NOT NULL, 
	submitted_at TIMESTAMP WITH TIME ZONE, 
	reviewed_by UUID, 
	reviewed_at TIMESTAMP WITH TIME ZONE, 
	shared_with_parents_at TIMESTAMP WITH TIME ZONE, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_class_reports PRIMARY KEY (id), 
	CONSTRAINT uq_class_reports_class_session_id UNIQUE (class_session_id), 
	CONSTRAINT fk_class_reports_class_session_id_class_sessions FOREIGN KEY(class_session_id) REFERENCES class_sessions (id) ON DELETE CASCADE, 
	CONSTRAINT fk_class_reports_tutor_id_tutors FOREIGN KEY(tutor_id) REFERENCES tutors (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_class_reports_subject_id_subjects FOREIGN KEY(subject_id) REFERENCES subjects (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_class_reports_reviewed_by_users FOREIGN KEY(reviewed_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_class_reports_tutor_id ON class_reports (tutor_id);

CREATE TABLE attendance (
	class_session_id UUID NOT NULL, 
	student_id UUID NOT NULL, 
	student_marked_status attendance_mark, 
	student_marked_at TIMESTAMP WITH TIME ZONE, 
	tutor_marked_status attendance_mark, 
	tutor_marked_at TIMESTAMP WITH TIME ZONE, 
	final_status attendance_mark, 
	has_discrepancy BOOLEAN NOT NULL, 
	resolved_by UUID, 
	resolved_at TIMESTAMP WITH TIME ZONE, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_attendance PRIMARY KEY (id), 
	CONSTRAINT uq_attendance_class_session_id_student_id UNIQUE (class_session_id, student_id), 
	CONSTRAINT fk_attendance_class_session_id_class_sessions FOREIGN KEY(class_session_id) REFERENCES class_sessions (id) ON DELETE CASCADE, 
	CONSTRAINT fk_attendance_student_id_students FOREIGN KEY(student_id) REFERENCES students (id) ON DELETE CASCADE, 
	CONSTRAINT fk_attendance_resolved_by_users FOREIGN KEY(resolved_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_attendance_student_id ON attendance (student_id);

CREATE INDEX ix_attendance_has_discrepancy ON attendance (has_discrepancy);

CREATE INDEX ix_attendance_class_session_id ON attendance (class_session_id);

CREATE TABLE test_answers (
	attempt_id UUID NOT NULL, 
	question_id UUID NOT NULL, 
	selected_option_ids UUID[], 
	numeric_answer NUMERIC(18, 6), 
	text_answer TEXT, 
	is_correct BOOLEAN, 
	marks_awarded NUMERIC(6, 2), 
	time_spent_seconds INTEGER, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_test_answers PRIMARY KEY (id), 
	CONSTRAINT uq_test_answers_attempt_id_question_id UNIQUE (attempt_id, question_id), 
	CONSTRAINT fk_test_answers_attempt_id_test_attempts FOREIGN KEY(attempt_id) REFERENCES test_attempts (id) ON DELETE CASCADE, 
	CONSTRAINT fk_test_answers_question_id_questions FOREIGN KEY(question_id) REFERENCES questions (id) ON DELETE RESTRICT
);

CREATE INDEX ix_test_answers_attempt_id ON test_answers (attempt_id);

CREATE TABLE payments (
	invoice_id UUID NOT NULL, 
	submission_id UUID, 
	amount INTEGER NOT NULL, 
	method payment_method NOT NULL, 
	reference_id VARCHAR(120), 
	received_on DATE NOT NULL, 
	recorded_by UUID NOT NULL, 
	note TEXT, 
	id UUID DEFAULT gen_random_uuid() NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	CONSTRAINT pk_payments PRIMARY KEY (id), 
	CONSTRAINT ck_payments_amount_positive CHECK (amount > 0), 
	CONSTRAINT fk_payments_invoice_id_invoices FOREIGN KEY(invoice_id) REFERENCES invoices (id) ON DELETE RESTRICT, 
	CONSTRAINT fk_payments_submission_id_payment_submissions FOREIGN KEY(submission_id) REFERENCES payment_submissions (id) ON DELETE SET NULL, 
	CONSTRAINT fk_payments_recorded_by_users FOREIGN KEY(recorded_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX ix_payments_invoice_id ON payments (invoice_id);


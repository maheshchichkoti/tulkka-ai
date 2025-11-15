-- ============================================================================
-- Tulkka AI - Complete MySQL Schema
-- Production-ready database schema for all game types and lesson content
-- ============================================================================

-- ============================================================================
-- WORD LISTS & FLASHCARDS
-- ============================================================================

CREATE TABLE IF NOT EXISTS word_lists (
    id              VARCHAR(36) PRIMARY KEY,
    user_id         VARCHAR(36) NOT NULL,
    name            VARCHAR(120) NOT NULL,
    description     TEXT,
    is_favorite     TINYINT(1) DEFAULT 0,
    word_count      INT DEFAULT 0,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_user_favorite (user_id, is_favorite)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS words (
    id              VARCHAR(36) PRIMARY KEY,
    list_id         VARCHAR(36) NOT NULL,
    word            VARCHAR(120) NOT NULL,
    translation     VARCHAR(240) NOT NULL,
    notes           TEXT,
    difficulty      ENUM('beginner','intermediate','advanced') DEFAULT 'beginner',
    is_favorite     TINYINT(1) DEFAULT 0,
    practice_count  INT DEFAULT 0,
    correct_count   INT DEFAULT 0,
    accuracy        INT DEFAULT 0,
    last_practiced  DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_list_id (list_id),
    INDEX idx_word (word),
    CONSTRAINT fk_words_word_lists FOREIGN KEY(list_id) REFERENCES word_lists(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS flashcard_sessions (
    id                VARCHAR(36) PRIMARY KEY,
    user_id           VARCHAR(36) NOT NULL,
    list_id           VARCHAR(36) NOT NULL,
    started_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at      DATETIME,
    progress_current  INT DEFAULT 0,
    progress_total    INT DEFAULT 0,
    correct           INT DEFAULT 0,
    incorrect         INT DEFAULT 0,
    status            ENUM('in_progress','completed') DEFAULT 'in_progress',
    INDEX idx_user_id (user_id),
    INDEX idx_list_id (list_id),
    INDEX idx_status (status),
    CONSTRAINT fk_flashcard_sessions_word_lists FOREIGN KEY(list_id) REFERENCES word_lists(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS flashcard_results (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id      VARCHAR(36) NOT NULL,
    word_id         VARCHAR(36) NOT NULL,
    is_correct      TINYINT(1) NOT NULL,
    attempts        INT DEFAULT 1,
    time_spent_ms   INT DEFAULT 0,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    INDEX idx_word_id (word_id),
    CONSTRAINT fk_flashcard_results_sessions FOREIGN KEY(session_id) REFERENCES flashcard_sessions(id) ON DELETE CASCADE,
    CONSTRAINT fk_flashcard_results_words FOREIGN KEY(word_id) REFERENCES words(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- GAME SESSIONS (All game types)
-- ============================================================================

CREATE TABLE IF NOT EXISTS game_sessions (
    id              VARCHAR(36) PRIMARY KEY,
    user_id         VARCHAR(36) NOT NULL,
    game_type       ENUM('flashcards','spelling_bee','advanced_cloze','grammar_challenge','sentence_builder') NOT NULL,
    lesson_id       VARCHAR(36),
    class_id        VARCHAR(36),
    started_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at    DATETIME,
    status          ENUM('in_progress','completed','abandoned') DEFAULT 'in_progress',
    progress_current INT DEFAULT 0,
    progress_total   INT DEFAULT 0,
    correct_count    INT DEFAULT 0,
    incorrect_count  INT DEFAULT 0,
    final_score      INT DEFAULT 0,
    time_spent_ms    INT DEFAULT 0,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_game_type (game_type),
    INDEX idx_lesson_id (lesson_id),
    INDEX idx_class_id (class_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS game_results (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id      VARCHAR(36) NOT NULL,
    prompt_id       VARCHAR(36),
    question_text   TEXT,
    user_answer     TEXT,
    correct_answer  TEXT,
    is_correct      TINYINT(1),
    attempts        INT DEFAULT 1,
    time_spent_ms   INT DEFAULT 0,
    answer_payload  JSON,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    INDEX idx_prompt_id (prompt_id),
    CONSTRAINT fk_game_results_sessions FOREIGN KEY(session_id) REFERENCES game_sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- USER MISTAKES & PROGRESS TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_mistakes (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id         VARCHAR(36) NOT NULL,
    game_type       ENUM('flashcards','spelling_bee','advanced_cloze','grammar_challenge','sentence_builder') NOT NULL,
    mistake_type    VARCHAR(50),
    incorrect_text  TEXT,
    correct_text    TEXT,
    context         TEXT,
    frequency       INT DEFAULT 1,
    last_occurred   DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_game_type (game_type),
    INDEX idx_mistake_type (mistake_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- LESSON CONTENT (Exercises generated from transcripts)
-- ============================================================================

CREATE TABLE IF NOT EXISTS lessons (
    id              VARCHAR(36) PRIMARY KEY,
    class_id        VARCHAR(36) NOT NULL,
    teacher_id      VARCHAR(36) NOT NULL,
    lesson_number   INT NOT NULL,
    lesson_date     DATE,
    transcript      LONGTEXT,
    transcript_length INT DEFAULT 0,
    status          ENUM('pending','processing','completed','failed') DEFAULT 'pending',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_class_id (class_id),
    INDEX idx_teacher_id (teacher_id),
    INDEX idx_status (status),
    UNIQUE KEY unique_class_lesson (class_id, lesson_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS lesson_exercises (
    id              VARCHAR(36) PRIMARY KEY,
    lesson_id       VARCHAR(36) NOT NULL,
    exercise_type   ENUM('flashcard','cloze','grammar','sentence','spelling') NOT NULL,
    exercise_data   JSON NOT NULL,
    difficulty      ENUM('beginner','intermediate','advanced') DEFAULT 'beginner',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_lesson_id (lesson_id),
    INDEX idx_exercise_type (exercise_type),
    CONSTRAINT fk_lesson_exercises_lessons FOREIGN KEY(lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- IDEMPOTENCY (For safe retries)
-- ============================================================================

CREATE TABLE IF NOT EXISTS idempotency_keys (
    id              VARCHAR(36) PRIMARY KEY,
    user_id         VARCHAR(36) NOT NULL,
    endpoint        VARCHAR(255) NOT NULL,
    idempotency_key VARCHAR(255) NOT NULL,
    response_data   JSON,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at      DATETIME,
    UNIQUE KEY unique_user_endpoint_key (user_id, endpoint, idempotency_key),
    INDEX idx_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- SPELLING GAME TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS spelling_sessions (
    id              VARCHAR(36) PRIMARY KEY,
    user_id         VARCHAR(36) NOT NULL,
    word_list_id    VARCHAR(36),
    started_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at    DATETIME,
    status          ENUM('active','completed','abandoned') DEFAULT 'active',
    correct_count   INT DEFAULT 0,
    incorrect_count INT DEFAULT 0,
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS spelling_results (
    id              VARCHAR(36) PRIMARY KEY,
    session_id      VARCHAR(36) NOT NULL,
    word_id         VARCHAR(36) NOT NULL,
    is_correct      TINYINT(1) NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    CONSTRAINT fk_spelling_results_sessions FOREIGN KEY(session_id) REFERENCES spelling_sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- CLOZE GAME TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS cloze_sessions (
    id              VARCHAR(36) PRIMARY KEY,
    user_id         VARCHAR(36) NOT NULL,
    class_id        VARCHAR(36),
    lesson_number   INT,
    started_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at    DATETIME,
    status          ENUM('active','completed','abandoned') DEFAULT 'active',
    correct_count   INT DEFAULT 0,
    incorrect_count INT DEFAULT 0,
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS cloze_results (
    id              VARCHAR(36) PRIMARY KEY,
    session_id      VARCHAR(36) NOT NULL,
    item_id         VARCHAR(36) NOT NULL,
    is_correct      TINYINT(1) NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    CONSTRAINT fk_cloze_results_sessions FOREIGN KEY(session_id) REFERENCES cloze_sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- GRAMMAR GAME TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS grammar_sessions (
    id              VARCHAR(36) PRIMARY KEY,
    user_id         VARCHAR(36) NOT NULL,
    class_id        VARCHAR(36),
    lesson_number   INT,
    started_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at    DATETIME,
    status          ENUM('active','completed','abandoned') DEFAULT 'active',
    correct_count   INT DEFAULT 0,
    incorrect_count INT DEFAULT 0,
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS grammar_results (
    id              VARCHAR(36) PRIMARY KEY,
    session_id      VARCHAR(36) NOT NULL,
    question_id     VARCHAR(36) NOT NULL,
    is_correct      TINYINT(1) NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    CONSTRAINT fk_grammar_results_sessions FOREIGN KEY(session_id) REFERENCES grammar_sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- SENTENCE BUILDER GAME TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS sentence_sessions (
    id              VARCHAR(36) PRIMARY KEY,
    user_id         VARCHAR(36) NOT NULL,
    class_id        VARCHAR(36),
    lesson_number   INT,
    started_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at    DATETIME,
    status          ENUM('active','completed','abandoned') DEFAULT 'active',
    correct_count   INT DEFAULT 0,
    incorrect_count INT DEFAULT 0,
    INDEX idx_user_id (user_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS sentence_results (
    id              VARCHAR(36) PRIMARY KEY,
    session_id      VARCHAR(36) NOT NULL,
    item_id         VARCHAR(36) NOT NULL,
    is_correct      TINYINT(1) NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    CONSTRAINT fk_sentence_results_sessions FOREIGN KEY(session_id) REFERENCES sentence_sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- SAMPLE DATA (Optional - for testing)
-- ============================================================================

-- Insert sample word list
INSERT IGNORE INTO word_lists (id, user_id, name, description, is_favorite, word_count) VALUES
('wl_sample_001', 'test-user-123', 'Basic Vocabulary', 'Common English words for beginners', 0, 5);

-- Insert sample words
INSERT IGNORE INTO words (id, list_id, word, translation, notes, difficulty, practice_count, correct_count, accuracy) VALUES
('w_sample_001', 'wl_sample_001', 'hello', 'مرحبا', 'Common greeting', 'beginner', 10, 8, 80),
('w_sample_002', 'wl_sample_001', 'goodbye', 'وداعا', 'Farewell', 'beginner', 8, 7, 88),
('w_sample_003', 'wl_sample_001', 'thank you', 'شكرا', 'Expression of gratitude', 'beginner', 12, 11, 92),
('w_sample_004', 'wl_sample_001', 'please', 'من فضلك', 'Polite request', 'beginner', 9, 8, 89),
('w_sample_005', 'wl_sample_001', 'excuse me', 'عفوا', 'Polite interruption', 'beginner', 7, 6, 86);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Additional composite indexes for common queries
CREATE INDEX idx_words_list_favorite ON words(list_id, is_favorite);
CREATE INDEX idx_game_sessions_user_type ON game_sessions(user_id, game_type);
CREATE INDEX idx_game_sessions_user_status ON game_sessions(user_id, status);
CREATE INDEX idx_flashcard_sessions_user_status ON flashcard_sessions(user_id, status);

-- ============================================================================
-- CLEANUP QUERIES (Run periodically)
-- ============================================================================

-- Delete expired idempotency keys (run daily)
-- DELETE FROM idempotency_keys WHERE expires_at < NOW();

-- Delete abandoned sessions older than 7 days
-- DELETE FROM game_sessions WHERE status = 'abandoned' AND created_at < DATE_SUB(NOW(), INTERVAL 7 DAY);

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check table structure
-- SHOW TABLES;
-- DESCRIBE word_lists;
-- DESCRIBE words;
-- DESCRIBE flashcard_sessions;
-- DESCRIBE game_sessions;

-- Check sample data
-- SELECT * FROM word_lists LIMIT 5;
-- SELECT * FROM words LIMIT 5;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================

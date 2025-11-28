-- ============================================================================
-- Tulkka AI - Clean 8-Table MySQL Schema
-- ============================================================================

-- ============================================================================  
-- TABLE 1: word_lists
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
    INDEX idx_user_favorite (user_id, is_favorite),
    INDEX idx_user_name (user_id, name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================  
-- TABLE 2: words
-- ============================================================================
CREATE TABLE IF NOT EXISTS words (
    id              VARCHAR(36) PRIMARY KEY,
    list_id         VARCHAR(36) NOT NULL,
    word            VARCHAR(120) NOT NULL,
    translation     VARCHAR(240) NOT NULL,
    notes           TEXT,
    is_favorite     TINYINT(1) DEFAULT 0,
    practice_count  INT DEFAULT 0,
    correct_count   INT DEFAULT 0,
    accuracy        INT DEFAULT 0,
    last_practiced  DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_list_id (list_id),
    INDEX idx_list_favorite (list_id, is_favorite),
    INDEX idx_word (word),
    CONSTRAINT fk_words_word_lists FOREIGN KEY (list_id) REFERENCES word_lists(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================  
-- TABLE 3: game_sessions
-- ============================================================================
CREATE TABLE IF NOT EXISTS game_sessions (
    id                  VARCHAR(36) PRIMARY KEY,
    user_id             VARCHAR(36) NOT NULL,
    game_type           ENUM('flashcards','spelling_bee','grammar_challenge','advanced_cloze','sentence_builder') NOT NULL,
    mode                VARCHAR(20) DEFAULT 'topic',
    word_list_id        VARCHAR(36),
    topic_id            VARCHAR(36),
    category_id         VARCHAR(36),
    lesson_id           VARCHAR(36),
    class_id            VARCHAR(36),
    difficulty          ENUM('easy','medium','hard'),
    item_order          JSON,
    progress_current    INT DEFAULT 0,
    progress_total      INT DEFAULT 0,
    correct_count       INT DEFAULT 0,
    incorrect_count     INT DEFAULT 0,
    mastered_ids        JSON DEFAULT ('[]'),
    needs_practice_ids  JSON DEFAULT ('[]'),
    started_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at        DATETIME,
    status              ENUM('active','completed','abandoned') DEFAULT 'active',
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_game_type (game_type),
    INDEX idx_user_game (user_id, game_type),
    INDEX idx_status (status),
    INDEX idx_word_list (word_list_id),
    INDEX idx_lesson (lesson_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================  
-- TABLE 4: game_results
-- ============================================================================
CREATE TABLE IF NOT EXISTS game_results (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id          VARCHAR(36) NOT NULL,
    item_id             VARCHAR(36) NOT NULL,
    client_result_id    VARCHAR(36),
    is_correct          TINYINT(1) NOT NULL,
    attempts            INT DEFAULT 1,
    time_spent_ms       INT DEFAULT 0,
    skipped             TINYINT(1) DEFAULT 0,
    user_answer         TEXT,
    selected_answer     INT,
    selected_answers    JSON,
    user_tokens         JSON,
    error_type          VARCHAR(50),
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_id (session_id),
    INDEX idx_item_id (item_id),
    CONSTRAINT fk_results_sessions FOREIGN KEY (session_id) REFERENCES game_sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================  
-- TABLE 5: user_mistakes
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_mistakes (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id             VARCHAR(36) NOT NULL,
    game_type           ENUM('flashcards','spelling_bee','grammar_challenge','advanced_cloze','sentence_builder') NOT NULL,
    item_id             VARCHAR(36) NOT NULL,
    user_answer         TEXT,
    correct_answer      TEXT,
    selected_answers    JSON,
    error_type          VARCHAR(50),
    mistake_count       INT DEFAULT 1,
    last_answered_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_game_item (user_id, game_type, item_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================  
-- TABLE 6: lessons
-- ============================================================================
CREATE TABLE IF NOT EXISTS lessons (
    id                  VARCHAR(36) PRIMARY KEY,
    class_id            VARCHAR(36) NOT NULL,
    teacher_id          VARCHAR(36) NOT NULL,
    student_id          VARCHAR(36),
    lesson_number       INT NOT NULL,
    title               VARCHAR(255),
    lesson_date         DATE,
    zoom_summary_id     VARCHAR(36),          -- Reference to Supabase zoom_summaries.id
    status              ENUM('pending','approved','rejected') DEFAULT 'pending',
    approved_at         DATETIME,
    approved_by         VARCHAR(36),
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_class_id (class_id),
    INDEX idx_teacher_id (teacher_id),
    INDEX idx_student_id (student_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================  
-- TABLE 7: lesson_exercises
-- ============================================================================
CREATE TABLE IF NOT EXISTS lesson_exercises (
    id                  VARCHAR(36) PRIMARY KEY,
    lesson_id           VARCHAR(36) NOT NULL,
    exercise_type       ENUM('flashcards','spelling_bee','grammar_challenge','advanced_cloze','sentence_builder') NOT NULL,
    topic_id            VARCHAR(50),
    topic_name          VARCHAR(100),
    exercise_data       JSON NOT NULL,           -- The actual exercise item (question, options, correct answer, etc.)
    difficulty          ENUM('easy','medium','hard') DEFAULT 'medium',
    hint                TEXT,
    explanation         TEXT,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_lesson_id (lesson_id),
    INDEX idx_exercise_type (exercise_type),
    INDEX idx_topic_id (topic_id),
    INDEX idx_difficulty (difficulty),
    CONSTRAINT fk_exercises_lessons FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================  
-- TABLE 8: idempotency_keys
-- ============================================================================
CREATE TABLE IF NOT EXISTS idempotency_keys (
    id                  VARCHAR(36) PRIMARY KEY,
    user_id             VARCHAR(36) NOT NULL,
    endpoint            VARCHAR(255) NOT NULL,
    idempotency_key     VARCHAR(255) NOT NULL,
    response_data       JSON,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at          DATETIME,
    UNIQUE KEY unique_user_endpoint_key (user_id, endpoint, idempotency_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

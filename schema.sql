-- ============================================================================
-- Tulkka AI - Clean 8-Table MySQL Schema
-- Production-ready database schema for TULKKA Games APIs
-- Matches: FLASHCARDS, SPELLING_BEE, GRAMMAR_CHALLENGE, ADVANCED_CLOZE, SENTENCE_BUILDER specs
-- ============================================================================

-- ============================================================================
-- TABLE 1: word_lists
-- Purpose: User-owned word lists (shared by Flashcards & Spelling Bee)
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
-- Purpose: Words within word lists with practice statistics
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
-- Purpose: Unified session storage for ALL game types
-- Supports: flashcards, spelling_bee, grammar_challenge, advanced_cloze, sentence_builder
-- ============================================================================

CREATE TABLE IF NOT EXISTS game_sessions (
    id                  VARCHAR(36) PRIMARY KEY,
    user_id             VARCHAR(36) NOT NULL,
    game_type           ENUM('flashcards', 'spelling_bee', 'grammar_challenge', 'advanced_cloze', 'sentence_builder') NOT NULL,
    
    -- Session mode (topic/lesson/custom/mistakes)
    mode                VARCHAR(20) DEFAULT 'topic',
    
    -- Reference IDs (nullable, depends on game type and mode)
    word_list_id        VARCHAR(36),                -- For flashcards/spelling
    topic_id            VARCHAR(36),                -- For grammar/cloze/sentence (topic mode)
    category_id         VARCHAR(36),                -- For grammar (category = topic)
    lesson_id           VARCHAR(36),                -- For lesson mode
    class_id            VARCHAR(36),                -- For class-based content
    
    -- Difficulty filter
    difficulty          ENUM('easy', 'medium', 'hard') DEFAULT NULL,
    
    -- Item order (JSON array of item IDs in practice order, supports shuffle)
    item_order          JSON,
    
    -- Progress tracking
    progress_current    INT DEFAULT 0,
    progress_total      INT DEFAULT 0,
    correct_count       INT DEFAULT 0,
    incorrect_count     INT DEFAULT 0,
    
    -- Mastery tracking (JSON arrays of item IDs)
    mastered_ids        JSON,
    needs_practice_ids  JSON,
    
    -- Timestamps
    started_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at        DATETIME,
    
    -- Status
    status              ENUM('active', 'completed', 'abandoned') DEFAULT 'active',
    
    -- Metadata
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_user_id (user_id),
    INDEX idx_game_type (game_type),
    INDEX idx_user_game (user_id, game_type),
    INDEX idx_user_status (user_id, status),
    INDEX idx_status (status),
    INDEX idx_word_list (word_list_id),
    INDEX idx_lesson (lesson_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE 4: game_results
-- Purpose: Unified per-item results for ALL game types
-- Stores: attempts, timeSpentMs, userAnswer, selectedAnswers, etc.
-- ============================================================================

CREATE TABLE IF NOT EXISTS game_results (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id          VARCHAR(36) NOT NULL,
    
    -- Item reference (word_id, question_id, item_id depending on game type)
    item_id             VARCHAR(36) NOT NULL,
    
    -- Client-provided deduplication key
    client_result_id    VARCHAR(36),
    
    -- Result data
    is_correct          TINYINT(1) NOT NULL,
    attempts            INT DEFAULT 1,
    time_spent_ms       INT DEFAULT 0,
    skipped             TINYINT(1) DEFAULT 0,
    
    -- Answer data (flexible for different game types)
    user_answer         TEXT,                       -- For spelling: typed answer
    selected_answer     INT,                        -- For grammar: selected option index
    selected_answers    JSON,                       -- For cloze: array of selected answers
    user_tokens         JSON,                       -- For sentence builder: array of tokens
    error_type          VARCHAR(50),                -- For sentence builder: word_order, missing_words, extra_words
    
    -- Timestamp
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_session_id (session_id),
    INDEX idx_item_id (item_id),
    INDEX idx_client_result (client_result_id),
    INDEX idx_session_item (session_id, item_id),
    CONSTRAINT fk_results_sessions FOREIGN KEY (session_id) REFERENCES game_sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE 5: user_mistakes
-- Purpose: Track user mistakes across all games for "mistakes mode"
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_mistakes (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id             VARCHAR(36) NOT NULL,
    game_type           ENUM('flashcards', 'spelling_bee', 'grammar_challenge', 'advanced_cloze', 'sentence_builder') NOT NULL,
    
    -- Item reference
    item_id             VARCHAR(36) NOT NULL,
    
    -- Mistake details
    user_answer         TEXT,                       -- What user answered
    correct_answer      TEXT,                       -- What was correct
    selected_answers    JSON,                       -- For multi-answer games
    error_type          VARCHAR(50),                -- For sentence builder
    
    -- Tracking
    mistake_count       INT DEFAULT 1,
    last_answered_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Timestamps
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- Unique constraint: one mistake record per user+game+item
    UNIQUE KEY unique_user_game_item (user_id, game_type, item_id),
    
    INDEX idx_user_id (user_id),
    INDEX idx_user_game (user_id, game_type),
    INDEX idx_game_type (game_type),
    INDEX idx_last_answered (last_answered_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE 6: lessons
-- Purpose: Lesson metadata from Zoom transcript processing
-- ============================================================================

CREATE TABLE IF NOT EXISTS lessons (
    id                  VARCHAR(36) PRIMARY KEY,
    class_id            VARCHAR(36) NOT NULL,
    teacher_id          VARCHAR(36) NOT NULL,
    lesson_number       INT NOT NULL,
    title               VARCHAR(255),
    lesson_date         DATE,
    transcript          LONGTEXT,
    transcript_length   INT DEFAULT 0,
    status              ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_class_id (class_id),
    INDEX idx_teacher_id (teacher_id),
    INDEX idx_status (status),
    INDEX idx_class_lesson (class_id, lesson_number),
    UNIQUE KEY unique_class_lesson (class_id, lesson_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE 7: lesson_exercises
-- Purpose: AI-generated exercises for all game types (JSON storage)
-- Stores: grammar questions, cloze items, sentence items, flashcard words
-- ============================================================================

CREATE TABLE IF NOT EXISTS lesson_exercises (
    id                  VARCHAR(36) PRIMARY KEY,
    lesson_id           VARCHAR(36) NOT NULL,
    
    -- Exercise type matches game types
    exercise_type       ENUM('flashcard', 'spelling', 'grammar', 'cloze', 'sentence') NOT NULL,
    
    -- Topic/Category for catalog organization
    topic_id            VARCHAR(50),
    topic_name          VARCHAR(100),
    
    -- Full exercise data as JSON (structure varies by type)
    -- Grammar: { prompt, options, correctIndex, explanation, category, difficulty }
    -- Cloze: { textParts, options, correct, explanation, topic, difficulty }
    -- Sentence: { english, translation, tokens, accepted, distractors, topic, difficulty }
    -- Flashcard/Spelling: { word, translation, notes }
    exercise_data       JSON NOT NULL,
    
    -- Difficulty level
    difficulty          ENUM('easy', 'medium', 'hard') DEFAULT 'medium',
    
    -- Hint text (optional, for grammar/cloze/sentence)
    hint                TEXT,
    
    -- Status for approval workflow
    status              ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_lesson_id (lesson_id),
    INDEX idx_exercise_type (exercise_type),
    INDEX idx_topic (topic_id),
    INDEX idx_difficulty (difficulty),
    INDEX idx_status (status),
    INDEX idx_type_topic (exercise_type, topic_id),
    INDEX idx_type_difficulty (exercise_type, difficulty),
    CONSTRAINT fk_exercises_lessons FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE 8: idempotency_keys
-- Purpose: Safe retries for POST operations
-- ============================================================================

CREATE TABLE IF NOT EXISTS idempotency_keys (
    id                  VARCHAR(36) PRIMARY KEY,
    user_id             VARCHAR(36) NOT NULL,
    endpoint            VARCHAR(255) NOT NULL,
    idempotency_key     VARCHAR(255) NOT NULL,
    response_data       JSON,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at          DATETIME,
    
    UNIQUE KEY unique_user_endpoint_key (user_id, endpoint, idempotency_key),
    INDEX idx_expires_at (expires_at),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- SAMPLE DATA (For testing)
-- ============================================================================

-- Sample word list
INSERT IGNORE INTO word_lists (id, user_id, name, description, is_favorite, word_count) VALUES
('wl_sample_001', 'test-user-123', 'Basic Vocabulary', 'Common English words for beginners', 0, 5);

-- Sample words
INSERT IGNORE INTO words (id, list_id, word, translation, notes, practice_count, correct_count, accuracy) VALUES
('w_sample_001', 'wl_sample_001', 'hello', 'مرحبا', 'Common greeting', 10, 8, 80),
('w_sample_002', 'wl_sample_001', 'goodbye', 'وداعا', 'Farewell', 8, 7, 88),
('w_sample_003', 'wl_sample_001', 'thank you', 'شكرا', 'Expression of gratitude', 12, 11, 92),
('w_sample_004', 'wl_sample_001', 'please', 'من فضلك', 'Polite request', 9, 8, 89),
('w_sample_005', 'wl_sample_001', 'excuse me', 'عفوا', 'Polite interruption', 7, 6, 86);

-- ============================================================================
-- CLEANUP QUERIES (Run periodically via cron)
-- ============================================================================

-- Delete expired idempotency keys (run daily)
-- DELETE FROM idempotency_keys WHERE expires_at < NOW();

-- Delete abandoned sessions older than 7 days
-- DELETE FROM game_sessions WHERE status = 'abandoned' AND created_at < DATE_SUB(NOW(), INTERVAL 7 DAY);

-- ============================================================================
-- SCHEMA SUMMARY
-- ============================================================================
-- Total Tables: 8
-- 
-- 1. word_lists      - User word lists (Flashcards, Spelling)
-- 2. words           - Words with practice stats
-- 3. game_sessions   - All game sessions (unified)
-- 4. game_results    - All per-item results (unified)
-- 5. user_mistakes   - Mistake tracking for "mistakes mode"
-- 6. lessons         - Lesson metadata from Zoom
-- 7. lesson_exercises - AI-generated exercises (JSON)
-- 8. idempotency_keys - Safe retries
--
-- This schema supports 100% of the TULKKA Games APIs specification.
-- ============================================================================

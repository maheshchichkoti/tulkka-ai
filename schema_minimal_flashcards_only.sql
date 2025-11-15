-- ============================================================================
-- Tulkka AI - MINIMAL Schema (Flashcards Only)
-- Matches the frontend UI: Word Lists → Words → Flashcard Practice
-- ============================================================================

-- ============================================================================
-- WORD LISTS & WORDS
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
    INDEX idx_list_favorite (list_id, is_favorite),
    CONSTRAINT fk_words_word_lists FOREIGN KEY(list_id) REFERENCES word_lists(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- FLASHCARD SESSIONS & RESULTS
-- ============================================================================

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
    INDEX idx_user_status (user_id, status),
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
-- CLEANUP QUERIES (Run periodically)
-- ============================================================================

-- Delete expired idempotency keys (run daily)
-- DELETE FROM idempotency_keys WHERE expires_at < NOW();

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check tables
-- SHOW TABLES;
-- DESCRIBE word_lists;
-- DESCRIBE words;
-- DESCRIBE flashcard_sessions;

-- Check sample data
-- SELECT * FROM word_lists;
-- SELECT * FROM words WHERE list_id = 'wl_sample_001';

-- ============================================================================
-- END OF MINIMAL SCHEMA - 5 TABLES TOTAL
-- ============================================================================

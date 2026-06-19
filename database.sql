-- ============================================================
-- SLeClear MIS - Sierra Leone Student Clearance & Finance MIS
-- Limkokwing University Sierra Leone
-- Database Schema + Sample Data
-- ============================================================

CREATE DATABASE IF NOT EXISTS sleclear_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE sleclear_db;

-- ============================================================
-- TABLE: users
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(50)  NOT NULL UNIQUE,
    password    VARCHAR(255) NOT NULL,
    full_name   VARCHAR(100) NOT NULL,
    role        ENUM('admin','finance','registry') NOT NULL DEFAULT 'registry',
    email       VARCHAR(100),
    is_active   TINYINT(1)   NOT NULL DEFAULT 1,
    last_login  DATETIME,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================================
-- TABLE: students
-- ============================================================
CREATE TABLE IF NOT EXISTS students (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    student_id      VARCHAR(20)  NOT NULL UNIQUE,
    full_name       VARCHAR(100) NOT NULL,
    gender          ENUM('Male','Female','Other') NOT NULL,
    department      VARCHAR(100) NOT NULL,
    programme       VARCHAR(100) NOT NULL,
    level           VARCHAR(20)  NOT NULL,
    phone           VARCHAR(20),
    email           VARCHAR(100),
    academic_year   VARCHAR(20)  NOT NULL,
    total_fee       DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    amount_paid     DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    balance         DECIMAL(12,2) GENERATED ALWAYS AS (total_fee - amount_paid) STORED,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================================
-- TABLE: payments
-- ============================================================
CREATE TABLE IF NOT EXISTS payments (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    payment_id      VARCHAR(20)  NOT NULL UNIQUE,
    student_id      VARCHAR(20)  NOT NULL,
    amount          DECIMAL(12,2) NOT NULL,
    semester        VARCHAR(30)  NOT NULL,
    payment_date    DATE         NOT NULL,
    payment_method  ENUM('Bank Transfer','Cash','Online','Cheque') NOT NULL DEFAULT 'Bank Transfer',
    status          ENUM('Verified','Pending','Rejected') NOT NULL DEFAULT 'Pending',
    reference_no    VARCHAR(50),
    recorded_by     INT,
    notes           TEXT,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_payment_student FOREIGN KEY (student_id) REFERENCES students(student_id) ON UPDATE CASCADE,
    CONSTRAINT fk_payment_user   FOREIGN KEY (recorded_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ============================================================
-- TABLE: clearances
-- ============================================================
CREATE TABLE IF NOT EXISTS clearances (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    student_id      VARCHAR(20)  NOT NULL UNIQUE,
    status          ENUM('Cleared','Not Cleared','Provisional') NOT NULL DEFAULT 'Not Cleared',
    cleared_by      INT,
    cleared_date    DATETIME,
    valid_until     DATE,
    notes           TEXT,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_clearance_student FOREIGN KEY (student_id) REFERENCES students(student_id) ON UPDATE CASCADE,
    CONSTRAINT fk_clearance_user    FOREIGN KEY (cleared_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ============================================================
-- TABLE: deferred_assessments
-- ============================================================
CREATE TABLE IF NOT EXISTS deferred_assessments (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    student_id      VARCHAR(20)  NOT NULL,
    course_code     VARCHAR(20)  NOT NULL,
    course_name     VARCHAR(100) NOT NULL,
    semester        VARCHAR(30)  NOT NULL,
    reason          TEXT         NOT NULL,
    supporting_doc  VARCHAR(255),
    status          ENUM('Pending','Approved','Rejected') NOT NULL DEFAULT 'Pending',
    reviewed_by     INT,
    review_date     DATETIME,
    review_notes    TEXT,
    submitted_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_deferred_student FOREIGN KEY (student_id) REFERENCES students(student_id) ON UPDATE CASCADE,
    CONSTRAINT fk_deferred_user    FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ============================================================
-- TABLE: activity_log
-- ============================================================
CREATE TABLE IF NOT EXISTS activity_log (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT,
    action      VARCHAR(255) NOT NULL,
    module      VARCHAR(50),
    ip_address  VARCHAR(45),
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_log_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ============================================================
-- SAMPLE DATA: users  (passwords are bcrypt hashes for XAMPP)
-- Plain passwords: admin123 | finance123 | registry123
-- ============================================================
INSERT INTO users (username, password, full_name, role, email) VALUES
('admin',    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/lewFZ.QL1wKxf8kTC', 'System Administrator',  'admin',    'admin@limkokwing.sl'),
('finance',  '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'Finance Officer Kamara','finance',  'finance@limkokwing.sl'),
('registry', '$2b$12$YhNkS5qCvJd4wSz0j3gBnOqMvIY.1mRJJrZvKVsXXqQk2IxKnZRQi','Registry Officer Sesay','registry', 'registry@limkokwing.sl');

-- ============================================================
-- SAMPLE DATA: students
-- ============================================================
INSERT INTO students (student_id, full_name, gender, department, programme, level, phone, email, academic_year, total_fee, amount_paid) VALUES
('LU/SL/001', 'Mohamed Koroma',       'Male',   'Computing',           'BSc Computer Science',     'Level 3', '+232 76 123456', 'mkoroma@student.lu.sl',   '2024/2025', 8500.00, 8500.00),
('LU/SL/002', 'Fatima Sesay',         'Female', 'Business',            'BA Business Administration','Level 2', '+232 77 234567', 'fsesay@student.lu.sl',    '2024/2025', 7800.00, 5000.00),
('LU/SL/003', 'Alusine Kamara',       'Male',   'Design',              'BSc Graphic Design',       'Level 1', '+232 78 345678', 'akamara@student.lu.sl',   '2024/2025', 7200.00, 7200.00),
('LU/SL/004', 'Isatu Bangura',        'Female', 'Computing',           'BSc Information Technology','Level 4', '+232 79 456789', 'ibangura@student.lu.sl',  '2024/2025', 9000.00, 3500.00),
('LU/SL/005', 'Samuel Conteh',        'Male',   'Media',               'BA Mass Communication',    'Level 2', '+232 76 567890', 'sconteh@student.lu.sl',   '2024/2025', 7500.00, 7500.00),
('LU/SL/006', 'Mariama Turay',        'Female', 'Business',            'BSc Accounting & Finance', 'Level 3', '+232 77 678901', 'mturay@student.lu.sl',    '2024/2025', 8200.00, 8200.00),
('LU/SL/007', 'Ibrahim Fofana',       'Male',   'Engineering',         'BEng Civil Engineering',   'Level 1', '+232 78 789012', 'iffofana@student.lu.sl',  '2024/2025', 9500.00, 2000.00),
('LU/SL/008', 'Adama Jalloh',         'Male',   'Computing',           'BSc Software Engineering', 'Level 2', '+232 79 890123', 'ajalloh@student.lu.sl',   '2024/2025', 8800.00, 8800.00),
('LU/SL/009', 'Hawa Dumbuya',         'Female', 'Design',              'BA Fashion Design',        'Level 3', '+232 76 901234', 'hdumbuya@student.lu.sl',  '2024/2025', 7000.00, 4000.00),
('LU/SL/010', 'Alhaji Mansaray',      'Male',   'Business',            'MBA Business Management',  'Level 1', '+232 77 012345', 'amansaray@student.lu.sl', '2024/2025', 12000.00,12000.00),
('LU/SL/011', 'Aminata Kanu',         'Female', 'Media',               'BA Public Relations',      'Level 4', '+232 78 123456', 'akanu@student.lu.sl',     '2024/2025', 7500.00, 7500.00),
('LU/SL/012', 'Lansana Koroma',       'Male',   'Engineering',         'BEng Electrical Eng.',     'Level 2', '+232 79 234567', 'lkoroma@student.lu.sl',   '2024/2025', 9200.00, 5000.00),
('LU/SL/013', 'Baindu Koroma',        'Female', 'Computing',           'BSc Computer Science',     'Level 1', '+232 76 345678', 'bkoroma@student.lu.sl',   '2024/2025', 8500.00, 8500.00),
('LU/SL/014', 'Abu Bakarr Sesay',     'Male',   'Business',            'BA Human Resource Mgmt',   'Level 3', '+232 77 456789', 'absesay@student.lu.sl',   '2024/2025', 7800.00, 1500.00),
('LU/SL/015', 'Sorie Kallon',         'Male',   'Design',              'BSc Interior Design',      'Level 2', '+232 78 567890', 'skallon@student.lu.sl',   '2024/2025', 7200.00, 7200.00);

-- ============================================================
-- SAMPLE DATA: payments
-- ============================================================
INSERT INTO payments (payment_id, student_id, amount, semester, payment_date, payment_method, status, reference_no) VALUES
('PAY-2025-001', 'LU/SL/001', 4250.00, 'Semester 1 2024/25', '2024-09-05', 'Bank Transfer', 'Verified', 'GTB/2024/00123'),
('PAY-2025-002', 'LU/SL/001', 4250.00, 'Semester 2 2024/25', '2025-01-10', 'Bank Transfer', 'Verified', 'GTB/2025/00045'),
('PAY-2025-003', 'LU/SL/002', 5000.00, 'Semester 1 2024/25', '2024-09-08', 'Cash',          'Verified', 'CASH/2024/001'),
('PAY-2025-004', 'LU/SL/003', 3600.00, 'Semester 1 2024/25', '2024-09-12', 'Online',        'Verified', 'ONL/2024/0012'),
('PAY-2025-005', 'LU/SL/003', 3600.00, 'Semester 2 2024/25', '2025-01-15', 'Online',        'Verified', 'ONL/2025/0018'),
('PAY-2025-006', 'LU/SL/004', 3500.00, 'Semester 1 2024/25', '2024-09-20', 'Bank Transfer', 'Verified', 'GTB/2024/00198'),
('PAY-2025-007', 'LU/SL/005', 3750.00, 'Semester 1 2024/25', '2024-09-03', 'Bank Transfer', 'Verified', 'GTB/2024/00201'),
('PAY-2025-008', 'LU/SL/005', 3750.00, 'Semester 2 2024/25', '2025-01-08', 'Bank Transfer', 'Verified', 'GTB/2025/00062'),
('PAY-2025-009', 'LU/SL/006', 4100.00, 'Semester 1 2024/25', '2024-09-01', 'Cheque',        'Verified', 'CHQ/2024/0045'),
('PAY-2025-010', 'LU/SL/006', 4100.00, 'Semester 2 2024/25', '2025-01-05', 'Cheque',        'Verified', 'CHQ/2025/0012'),
('PAY-2025-011', 'LU/SL/007', 2000.00, 'Semester 1 2024/25', '2024-09-25', 'Cash',          'Verified', 'CASH/2024/002'),
('PAY-2025-012', 'LU/SL/008', 4400.00, 'Semester 1 2024/25', '2024-09-07', 'Bank Transfer', 'Verified', 'GTB/2024/00215'),
('PAY-2025-013', 'LU/SL/008', 4400.00, 'Semester 2 2024/25', '2025-01-12', 'Bank Transfer', 'Verified', 'GTB/2025/00071'),
('PAY-2025-014', 'LU/SL/009', 4000.00, 'Semester 1 2024/25', '2024-09-18', 'Online',        'Pending',  'ONL/2024/0034'),
('PAY-2025-015', 'LU/SL/010', 6000.00, 'Semester 1 2024/25', '2024-09-02', 'Bank Transfer', 'Verified', 'GTB/2024/00222'),
('PAY-2025-016', 'LU/SL/010', 6000.00, 'Semester 2 2024/25', '2025-01-04', 'Bank Transfer', 'Verified', 'GTB/2025/00081'),
('PAY-2025-017', 'LU/SL/011', 3750.00, 'Semester 1 2024/25', '2024-09-10', 'Online',        'Verified', 'ONL/2024/0041'),
('PAY-2025-018', 'LU/SL/011', 3750.00, 'Semester 2 2024/25', '2025-01-18', 'Online',        'Verified', 'ONL/2025/0025'),
('PAY-2025-019', 'LU/SL/012', 5000.00, 'Semester 1 2024/25', '2024-09-22', 'Bank Transfer', 'Verified', 'GTB/2024/00230'),
('PAY-2025-020', 'LU/SL/013', 4250.00, 'Semester 1 2024/25', '2024-09-06', 'Cash',          'Verified', 'CASH/2024/003'),
('PAY-2025-021', 'LU/SL/013', 4250.00, 'Semester 2 2024/25', '2025-01-09', 'Cash',          'Verified', 'CASH/2025/001'),
('PAY-2025-022', 'LU/SL/014', 1500.00, 'Semester 1 2024/25', '2024-10-01', 'Bank Transfer', 'Pending',  'GTB/2024/00245'),
('PAY-2025-023', 'LU/SL/015', 3600.00, 'Semester 1 2024/25', '2024-09-14', 'Online',        'Verified', 'ONL/2024/0052'),
('PAY-2025-024', 'LU/SL/015', 3600.00, 'Semester 2 2024/25', '2025-01-20', 'Online',        'Verified', 'ONL/2025/0031');

-- ============================================================
-- SAMPLE DATA: clearances (auto-derived from balance)
-- ============================================================
INSERT INTO clearances (student_id, status, cleared_date, valid_until, notes) VALUES
('LU/SL/001', 'Cleared',     '2025-01-11 09:00:00', '2025-08-31', 'Full payment confirmed'),
('LU/SL/002', 'Not Cleared', NULL, NULL, 'Outstanding balance: Le 2,800.00'),
('LU/SL/003', 'Cleared',     '2025-01-16 10:30:00', '2025-08-31', 'Full payment confirmed'),
('LU/SL/004', 'Not Cleared', NULL, NULL, 'Outstanding balance: Le 5,500.00'),
('LU/SL/005', 'Cleared',     '2025-01-09 08:15:00', '2025-08-31', 'Full payment confirmed'),
('LU/SL/006', 'Cleared',     '2025-01-06 11:00:00', '2025-08-31', 'Full payment confirmed'),
('LU/SL/007', 'Not Cleared', NULL, NULL, 'Outstanding balance: Le 7,500.00'),
('LU/SL/008', 'Cleared',     '2025-01-13 09:45:00', '2025-08-31', 'Full payment confirmed'),
('LU/SL/009', 'Not Cleared', NULL, NULL, 'Outstanding balance: Le 3,000.00'),
('LU/SL/010', 'Cleared',     '2025-01-05 14:00:00', '2025-08-31', 'Full payment confirmed'),
('LU/SL/011', 'Cleared',     '2025-01-19 10:00:00', '2025-08-31', 'Full payment confirmed'),
('LU/SL/012', 'Not Cleared', NULL, NULL, 'Outstanding balance: Le 4,200.00'),
('LU/SL/013', 'Cleared',     '2025-01-10 08:30:00', '2025-08-31', 'Full payment confirmed'),
('LU/SL/014', 'Not Cleared', NULL, NULL, 'Outstanding balance: Le 6,300.00'),
('LU/SL/015', 'Cleared',     '2025-01-21 13:00:00', '2025-08-31', 'Full payment confirmed');

-- ============================================================
-- SAMPLE DATA: deferred_assessments
-- ============================================================
INSERT INTO deferred_assessments (student_id, course_code, course_name, semester, reason, status, review_date, review_notes) VALUES
('LU/SL/002', 'CS201', 'Data Structures & Algorithms', 'Semester 1 2024/25', 'Medical emergency – hospitalization during exam period. Medical certificate attached.', 'Approved', '2025-01-20 10:00:00', 'Medical certificate verified. Approved for supplementary exam.'),
('LU/SL/004', 'BA301', 'Corporate Finance',            'Semester 1 2024/25', 'Family bereavement – loss of parent during examination week.',                          'Approved', '2025-01-18 14:00:00', 'Bereavement letter verified. Approved.'),
('LU/SL/007', 'CE101', 'Engineering Mathematics I',   'Semester 1 2024/25', 'Financial difficulties affecting study preparation and attendance.',                    'Pending',  NULL, NULL),
('LU/SL/009', 'FD201', 'Textile Design & Technology', 'Semester 1 2024/25', 'Medical condition (chronic illness flare-up). Documentation submitted.',               'Pending',  NULL, NULL),
('LU/SL/012', 'EE201', 'Circuit Theory II',           'Semester 1 2024/25', 'Accident and injury – unable to sit examination. Hospital report attached.',            'Rejected', '2025-01-22 09:00:00', 'Insufficient supporting documentation. Resubmit with complete hospital records.'),
('LU/SL/014', 'HR301', 'Organizational Behaviour',    'Semester 1 2024/25', 'Personal hardship – family crisis requiring travel outside the country.',              'Pending',  NULL, NULL);

-- ============================================================
-- SAMPLE DATA: activity_log
-- ============================================================
INSERT INTO activity_log (user_id, action, module) VALUES
(1, 'System initialized',             'System'),
(2, 'Payment PAY-2025-023 verified',  'Payments'),
(3, 'Clearance generated for LU/SL/013', 'Clearance'),
(1, 'New student LU/SL/015 added',   'Students'),
(2, 'Payment PAY-2025-024 verified',  'Payments'),
(3, 'Deferred application reviewed',  'Deferred'),
(1, 'Report exported: Finance Summary','Reports');

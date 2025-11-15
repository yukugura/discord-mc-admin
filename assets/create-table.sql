CREATE TABLE IF NOT EXISTS perm_limits (
    perm_name VARCHAR(50) PRIMARY KEY,
    max_sv INT NOT NULL
);

INSERT IGNORE INTO perm_limits (perm_name, max_sv) VALUES
('default', 1),
('premium', 3),
('admin', 999);

CREATE TABLE IF NOT EXISTS users (
    dc_user_id VARCHAR(50) PRIMARY KEY,
    dc_user_name VARCHAR(255) NOT NULL,
    perm_name VARCHAR(50) NOT NULL,
    dc_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (perm_name) REFERENCES perm_limits(perm_name) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS servers (
    sv_id INT AUTO_INCREMENT PRIMARY KEY,
    dc_user_id VARCHAR(50) NOT NULL,
    sv_name VARCHAR(255) NOT NULL,
    sv_type VARCHAR(50) NOT NULL,
    sv_ver VARCHAR(20) NOT NULL,
    sv_port INT,
    status ENUM('running', 'stopped', 'creating', 'deleting','deleted', 'error') DEFAULT 'error' NOT NULL,
    sv_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dc_user_id) REFERENCES users(dc_user_id) ON UPDATE CASCADE ON DELETE CASCADE,
    UNIQUE (dc_user_id, sv_name)
);

CREATE TABLE IF NOT EXISTS server_versions(
    sv_ver_id INT AUTO_INCREMENT PRIMARY KEY,
    sv_type VARCHAR(50) NOT NULL,
    sv_ver VARCHAR(20) NOT NULL,
    build_ver INT NOT NULL DEFAULT 1,
    download_url VARCHAR(255) NOT NULL DEFAULT '1',
    is_supported BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (sv_type, sv_ver, build_ver)
);

INSERT IGNORE INTO server_versions (sv_type, sv_ver, is_supported) VALUES
('vanilla', '1.21.10', FALSE),
('vanilla', '1.21.9', FALSE),
('vanilla', '1.21.8', TRUE),
('vanilla', '1.21.7', TRUE),
('vanilla', '1.21.6', TRUE),
('vanilla', '1.21.5', TRUE),
('vanilla', '1.21.4', TRUE),
('vanilla', '1.21.3', TRUE),
('vanilla', '1.21.2', TRUE),
('vanilla', '1.20.6', TRUE),
('vanilla', '1.20.5', TRUE),
('vanilla', '1.20.4', TRUE),
('vanilla', '1.20.3', TRUE),
('vanilla', '1.20.2', TRUE),
('vanilla', '1.20.1', TRUE);

INSERT IGNORE INTO server_versions (sv_type, sv_ver, build_ver, download_url, is_supported) VALUES
('paper', '1.21.10', 113, 'https://fill-data.papermc.io/v1/objects/d4f897545310f31e623d9680786b25dd20a9989e139db050d1aacf81ecafd05c/paper-1.21.10-113.jar', TRUE),
('paper', '1.21.10', 112, 'https://fill-data.papermc.io/v1/objects/d901c205cebd2c14e2d92c5fcbd0ba95add71da9726fc7829d1431a8b80969b6/paper-1.21.10-112.jar', TRUE),
('paper', '1.21.10', 108, 'https://fill-data.papermc.io/v1/objects/2c825ddbe47897db1efbf1adfef0dbcfee7ebab2f959168cf59a654f3bdd0b36/paper-1.21.10-108.jar', TRUE),
('paper', '1.21.8', 60, 'https://fill-data.papermc.io/v1/objects/8de7c52c3b02403503d16fac58003f1efef7dd7a0256786843927fa92ee57f1e/paper-1.21.8-60.jar', TRUE);
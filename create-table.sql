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
    status ENUM('running', 'stopped', 'creating', 'deleting', 'error') DEFAULT 'stopped' NOT NULL,
    sv_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dc_user_id) REFERENCES users(dc_user_id) ON UPDATE CASCADE ON DELETE CASCADE,
    UNIQUE (dc_user_id, sv_name)
);

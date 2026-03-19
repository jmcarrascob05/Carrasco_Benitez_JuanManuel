USE rustyx_db;

CREATE TABLE IF NOT EXISTS health_check (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS servers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    server_name VARCHAR(50),
    ip_address VARCHAR(15),
    status VARCHAR(20),
    last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Insertar datos de ejemplo
INSERT INTO servers (server_name, ip_address, status) VALUES 
('web1', '192.168.20.10', 'active'),
('web2', '192.168.20.11', 'active');

-- Configurar permisos solo desde red backend
GRANT ALL PRIVILEGES ON rustyx_db.* TO 'rustyx_user'@'192.168.30.%';
FLUSH PRIVILEGES;

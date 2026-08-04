-- SupplyVision – Create Database & User
-- Run as MySQL root/admin user

CREATE DATABASE IF NOT EXISTS supply_vision
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'sv_user'@'localhost'
    IDENTIFIED BY 'SV@SecurePass2024!';

GRANT ALL PRIVILEGES ON supply_vision.* TO 'sv_user'@'localhost';
FLUSH PRIVILEGES;

USE supply_vision;

SELECT 'Database supply_vision created successfully.' AS status;

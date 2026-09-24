CREATE TABLE IF NOT EXISTS bases (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(160) NOT NULL UNIQUE,
  code VARCHAR(30) NOT NULL UNIQUE,
  location VARCHAR(200) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS users (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  display_name VARCHAR(160) NOT NULL,
  role ENUM('admin','base_commander','logistics_officer') NOT NULL,
  base_id BIGINT UNSIGNED NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT users_base_fk FOREIGN KEY (base_id) REFERENCES bases(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS equipment_types (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(180) NOT NULL,
  category ENUM('weapons','vehicles','ammunition','other') NOT NULL,
  unit VARCHAR(30) NOT NULL DEFAULT 'each',
  reorder_level BIGINT NOT NULL DEFAULT 0,
  UNIQUE KEY equipment_name_category (name, category)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS purchases (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  base_id BIGINT UNSIGNED NOT NULL,
  equipment_type_id BIGINT UNSIGNED NOT NULL,
  quantity BIGINT UNSIGNED NOT NULL,
  purchase_date DATE NOT NULL,
  reference VARCHAR(120) NULL,
  recorded_by BIGINT UNSIGNED NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (base_id) REFERENCES bases(id),
  FOREIGN KEY (equipment_type_id) REFERENCES equipment_types(id),
  FOREIGN KEY (recorded_by) REFERENCES users(id),
  INDEX purchases_base_date_idx (base_id, purchase_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS transfers (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  from_base_id BIGINT UNSIGNED NOT NULL,
  to_base_id BIGINT UNSIGNED NOT NULL,
  equipment_type_id BIGINT UNSIGNED NOT NULL,
  quantity BIGINT UNSIGNED NOT NULL,
  status ENUM('in_transit','received','cancelled') NOT NULL DEFAULT 'in_transit',
  reference VARCHAR(120) NOT NULL UNIQUE,
  dispatched_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  received_at TIMESTAMP NULL,
  dispatched_by BIGINT UNSIGNED NOT NULL,
  received_by BIGINT UNSIGNED NULL,
  FOREIGN KEY (from_base_id) REFERENCES bases(id),
  FOREIGN KEY (to_base_id) REFERENCES bases(id),
  FOREIGN KEY (equipment_type_id) REFERENCES equipment_types(id),
  FOREIGN KEY (dispatched_by) REFERENCES users(id),
  FOREIGN KEY (received_by) REFERENCES users(id),
  INDEX transfers_from_time_idx (from_base_id, dispatched_at),
  INDEX transfers_to_time_idx (to_base_id, dispatched_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS assignments (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  base_id BIGINT UNSIGNED NOT NULL,
  equipment_type_id BIGINT UNSIGNED NOT NULL,
  quantity BIGINT UNSIGNED NOT NULL,
  personnel_name VARCHAR(180) NOT NULL,
  unit_name VARCHAR(180) NULL,
  assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  returned_at TIMESTAMP NULL,
  recorded_by BIGINT UNSIGNED NOT NULL,
  FOREIGN KEY (base_id) REFERENCES bases(id),
  FOREIGN KEY (equipment_type_id) REFERENCES equipment_types(id),
  FOREIGN KEY (recorded_by) REFERENCES users(id),
  INDEX assignments_base_time_idx (base_id, assigned_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS expenditures (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  base_id BIGINT UNSIGNED NOT NULL,
  equipment_type_id BIGINT UNSIGNED NOT NULL,
  quantity BIGINT UNSIGNED NOT NULL,
  expended_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  purpose VARCHAR(500) NULL,
  reference VARCHAR(120) NULL,
  recorded_by BIGINT UNSIGNED NOT NULL,
  FOREIGN KEY (base_id) REFERENCES bases(id),
  FOREIGN KEY (equipment_type_id) REFERENCES equipment_types(id),
  FOREIGN KEY (recorded_by) REFERENCES users(id),
  INDEX expenditures_base_time_idx (base_id, expended_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS audit_log (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  actor_id BIGINT UNSIGNED NULL,
  action VARCHAR(100) NOT NULL,
  entity_type VARCHAR(60) NOT NULL,
  entity_id BIGINT UNSIGNED NULL,
  base_id BIGINT UNSIGNED NULL,
  before_data JSON NULL,
  after_data JSON NULL,
  request_id VARCHAR(120) NULL,
  occurred_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (actor_id) REFERENCES users(id),
  FOREIGN KEY (base_id) REFERENCES bases(id),
  INDEX audit_base_time_idx (base_id, occurred_at),
  INDEX audit_entity_idx (entity_type, entity_id)
) ENGINE=InnoDB;

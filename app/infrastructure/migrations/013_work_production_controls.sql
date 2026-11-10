ALTER TABLE work_runs ADD COLUMN pause_requested INTEGER NOT NULL DEFAULT 0 CHECK(pause_requested IN (0,1));
CREATE TABLE package_production_links (
 import_id TEXT PRIMARY KEY REFERENCES package_imports(import_id),
 project_id TEXT NOT NULL REFERENCES work_packages(project_id)
);

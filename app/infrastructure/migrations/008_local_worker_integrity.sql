CREATE TRIGGER local_studio_worker_capability
BEFORE UPDATE OF status,worker_id ON jobs
WHEN NEW.status='running' AND EXISTS(SELECT 1 FROM pilot_runs p WHERE p.job_id=NEW.job_id AND json_extract(p.config,'$.profile')='local-studio-1')
AND (NEW.worker_id IS NULL OR NEW.worker_id NOT LIKE 'studio:%')
BEGIN SELECT RAISE(ABORT,'Local studio requires the current worker'); END;
ALTER TABLE scheduled_items ADD COLUMN revision_id TEXT REFERENCES edit_revisions(revision_id);
ALTER TABLE scheduled_items ADD COLUMN last_error TEXT;
CREATE TRIGGER schedule_channel_guard BEFORE INSERT ON scheduled_items
WHEN NOT EXISTS(SELECT 1 FROM ideas WHERE idea_id=NEW.idea_id AND channel_id=NEW.channel_id)
OR (NEW.episode_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM episodes WHERE episode_id=NEW.episode_id AND channel_id=NEW.channel_id AND idea_id=NEW.idea_id))
BEGIN SELECT RAISE(ABORT,'Schedule belongs to another channel or idea'); END;
CREATE TRIGGER edit_channel_guard BEFORE INSERT ON edit_revisions
WHEN NOT EXISTS(SELECT 1 FROM episodes WHERE episode_id=NEW.episode_id AND channel_id=NEW.channel_id)
BEGIN SELECT RAISE(ABORT,'Storyboard belongs to another channel'); END;

-- Add access_status to org_memberships to track OAuth app authorization state.
-- Values: 'authorized' (default), 'restricted', 'pending_request'

ALTER TABLE org_memberships ADD COLUMN access_status TEXT DEFAULT 'authorized';

INSERT OR IGNORE INTO schema_version (version) VALUES (4);

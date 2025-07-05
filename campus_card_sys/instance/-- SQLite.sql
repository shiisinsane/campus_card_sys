-- SQLite
DELETE FROM campus_card;
DELETE FROM forum_post;
DELETE FROM user;

ALTER TABLE campus_card ADD COLUMN contact TEXT DEFAULT '';
UPDATE campus_card SET contact = NULL;

UPDATE campus_card 
SET contact = '13300000000' 
WHERE id = 3;

ALTER TABLE forum_post ADD COLUMN is_advice BOOLEAN DEFAULT FALSE;
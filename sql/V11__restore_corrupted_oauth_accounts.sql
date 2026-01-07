-- Restore OAuth accounts that were incorrectly set to 'imap' by the bug
--
-- Issue: The auth_method corruption bug caused OAuth accounts to have their
-- auth_method set to 'imap' even though they had valid OAuth refresh tokens.
--
-- This migration restores those accounts by:
-- 1. Finding accounts with auth_method='imap' AND oauth_refresh_token IS NOT NULL
-- 2. Setting their auth_method back to 'oauth'
--
-- Idempotent: Safe to run multiple times. Only affects accounts that are
-- currently corrupted. Already-restored accounts are not modified.

UPDATE email_accounts
SET auth_method = 'oauth',
    updated_at = NOW()
WHERE auth_method = 'imap'
  AND oauth_refresh_token IS NOT NULL
  AND oauth_refresh_token != '';

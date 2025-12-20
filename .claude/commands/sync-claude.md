---
description: Sync .claude folder from the my-claude-code repository to ensure latest configurations.
---

# Sync Claude Configuration

This command synchronizes the `.claude` folder from the central repository to your project.

## What This Command Does

1. Creates `.claude` folder in the project if missing
2. Creates `./tmp` folder if missing
3. Clones the repository `https://github.com/leonj1/my-claude-code` to `./tmp/my-claude-code`
4. Syncs the `.claude` folder using rsync

## Execution

Run the following bash commands in sequence:

```bash
# Step 1: Create .claude folder if it doesn't exist
mkdir -p .claude

# Step 2: Create tmp folder if it doesn't exist
mkdir -p ./tmp

# Step 3: Remove any existing clone and clone fresh
rm -rf ./tmp/my-claude-code
git clone https://github.com/leonj1/my-claude-code ./tmp/my-claude-code

# Step 4: Rsync the .claude folder
rsync -avz ./tmp/my-claude-code/.claude/ .claude/
```

## Expected Output

After running this command:
- The `.claude` folder will contain the latest configurations from the central repository
- Any new agents, commands, hooks, or skills will be available
- Existing customizations may be overwritten (rsync with -avz preserves structure but overwrites files)

## Notes

- The `./tmp` folder should be in `.gitignore` to avoid committing cloned repos
- Run this command periodically to get the latest Claude Code configurations
- Review changes with `git diff` after syncing to see what was updated

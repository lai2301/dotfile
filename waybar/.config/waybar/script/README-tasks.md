# Waybar Task Module

A custom waybar module written in Go that displays tasks from your markdown files.

## Features

- **Task Counter**: Shows the number of incomplete tasks in waybar
- **Tooltip Preview**: Displays top 5 active tasks with progress on hover
- **Click to View**: Click on the task icon or clock to open a detailed task view in a terminal
- **Auto-refresh**: Updates every 5 minutes (300 seconds)

## Files

- `tasks.go` - Main Go program that parses task markdown files
- `show-tasks.sh` - Shell script wrapper to display tasks in a terminal

## Usage

### Waybar Module (JSON output)
```bash
cd ~/.config/waybar/script && go run tasks.go
```

With sorting options:
```bash
cd ~/.config/waybar/script && go run tasks.go -sort=date
```

### Terminal Display Mode
```bash
cd ~/.config/waybar/script && go run tasks.go -display
```

Or use the convenience wrapper:
```bash
~/.config/waybar/script/show-tasks.sh
```

## Sorting Options

The module supports multiple sorting methods via the `-sort` flag:

| Sort Option | Description | Use Case |
|------------|-------------|----------|
| `lastmod` | Sort by last modified date (newest first) | **Default** - See recently updated tasks |
| `date` | Sort by task date (newest first) | See tasks by their creation/due date |
| `ticket` | Sort by ticket number (alphabetically desc) | Group tasks by ticket ID |
| `name` | Sort by filename (alphabetically asc) | Find tasks alphabetically |
| `progress` | Sort by completion % (incomplete first) | Focus on unfinished work |

### Examples

```bash
# Show most recently modified tasks first (default)
go run tasks.go -sort=lastmod

# Show newest tasks by date first
go run tasks.go -sort=date

# Show tasks sorted by ticket number
go run tasks.go -sort=ticket

# Show incomplete tasks first
go run tasks.go -sort=progress

# Show tasks alphabetically by name
go run tasks.go -sort=name
```

## Configuration

The module reads task files from: `/home/lai2301/Documents/lai_vault/000 Tasks`

Tasks are parsed from markdown files with:
- YAML frontmatter containing metadata (title, date, ticket, etc.)
- Checkbox format: `- [ ]` for incomplete, `- [x]` for completed

## Customization

### Change task directory
Edit `tasks.go` line:
```go
tasksDir := "/home/lai2301/Documents/lai_vault/000 Tasks"
```

### Change sorting order
Edit `config.jsonc`:
```json
"custom/tasks": {
  "exec": "cd $HOME/.config/waybar/script && go run tasks.go -sort=progress"
  // Options: lastmod, date, ticket, name, progress
}
```

### Change refresh interval
Edit `config.jsonc`:
```json
"custom/tasks": {
  "interval": 300  // seconds
}
```

### Change terminal emulator
Edit `config.jsonc` and `show-tasks.sh` to use your preferred terminal instead of `foot`.

## Building a Binary (Optional)

To improve performance, you can build a binary instead of using `go run`:

```bash
cd ~/.config/waybar/script
go build -o tasks tasks.go
```

Then update `config.jsonc`:
```json
"custom/tasks": {
  "exec": "$HOME/.config/waybar/script/tasks"
}
```

And update `show-tasks.sh`:
```bash
#!/bin/bash
cd "$(dirname "$0")"
./tasks display
```

## Styling

The module is styled in `style.css` under `#custom-tasks`. Customize colors, spacing, and hover effects there.


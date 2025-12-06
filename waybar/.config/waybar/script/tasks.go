package main

import (
	"bufio"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

type Task struct {
	Filename     string
	Title        string
	Ticket       string
	Date         string
	LastModified string
	Incomplete   int
	Total        int
	Tasks        []string
}

type WaybarOutput struct {
	Text       string `json:"text"`
	Tooltip    string `json:"tooltip"`
	Class      string `json:"class"`
	Percentage int    `json:"percentage"`
	Alt        string `json:"alt,omitempty"`
}

func parseFrontmatter(lines []string) (map[string]string, int) {
	metadata := make(map[string]string)
	inFrontmatter := false
	endLine := 0

	for i, line := range lines {
		trimmed := strings.TrimSpace(line)

		if trimmed == "---" {
			if !inFrontmatter {
				inFrontmatter = true
				continue
			} else {
				endLine = i + 1
				break
			}
		}

		if inFrontmatter && strings.Contains(trimmed, ":") {
			parts := strings.SplitN(trimmed, ":", 2)
			if len(parts) == 2 {
				key := strings.TrimSpace(parts[0])
				value := strings.TrimSpace(parts[1])
				metadata[key] = value
			}
		}
	}

	return metadata, endLine
}

func parseTaskFile(filename string) (*Task, error) {
	file, err := os.Open(filename)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	var lines []string
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		lines = append(lines, scanner.Text())
	}

	if err := scanner.Err(); err != nil {
		return nil, err
	}

	metadata, endLine := parseFrontmatter(lines)

	task := &Task{
		Filename:     filepath.Base(filename),
		Title:        metadata["title"],
		Ticket:       metadata["Ticket"],
		Date:         metadata["date"],
		LastModified: metadata["LastModified"],
		Tasks:        []string{},
	}

	// Parse tasks from content
	checkboxPattern := regexp.MustCompile(`^\s*-\s+\[([ x])\]\s+(.+)$`)

	for i := endLine; i < len(lines); i++ {
		line := lines[i]
		if matches := checkboxPattern.FindStringSubmatch(line); matches != nil {
			task.Total++
			taskText := matches[2]

			// Clean up the task text (remove wiki links brackets)
			taskText = strings.ReplaceAll(taskText, "[[", "")
			taskText = strings.ReplaceAll(taskText, "]]", "")

			if matches[1] == " " {
				task.Incomplete++
				task.Tasks = append(task.Tasks, "☐ "+taskText)
			} else {
				task.Tasks = append(task.Tasks, "☑ "+taskText)
			}
		}
	}

	return task, nil
}

func getTaskFiles(dir string) ([]string, error) {
	var files []string

	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, err
	}

	for _, entry := range entries {
		if !entry.IsDir() && strings.HasSuffix(entry.Name(), ".md") && entry.Name() != "000.base" {
			fullPath := filepath.Join(dir, entry.Name())
			files = append(files, fullPath)
		}
	}

	return files, nil
}

func main() {
	tasksDir := "/home/lai2301/Documents/lai_vault/000 Tasks"

	// Define flags
	sortBy := flag.String("sort", "lastmod", "Sort order: lastmod, date, ticket, name, progress")
	displayMode := flag.Bool("display", false, "Display detailed task list")

	// Parse flags
	flag.Parse()

	// Handle legacy "display" argument for backwards compatibility
	if len(flag.Args()) > 0 && flag.Args()[0] == "display" {
		*displayMode = true
	}

	files, err := getTaskFiles(tasksDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error reading tasks directory: %v\n", err)
		os.Exit(1)
	}

	var allTasks []*Task
	totalIncomplete := 0
	totalTasks := 0
	totalFiles := 0
	incompleteFiles := 0

	for _, file := range files {
		task, err := parseTaskFile(file)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error parsing %s: %v\n", file, err)
			continue
		}

		// Count all tasks (files), regardless of whether they have todos
		allTasks = append(allTasks, task)
		totalFiles++

		// Check if this task file has incomplete todos or no todos at all
		if task.Incomplete > 0 || task.Total == 0 {
			incompleteFiles++
		}

		totalIncomplete += task.Incomplete
		totalTasks += task.Total
	}

	// Sort tasks based on selected method
	sortTasks(allTasks, *sortBy)

	if *displayMode {
		// Display detailed task list
		fmt.Println("\n╔══════════════════════════════════════════════════════════════════════════╗")
		fmt.Printf("║  📋 TASK OVERVIEW - %d tasks%*s║\n",
			totalFiles,
			55-len(fmt.Sprintf("%d tasks", totalFiles)), "")
		fmt.Println("╚══════════════════════════════════════════════════════════════════════════╝")
		fmt.Println()

		for _, task := range allTasks {
			// Show all tasks, highlighting incomplete ones
			displayName := strings.TrimSuffix(task.Filename, ".md")

			fmt.Printf("┌─ %s\n", displayName)

			if task.Total > 0 {
				fmt.Printf("│  Progress: %d/%d todos (%d%%)\n",
					task.Total-task.Incomplete, task.Total,
					(task.Total-task.Incomplete)*100/task.Total)
			} else {
				fmt.Printf("│  No todos defined\n")
			}

			if task.Ticket != "" {
				fmt.Printf("│  Ticket: %s\n", task.Ticket)
			}

			if task.Date != "" {
				fmt.Printf("│  Date: %s\n", task.Date)
			}

			// Only show incomplete todos if there are any
			if task.Incomplete > 0 {
				fmt.Println("│")
				for _, t := range task.Tasks {
					if strings.HasPrefix(t, "☐") {
						fmt.Printf("│  %s\n", t)
					}
				}
			}

			fmt.Println("└──────────────────────────────────────────────────────────────────────────")
			fmt.Println()
		}
	} else {
		// Waybar mode - output JSON
		tooltip := buildTooltip(allTasks)

		output := WaybarOutput{
			Text:       fmt.Sprintf("󰄲 %d", incompleteFiles),
			Tooltip:    tooltip,
			Class:      "tasks",
			Percentage: 0,
		}

		if totalFiles > 0 {
			output.Percentage = (totalFiles - incompleteFiles) * 100 / totalFiles
		}

		jsonData, err := json.Marshal(output)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error encoding JSON: %v\n", err)
			os.Exit(1)
		}

		fmt.Println(string(jsonData))
	}
}

func sortTasks(tasks []*Task, sortBy string) {
	switch sortBy {
	case "date":
		// Sort by task date (most recent first)
		sort.Slice(tasks, func(i, j int) bool {
			return tasks[i].Date > tasks[j].Date
		})
	case "ticket":
		// Sort by ticket number (alphabetically)
		sort.Slice(tasks, func(i, j int) bool {
			if tasks[i].Ticket == tasks[j].Ticket {
				return tasks[i].LastModified > tasks[j].LastModified
			}
			return tasks[i].Ticket > tasks[j].Ticket
		})
	case "name":
		// Sort by filename (alphabetically)
		sort.Slice(tasks, func(i, j int) bool {
			return tasks[i].Filename < tasks[j].Filename
		})
	case "progress":
		// Sort by completion percentage (incomplete first, then by percentage)
		sort.Slice(tasks, func(i, j int) bool {
			// Tasks without todos go to the end
			if tasks[i].Total == 0 && tasks[j].Total == 0 {
				return tasks[i].LastModified > tasks[j].LastModified
			}
			if tasks[i].Total == 0 {
				return false
			}
			if tasks[j].Total == 0 {
				return true
			}

			// Calculate completion percentages
			pctI := (tasks[i].Total - tasks[i].Incomplete) * 100 / tasks[i].Total
			pctJ := (tasks[j].Total - tasks[j].Incomplete) * 100 / tasks[j].Total

			// Sort by percentage (lowest first - most incomplete)
			if pctI == pctJ {
				return tasks[i].LastModified > tasks[j].LastModified
			}
			return pctI < pctJ
		})
	default: // "lastmod"
		// Sort by last modified date (most recent first)
		sort.Slice(tasks, func(i, j int) bool {
			return tasks[i].LastModified > tasks[j].LastModified
		})
	}
}

func buildTooltip(tasks []*Task) string {
	var builder strings.Builder

	// STYLING CONFIGURATION - Customize colors and appearance here
	// Use Pango markup: https://docs.gtk.org/Pango/pango_markup.html
	const (
		headerColor    = "#f5c2e7" // Pink - main header
		taskNameColor  = "#89b4fa" // Blue - task names
		metadataColor  = "#cdd6f4" // Light gray - metadata text
		progressColor  = "#a6e3a1" // Green - progress info
		separatorColor = "#6c7086" // Dim gray - separators
		hintColor      = "#89b4fa" // Blue - footer hints

		// Pango size units: 'xx-small', 'x-small', 'small', 'medium', 'large', 'x-large', 'xx-large'
		// Or use absolute sizes like '12000' (12pt * 1000)
		headerSize   = "15pt" // Header font size
		taskNameSize = "12pt" // Task name font size
		metadataSize = "10pt" // Metadata font size
	)

	// Header with custom styling
	builder.WriteString(fmt.Sprintf("<span size='%s' weight='bold' foreground='%s'>📋 Task List</span>\n",
		headerSize, headerColor))
	builder.WriteString(fmt.Sprintf("<span foreground='%s'>━━━━━━━━━━━━━━━━━━━━━━━━━━━━</span>\n\n",
		separatorColor))

	// Show up to 8 most recent tasks
	count := 0
	for _, task := range tasks {
		if count >= 8 {
			break
		}

		displayName := strings.TrimSuffix(task.Filename, ".md")

		// Limit display name length
		if len(displayName) > 40 {
			displayName = displayName[:37] + "..."
		}

		// Determine status indicator and color
		statusIcon := "📄"
		taskColor := taskNameColor
		if task.Total > 0 {
			if task.Incomplete == 0 {
				statusIcon = "✅"
				taskColor = progressColor // Green for completed
			} else if task.Incomplete > 0 {
				statusIcon = "⏳"
				taskColor = taskNameColor // Blue for in-progress
			}
		}

		// Task name with custom color and size
		builder.WriteString(fmt.Sprintf("%s <span size='%s' weight='bold' foreground='%s'>%s</span>\n",
			statusIcon, taskNameSize, taskColor, displayName))

		// Show metadata with custom styling
		if task.Ticket != "" {
			builder.WriteString(fmt.Sprintf("   <span size='%s' foreground='%s'>Ticket: %s</span>",
				metadataSize, metadataColor, task.Ticket))
			if task.Date != "" {
				builder.WriteString(fmt.Sprintf(" <span foreground='%s'>|</span> <span size='%s' foreground='%s'>Date: %s</span>",
					separatorColor, metadataSize, metadataColor, task.Date))
			}
			builder.WriteString("\n")
		} else if task.Date != "" {
			builder.WriteString(fmt.Sprintf("   <span size='%s' foreground='%s'>Date: %s</span>\n",
				metadataSize, metadataColor, task.Date))
		}

		// Show todo progress if available
		if task.Total > 0 {
			percentage := (task.Total - task.Incomplete) * 100 / task.Total
			builder.WriteString(fmt.Sprintf("   <span size='%s' foreground='%s'>Progress: %d/%d todos (%d%%)</span>\n",
				metadataSize, progressColor, task.Total-task.Incomplete, task.Total, percentage))
		}

		builder.WriteString("\n")
		count++
	}

	if count == 0 {
		builder.WriteString(fmt.Sprintf("<span foreground='%s'><i>No tasks found! 🎉</i></span>\n",
			progressColor))
	}

	builder.WriteString(fmt.Sprintf("<span foreground='%s'>━━━━━━━━━━━━━━━━━━━━━━━━━━━━</span>\n",
		separatorColor))
	builder.WriteString(fmt.Sprintf("<span size='%s' foreground='%s'><i>Click to view details</i></span>",
		metadataSize, hintColor))

	return builder.String()
}

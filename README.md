# CODX - Code Snippet Manager

A powerful command-line code snippet library manager with an interactive Text User Interface (TUI). Organize, search, and execute your code snippets efficiently from the terminal.

## Features

- **🚀 CLI Commands**: Add, find, get, run, edit, and manage code snippets
- **🎨 Interactive TUI**: Browse and search snippets with a beautiful terminal interface
- **🔧 Variable Substitution**: Use placeholders in snippets with default values
- **🌐 Multi-language Support**: Support for Python, JavaScript, Bash, Ruby, PHP, Perl, and more
- **🔍 Fuzzy Search**: Find snippets quickly with intelligent search
- **📋 Clipboard Integration**: Copy snippets to clipboard with one command
- **🏷️ Tag System**: Organize snippets with tags for better categorization
- **⚡ Quick Execution**: Run snippets directly from the command line

## Installation

```bash
pip install codx-snippet-manager
```

## Quick Start

1. **Initialize the database**:
   ```bash
   codx init
   ```

2. **Add your first snippet**:
   ```bash
   codx add --description "Hello World Python" --language python
   ```

3. **Launch the interactive finder**:
   ```bash
   codx find
   ```

## Commands

### Managing Snippets

```bash
# Add a snippet from file
codx add --file script.py --description "My Python script"

# Add a snippet interactively
codx add --description "Quick command" --language bash

# Edit an existing snippet
codx edit 1

# Delete a snippet
codx delete 1
```

### Finding and Using Snippets

```bash
# Launch interactive TUI browser
codx find

# Search with specific filters
codx find --query "python" --language python --tags "web,api"

# Copy snippet to clipboard
codx get 1

# Execute snippet with variable substitution
codx run 1
```

### Data Management

```bash
# Export all snippets to JSON
codx export snippets.json

# Import snippets from JSON
codx import snippets.json
```

## Variable Substitution

Snippets can contain variables using the `{{variable_name}}` or `{{variable_name:default_value}}` syntax:

```python
print("Hello, {{name:World}}!")
print("Your age is {{age}}")
```

When running the snippet, you'll be prompted to provide values for these variables.

## Interactive TUI

The Text User Interface provides an intuitive way to browse and manage your snippets:

### Navigation
- **Search**: Type to filter snippets in real-time
- **Navigate**: Use arrow keys to select snippets
- **Preview**: View snippet content before using

### Keyboard Shortcuts
- `Enter` or `c`: Copy snippet to clipboard
- `v`: View full snippet details
- `e`: Edit snippet
- `r`: Run snippet with variable substitution
- `d`: Delete snippet
- `q` or `Escape`: Quit

## Advanced Features

### Variable Substitution

Snippets support dynamic variables using `{{variable_name}}` or `{{variable_name:default_value}}` syntax:

```python
print("Hello, {{name:World}}!")
print("Your age is {{age}}")
```

When executing, you'll be prompted to provide values for these variables.

### Tags and Organization

Organize snippets with tags for better categorization:

```bash
# Add snippet with tags
codx add --description "API request" --tags "python,web,api"

# Search by tags
codx find --tags "web,api"
```

## Requirements

- Python 3.8 or higher
- Terminal with Unicode support (for best TUI experience)

## License

MIT License
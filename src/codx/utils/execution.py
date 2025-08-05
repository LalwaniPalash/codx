"""Code execution utilities for CODX."""

import os
import tempfile
import subprocess
from typing import Optional
from rich.console import Console
from .variables import extract_variables, prompt_for_variables, substitute_variables

console = Console()


def execute_snippet(content: str, language: str = None, variables: dict = None) -> dict:
    """Execute a code snippet.
    
    Args:
        content: The code content to execute
        language: Programming language (used to determine execution method)
        variables: Dictionary of variable values to substitute
        
    Returns:
        Dictionary with 'success' (bool) and 'output' (str) keys
    """
    # Handle variables if present
    if variables:
        content = substitute_variables(content, variables)
    else:
        snippet_variables = extract_variables(content)
        if snippet_variables:
            var_values = prompt_for_variables(content)
            content = substitute_variables(content, var_values)
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix=get_file_extension(language), delete=False) as temp_file:
        temp_file.write(content)
        temp_file_path = temp_file.name
    
    try:
        # Determine execution command based on language
        if language:
            lang = language.lower()
            if lang in ['python', 'py']:
                cmd = ['python', temp_file_path]
            elif lang in ['javascript', 'js', 'node']:
                cmd = ['node', temp_file_path]
            elif lang in ['bash', 'sh', 'shell']:
                cmd = ['bash', temp_file_path]
            elif lang in ['ruby', 'rb']:
                cmd = ['ruby', temp_file_path]
            elif lang in ['php']:
                cmd = ['php', temp_file_path]
            elif lang in ['perl', 'pl']:
                cmd = ['perl', temp_file_path]
            else:
                error_msg = f"Language '{language}' is not supported"
                console.print(f"[red]{error_msg}[/red]")
                return {
                    'success': False,
                    'output': "",
                    'error': error_msg
                }
        else:
            # Default to shell execution
            cmd = ['bash', temp_file_path]
        
        console.print(f"[yellow]Executing snippet...[/yellow]")
        console.print(f"[dim]Command: {' '.join(cmd)}[/dim]")
        console.print("[dim]" + "="*50 + "[/dim]")
        
        # Execute the command
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        console.print("[dim]" + "="*50 + "[/dim]")
        
        # Combine stdout and stderr for output
        output = result.stdout
        if result.stderr:
            output += result.stderr
        
        success = result.returncode == 0
        
        if success:
            console.print("[green]✓ Execution completed successfully[/green]")
        else:
            console.print(f"[red]✗ Execution failed with exit code {result.returncode}[/red]")
        
        return {
            'success': success,
            'output': output,
            'error': result.stderr if result.stderr else ""
        }
            
    except subprocess.TimeoutExpired:
            console.print("[red]Execution timeout[/red]")
            return {
                'success': False,
                'output': '',
                'error': 'Execution timeout after 30 seconds'
            }
    except FileNotFoundError as e:
        error_msg = f"Required interpreter not found. {e}"
        console.print(f"[red]Error: {error_msg}[/red]")
        console.print("[yellow]Make sure the appropriate interpreter is installed and in your PATH.[/yellow]")
        return {
            'success': False,
            'output': '',
            'error': error_msg
        }
    except Exception as e:
        error_msg = f"Error executing snippet: {e}"
        console.print(f"[red]{error_msg}[/red]")
        return {
            'success': False,
            'output': '',
            'error': error_msg
        }
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_file_path)
        except OSError:
            pass


def get_file_extension(language: str) -> str:
    """Get appropriate file extension for a programming language.
    
    Args:
        language: Programming language name
        
    Returns:
        File extension including the dot
    """
    if not language:
        return '.txt'
    
    lang = language.lower()
    extensions = {
        'python': '.py',
        'py': '.py',
        'javascript': '.js',
        'js': '.js',
        'node': '.js',
        'bash': '.sh',
        'sh': '.sh',
        'shell': '.sh',
        'ruby': '.rb',
        'rb': '.rb',
        'php': '.php',
        'perl': '.pl',
        'pl': '.pl',
        'java': '.java',
        'c': '.c',
        'cpp': '.cpp',
        'go': '.go',
        'rust': '.rs',
        'swift': '.swift',
        'kotlin': '.kt',
        'scala': '.scala'
    }
    
    return extensions.get(lang, '.txt')


def open_editor_for_content(content: str = "", language: str = "txt") -> str:
    """Open the default text editor to edit snippet content.
    
    Args:
        content: Initial content to populate the editor with
        language: Programming language for file extension
        
    Returns:
        Content written in the editor
    """
    # Get the default editor from environment
    editor = os.environ.get('EDITOR', 'nano')  # Default to nano if EDITOR not set
    
    # Get appropriate file extension
    extension = get_file_extension(language)
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w+', suffix=extension, delete=False) as temp_file:
        temp_file_path = temp_file.name
        # Write the initial content
        temp_file.write(content)
    
    try:
        # Open the editor
        console.print(f"[yellow]Opening {editor} for snippet content...[/yellow]")
        result = subprocess.run([editor, temp_file_path], check=True)
        
        # Read the content back
        with open(temp_file_path, 'r') as temp_file:
            edited_content = temp_file.read()
        
        return edited_content
        
    except subprocess.CalledProcessError:
        console.print("[red]Editor was cancelled or failed[/red]")
        return content  # Return original content on error
    except Exception as e:
        console.print(f"[red]Error opening editor: {e}[/red]")
        return content  # Return original content on error
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_file_path)
        except OSError:
            pass
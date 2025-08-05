"""Variable handling utilities for CODX."""

import re
from typing import List, Dict
from rich.console import Console
from rich.prompt import Prompt

console = Console()


def extract_variables(content: str) -> List[str]:
    """Extract variable placeholders from snippet content.
    
    Variables are defined as {{variable_name}} or {{variable_name:default_value}}
    
    Args:
        content: The snippet content
        
    Returns:
        List of variable names found in the content
    """
    pattern = r'\{\{([^}]+)\}\}'
    matches = re.findall(pattern, content)
    variables = []
    
    for match in matches:
        var_name = match.split(':')[0].strip()
        if var_name not in variables:
            variables.append(var_name)
    
    return variables


def substitute_variables(content: str, variables: Dict[str, str]) -> str:
    """Replace variable placeholders with actual values.
    
    Args:
        content: The snippet content with variables
        variables: Dictionary mapping variable names to values
        
    Returns:
        Content with variables substituted
    """
    result = content
    
    # Replace variables with provided values
    for var_name, var_value in variables.items():
        # Replace both {{var}} and {{var:default}} patterns
        pattern = r'\{\{' + re.escape(var_name) + r'(?::[^}]*)?\}\}'
        result = re.sub(pattern, var_value, result)
    
    # Handle remaining variables with default values
    def replace_with_default(match):
        full_match = match.group(1)
        if ':' in full_match:
            var_name, default_value = full_match.split(':', 1)
            return default_value.strip()
        else:
            return f"{{{{{full_match}}}}}"
    
    pattern = r'\{\{([^}]+)\}\}'
    result = re.sub(pattern, replace_with_default, result)
    
    return result


def prompt_for_variables(variables) -> Dict[str, str]:
    """
    Prompt user for variable values.
    
    Args:
        variables: Either a string containing variables or a list of variable names
        
    Returns:
        Dictionary mapping variable names to user-provided values
    """
    # Handle both string content and list of variables
    if isinstance(variables, str):
        var_list = extract_variables(variables)
        content = variables
    else:
        var_list = variables
        content = None
    
    if not var_list:
        return {}
    
    console.print("\n[yellow]This snippet contains variables. Please provide values:[/yellow]")
    
    var_values = {}
    for var_name in var_list:
        # Check if variable has a default value (only if we have content)
        default_value = None
        if content:
            pattern = r'\{\{' + re.escape(var_name) + r':([^}]+)\}\}'
            match = re.search(pattern, content)
            default_value = match.group(1).strip() if match else None
        
        if default_value:
            value = Prompt.ask(f"Enter value for '{var_name}'", default=default_value)
        else:
            value = Prompt.ask(f"Enter value for '{var_name}'")
        
        var_values[var_name] = value
    
    return var_values


def substitute_variables(content: str, variables: Dict[str, str]) -> str:
    """Substitute variables in content with provided values.
    
    Args:
        content: The content containing variable placeholders
        variables: Dictionary mapping variable names to values
        
    Returns:
        Content with variables substituted
    """
    result = content
    for var_name, value in variables.items():
        # Replace both {{var}} and {{var:default}} patterns
        pattern = r'\{\{' + re.escape(var_name) + r'(?::[^}]+)?\}\}'
        result = re.sub(pattern, value, result)
    
    return result
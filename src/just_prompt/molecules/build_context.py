"""
Build context functionality for just-prompt.
"""

import logging
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from .prompt import prompt

logger = logging.getLogger(__name__)

# Common file extensions and their language mappings
LANGUAGE_MAP = {
    '.py': 'python',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.jsx': 'javascript',
    '.java': 'java',
    '.c': 'c',
    '.cpp': 'cpp',
    '.cc': 'cpp',
    '.cxx': 'cpp',
    '.h': 'c',
    '.hpp': 'cpp',
    '.cs': 'csharp',
    '.go': 'go',
    '.rs': 'rust',
    '.php': 'php',
    '.rb': 'ruby',
    '.swift': 'swift',
    '.kt': 'kotlin',
    '.scala': 'scala',
    '.sh': 'bash',
    '.bash': 'bash',
    '.zsh': 'zsh',
    '.fish': 'fish',
    '.ps1': 'powershell',
    '.sql': 'sql',
    '.html': 'html',
    '.css': 'css',
    '.scss': 'scss',
    '.sass': 'sass',
    '.less': 'less',
    '.xml': 'xml',
    '.json': 'json',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.toml': 'toml',
    '.ini': 'ini',
    '.cfg': 'ini',
    '.conf': 'ini',
    '.md': 'markdown',
    '.txt': 'text',
    '.log': 'text',
    '.env': 'bash',
    '.dockerfile': 'dockerfile',
    '.makefile': 'makefile',
    '.gradle': 'gradle',
    '.r': 'r',
    '.R': 'r',
    '.m': 'matlab',
    '.pl': 'perl',
    '.lua': 'lua',
    '.vim': 'vim',
    '.dart': 'dart',
    '.elm': 'elm',
    '.ex': 'elixir',
    '.exs': 'elixir',
    '.clj': 'clojure',
    '.cljs': 'clojure',
    '.hs': 'haskell',
    '.ml': 'ocaml',
    '.fs': 'fsharp',
    '.jl': 'julia',
    '.nim': 'nim',
    '.zig': 'zig',
}

# Files to ignore by default
DEFAULT_IGNORE_PATTERNS = [
    '.git',
    '.gitignore',
    '.gitmodules',
    '__pycache__',
    '.pytest_cache',
    'node_modules',
    '.npm',
    '.yarn',
    'package-lock.json',
    'yarn.lock',
    '.env',
    '.venv',
    'env',
    'venv',
    '.DS_Store',
    'Thumbs.db',
    '*.pyc',
    '*.pyo',
    '*.pyd',
    '*.so',
    '*.dylib',
    '*.dll',
    '*.exe',
    '*.o',
    '*.obj',
    '*.a',
    '*.lib',
    '*.log',
    '.idea',
    '.vscode',
    '.vs',
    '*.swp',
    '*.swo',
    '*~',
    '.coverage',
    '.nyc_output',
    'coverage',
    'dist',
    'build',
    'target',
    'bin',
    'obj',
    '.next',
    '.nuxt',
    '.svelte-kit',
    'node_modules.nosync',
    '.tmp',
    '.temp',
]


def get_file_language(file_path: Path) -> str:
    """
    Determine the programming language for a file based on its extension.
    Handles multiple extensions like config.yaml.example by using the last known extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Language string for markdown code block formatting
    """
    filename = file_path.name.lower()
    
    # Special cases for files without extensions
    if '.' not in filename:
        if filename in ['dockerfile', 'makefile', 'rakefile', 'gemfile']:
            return filename
        elif filename.startswith('makefile'):
            return 'makefile'
        return 'text'
    
    # Handle multiple extensions by checking each extension from right to left
    # e.g., for "config.yaml.example", check ".example", then ".yaml"
    parts = filename.split('.')
    for i in range(len(parts) - 1, 0, -1):
        extension = '.' + parts[i]
        if extension in LANGUAGE_MAP:
            return LANGUAGE_MAP[extension]
    
    # Fallback to the actual suffix if no known extension found
    extension = file_path.suffix.lower()
    return LANGUAGE_MAP.get(extension, 'text')


def should_ignore_file(file_path: Path, ignore_patterns: List[str]) -> bool:
    """
    Check if a file should be ignored based on ignore patterns.
    
    Args:
        file_path: Path to the file
        ignore_patterns: List of patterns to ignore
        
    Returns:
        True if file should be ignored, False otherwise
    """
    filename = file_path.name
    path_parts = file_path.parts
    
    for pattern in ignore_patterns:
        # Check if pattern matches filename exactly
        if pattern == filename:
            return True
        
        # Handle wildcard patterns
        if pattern.startswith('*'):
            if filename.endswith(pattern[1:]):
                return True
        
        # Check if pattern matches any part of the path (directory names)
        if pattern in path_parts:
            return True
    
    return False


def collect_files(directories: Optional[List[str]] = None, files: Optional[List[str]] = None, ignore_patterns: Optional[List[str]] = None) -> List[Path]:
    """
    Collect files from specified directories and/or specific file paths.
    
    Args:
        directories: Optional list of directory paths to traverse
        files: Optional list of specific file paths to include
        ignore_patterns: List of patterns to ignore (uses defaults if None)
        
    Returns:
        List of Path objects for all collected files
    """
    if ignore_patterns is None:
        ignore_patterns = DEFAULT_IGNORE_PATTERNS
    
    collected_files = []
    
    # Process directories if provided
    if directories:
        for directory in directories:
            dir_path = Path(directory)
            
            if not dir_path.exists():
                logger.warning(f"Directory does not exist: {directory}")
                continue
                
            if not dir_path.is_dir():
                logger.warning(f"Not a directory: {directory}")
                continue
            
            # Walk through directory recursively
            for file_path in dir_path.rglob('*'):
                if file_path.is_file() and not should_ignore_file(file_path, ignore_patterns):
                    # Check if file is readable and not too large (> 1MB)
                    try:
                        if file_path.stat().st_size > 1024 * 1024:  # 1MB limit
                            logger.warning(f"Skipping large file: {file_path}")
                            continue
                        collected_files.append(file_path)
                    except (OSError, IOError) as e:
                        logger.warning(f"Cannot access file {file_path}: {e}")
                        continue
    
    # Process specific files if provided
    if files:
        for file_str in files:
            file_path = Path(file_str)
            
            if not file_path.exists():
                logger.warning(f"File does not exist: {file_str}")
                continue
                
            if not file_path.is_file():
                logger.warning(f"Not a file: {file_str}")
                continue
            
            # Check if file should be ignored
            if should_ignore_file(file_path, ignore_patterns):
                logger.info(f"File ignored due to ignore patterns: {file_str}")
                continue
            
            # Check if file is readable and not too large (> 1MB)
            try:
                if file_path.stat().st_size > 1024 * 1024:  # 1MB limit
                    logger.warning(f"Skipping large file: {file_path}")
                    continue
                collected_files.append(file_path)
            except (OSError, IOError) as e:
                logger.warning(f"Cannot access file {file_path}: {e}")
                continue
    
    # Sort files by path for consistent output and remove duplicates
    return sorted(list(set(collected_files)))


def read_file_content(file_path: Path, include_line_numbers: bool = True) -> str:
    """
    Read the content of a file safely.
    
    Args:
        file_path: Path to the file
        include_line_numbers: Whether to include line numbers in the output
        
    Returns:
        File content as string, or error message if read fails
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if include_line_numbers:
                lines = content.splitlines()
                numbered_lines = []
                for i, line in enumerate(lines, 1):
                    numbered_lines.append(f"{i:>4}→{line}")
                return '\n'.join(numbered_lines)
            return content
    except UnicodeDecodeError:
        try:
            # Try with latin-1 encoding for binary-like files
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
                if all(ord(c) < 128 for c in content[:100]):  # Check if mostly ASCII
                    if include_line_numbers:
                        lines = content.splitlines()
                        numbered_lines = []
                        for i, line in enumerate(lines, 1):
                            numbered_lines.append(f"{i:>4}→{line}")
                        return '\n'.join(numbered_lines)
                    return content
                else:
                    return f"[Binary file - content not displayed]"
        except Exception:
            return f"[Error reading file: Unable to decode]"
    except Exception as e:
        return f"[Error reading file: {str(e)}]"


def generate_file_summary(file_path: Path, content: str, model: str) -> str:
    """
    Generate a summary of the file's purpose using an LLM.
    
    Args:
        file_path: Path to the file
        content: File content
        model: Model to use for summarization
        
    Returns:
        Summary text
    """
    try:
        summary_prompt = f"""
Analyze this file and provide a brief 1-2 sentence summary of its purpose and functionality.

File: {file_path}

Content:
```
{content[:2000]}...
```

Respond only with the summary, no additional text.
"""
        
        responses = prompt(summary_prompt, [model])
        if responses and len(responses) > 0:
            return responses[0].strip()
        else:
            return "No summary available"
            
    except Exception as e:
        logger.warning(f"Failed to generate summary for {file_path}: {e}")
        return "Summary generation failed"


def count_max_backticks(content: str) -> int:
    """
    Count the maximum number of consecutive backticks in content.
    
    Args:
        content: The content to analyze
        
    Returns:
        Maximum number of consecutive backticks found
    """
    max_backticks = 0
    current_backticks = 0
    
    for char in content:
        if char == '`':
            current_backticks += 1
            max_backticks = max(max_backticks, current_backticks)
        else:
            current_backticks = 0
    
    return max_backticks


def build_context(
    directories: Optional[List[str]] = None,
    files: Optional[List[str]] = None,
    output_file: str = None,
    overview_text: Optional[str] = None,
    summarize_model: Optional[str] = None,
    ignore_patterns: Optional[List[str]] = None,
    base_directory: Optional[str] = None,
    current_working_directory: Optional[str] = None,
    include_line_numbers: bool = True
) -> str:
    """
    Build a context file from directories and/or specific files.
    
    Args:
        directories: Optional list of directory paths to include
        files: Optional list of specific file paths to include
        output_file: Path where the context file will be saved
        overview_text: Optional overview text to include at the top
        summarize_model: Optional model to use for file summarization
        ignore_patterns: Optional list of patterns to ignore
        base_directory: Optional base directory for relative path calculation
        current_working_directory: Optional current working directory for resolving relative paths
        include_line_numbers: Whether to include line numbers in file contents
        
    Returns:
        Path to the generated context file
    """
    # Validate that at least one of directories or files is provided
    if not directories and not files:
        raise ValueError("At least one of 'directories' or 'files' must be provided")
    
    logger.info(f"Building context from directories: {directories}, files: {files}")
    
    # Set current working directory if provided
    original_cwd = None
    if current_working_directory:
        import os
        original_cwd = os.getcwd()
        os.chdir(current_working_directory)
        logger.info(f"Changed working directory to: {current_working_directory}")
    
    try:
        # Set base directory for relative paths
        if base_directory:
            base_path = Path(base_directory)
        else:
            # Use the first directory as base, or current working directory
            if directories:
                base_path = Path(directories[0])
            elif files:
                base_path = Path(files[0]).parent
            else:
                base_path = Path.cwd()
        
        # Collect all files
        collected_files = collect_files(directories, files, ignore_patterns)
        logger.info(f"Collected {len(collected_files)} files")
        
        # Start building the markdown content
        content_lines = []
    
        # Add overview section if provided (without heading)
        if overview_text:
            content_lines.extend([
                overview_text,
                "",
            ])
        
        # Add files section
        content_lines.extend([
            "# Files",
            "",
        ])
    
        # Process each file
        for file_path in collected_files:
            try:
                # Calculate relative path from current working directory
                try:
                    relative_path = file_path.relative_to(Path.cwd())
                except ValueError:
                    # If file is not relative to cwd, use absolute path
                    relative_path = file_path
            
                # Read file content
                file_content = read_file_content(file_path, include_line_numbers)
                
                # Get language for syntax highlighting
                language = get_file_language(file_path)
                
                # Add file section
                content_lines.extend([
                    f"## {relative_path}",
                ])
                
                # Add summary section
                if summarize_model and not file_content.startswith("["):  # Skip if error reading file
                    summary = generate_file_summary(file_path, file_content, summarize_model)
                    content_lines.extend([
                        "### Summary",
                        summary,
                        "",
                    ])
                else:
                    content_lines.extend([
                        "### Summary",
                        "[No summary available]",
                        "",
                    ])
            
                
                # Add contents section
                content_lines.extend([
                    "### File Contents",
                ])
                
                # Add file content in code block
                # For markdown files, count max backticks and use one more to avoid conflicts
                if language == 'markdown':
                    max_backticks = count_max_backticks(file_content)
                    fence_backticks = '`' * (max_backticks + 1)
                    content_lines.extend([
                        f"{fence_backticks}{language}",
                        file_content,
                        fence_backticks,
                        "",
                    ])
                else:
                    content_lines.extend([
                        f"```{language}",
                        file_content,
                        "```",
                        "",
                    ])
                
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                content_lines.extend([
                    f"## {file_path}",
                    "",
                    f"[Error processing file: {str(e)}]",
                    "",
                ])
        
        # Write the context file
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content_lines))
        
        logger.info(f"Context file generated: {output_path}")
        return str(output_path)
        
    except Exception as e:
        logger.error(f"Error writing context file {output_file}: {e}")
        raise ValueError(f"Error writing context file: {str(e)}")
    finally:
        # Restore original working directory if it was changed
        if original_cwd:
            import os
            os.chdir(original_cwd)
            logger.info(f"Restored working directory to: {original_cwd}")
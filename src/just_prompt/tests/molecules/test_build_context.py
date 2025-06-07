"""
Tests for build_context functionality.
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path
from dotenv import load_dotenv
from just_prompt.molecules.build_context import build_context, collect_files, get_file_language, should_ignore_file

# Load environment variables
load_dotenv()


@pytest.fixture
def temp_directory():
    """Create a temporary directory with sample files for testing."""
    temp_dir = tempfile.mkdtemp()
    
    # Create sample directory structure
    src_dir = Path(temp_dir) / "src"
    src_dir.mkdir()
    
    # Create Python file
    (src_dir / "main.py").write_text("""
def hello_world():
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
""")
    
    # Create JavaScript file
    (src_dir / "app.js").write_text("""
function greet(name) {
    console.log(`Hello, ${name}!`);
}

greet("World");
""")
    
    # Create README
    (Path(temp_dir) / "README.md").write_text("""
# Test Project

This is a test project for build_context.
""")
    
    # Create .gitignore (should be ignored)
    (Path(temp_dir) / ".gitignore").write_text("__pycache__/\n*.pyc")
    
    # Create node_modules directory (should be ignored)
    node_modules = Path(temp_dir) / "node_modules"
    node_modules.mkdir()
    (node_modules / "some_package.js").write_text("// Package code")
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)




def test_get_file_language():
    """Test file language detection."""
    assert get_file_language(Path("test.py")) == "python"
    assert get_file_language(Path("test.js")) == "javascript"
    assert get_file_language(Path("test.ts")) == "typescript"
    assert get_file_language(Path("test.unknown")) == "text"
    assert get_file_language(Path("Dockerfile")) == "dockerfile"
    assert get_file_language(Path("Makefile")) == "makefile"
    
    # Test multiple extensions - should use the last known extension
    assert get_file_language(Path("config.yaml.example")) == "yaml"
    assert get_file_language(Path("app.js.backup")) == "javascript"
    assert get_file_language(Path("main.py.orig")) == "python"
    assert get_file_language(Path("script.sh.example")) == "bash"
    assert get_file_language(Path("unknown.xyz.example")) == "text"


def test_should_ignore_file():
    """Test file ignore logic."""
    ignore_patterns = ['.git', '__pycache__', 'node_modules', '*.pyc']
    
    assert should_ignore_file(Path("src/.git/config"), ignore_patterns) == True
    assert should_ignore_file(Path("src/__pycache__/test.pyc"), ignore_patterns) == True
    assert should_ignore_file(Path("node_modules/package.js"), ignore_patterns) == True
    assert should_ignore_file(Path("test.pyc"), ignore_patterns) == True
    assert should_ignore_file(Path("src/main.py"), ignore_patterns) == False
    assert should_ignore_file(Path("README.md"), ignore_patterns) == False


def test_collect_files(temp_directory):
    """Test file collection from directories."""
    files = collect_files(directories=[temp_directory])
    
    # Should collect Python, JavaScript, and Markdown files
    file_names = [f.name for f in files]
    assert "main.py" in file_names
    assert "app.js" in file_names
    assert "README.md" in file_names
    
    # Should ignore .gitignore and node_modules
    assert ".gitignore" not in file_names
    assert "some_package.js" not in file_names


def test_collect_files_nonexistent_directory():
    """Test collection from non-existent directory."""
    files = collect_files(directories=["/nonexistent/directory"])
    assert files == []


def test_collect_files_with_specific_files(temp_directory):
    """Test file collection with specific files."""
    src_dir = Path(temp_directory) / "src"
    main_py = src_dir / "main.py"
    readme_md = Path(temp_directory) / "README.md"
    
    files = collect_files(files=[str(main_py), str(readme_md)])
    
    # Should collect only the specified files
    file_names = [f.name for f in files]
    assert "main.py" in file_names
    assert "README.md" in file_names
    assert "app.js" not in file_names  # Not specified, so not included


def test_collect_files_mixed_dirs_and_files(temp_directory):
    """Test file collection with both directories and specific files."""
    src_dir = Path(temp_directory) / "src" 
    readme_md = Path(temp_directory) / "README.md"
    
    # Create an additional file outside src
    extra_file = Path(temp_directory) / "extra.txt"
    extra_file.write_text("Extra content")
    
    files = collect_files(directories=[str(src_dir)], files=[str(readme_md), str(extra_file)])
    
    file_names = [f.name for f in files]
    # Should include files from src directory
    assert "main.py" in file_names
    assert "app.js" in file_names
    # Should include specified files
    assert "README.md" in file_names
    assert "extra.txt" in file_names


def test_collect_files_no_input():
    """Test collection with no directories or files specified."""
    files = collect_files()
    assert files == []


def test_build_context_basic(temp_directory):
    """Test basic context building without LLM summarization."""
    output_file = Path(temp_directory) / "context.md"
    
    result_path = build_context(
        directories=[temp_directory],
        output_file=str(output_file)
    )
    
    assert result_path == str(output_file)
    assert output_file.exists()
    
    content = output_file.read_text()
    
    # Check that files section exists
    assert "# Files" in content
    
    # Check that Python file is included
    assert "main.py" in content
    assert "def hello_world():" in content
    assert "```python" in content
    
    # Check that JavaScript file is included
    assert "app.js" in content
    assert "function greet(name)" in content
    assert "```javascript" in content
    
    # Check that README is included
    assert "README.md" in content
    assert "# Test Project" in content


def test_build_context_with_overview(temp_directory):
    """Test context building with overview text."""
    output_file = Path(temp_directory) / "context_with_overview.md"
    overview_text = """
This project demonstrates the build_context functionality.

It includes sample Python and JavaScript files to test the context building process.
"""
    
    result_path = build_context(
        directories=[temp_directory],
        output_file=str(output_file),
        overview_text=overview_text
    )
    
    assert result_path == str(output_file)
    assert output_file.exists()
    
    content = output_file.read_text()
    
    # Check that overview text exists (without heading)
    assert "This project demonstrates" in content
    
    # Check that files section comes after overview
    overview_pos = content.find("This project demonstrates")
    files_pos = content.find("# Files")
    assert overview_pos < files_pos


def test_build_context_with_specific_files(temp_directory):
    """Test context building with specific files."""
    output_file = Path(temp_directory) / "context_specific_files.md"
    src_dir = Path(temp_directory) / "src"
    main_py = src_dir / "main.py"
    
    result_path = build_context(
        files=[str(main_py)],
        output_file=str(output_file)
    )
    
    assert result_path == str(output_file)
    assert output_file.exists()
    
    content = output_file.read_text()
    
    # Should include the specified file
    assert "main.py" in content
    assert "def hello_world():" in content
    
    # Should not include other files
    assert "app.js" not in content
    assert "README.md" not in content


def test_build_context_mixed_dirs_and_files(temp_directory):
    """Test context building with both directories and specific files."""
    output_file = Path(temp_directory) / "context_mixed.md"
    src_dir = Path(temp_directory) / "src"
    readme_md = Path(temp_directory) / "README.md"
    
    # Create an additional file
    extra_file = Path(temp_directory) / "extra.py"
    extra_file.write_text("# Extra Python file\nprint('extra')")
    
    result_path = build_context(
        directories=[str(src_dir)],
        files=[str(readme_md), str(extra_file)],
        output_file=str(output_file)
    )
    
    assert result_path == str(output_file)
    assert output_file.exists()
    
    content = output_file.read_text()
    
    # Should include files from directory
    assert "main.py" in content
    assert "app.js" in content
    
    # Should include specified files
    assert "README.md" in content
    assert "extra.py" in content


def test_build_context_with_custom_ignore(temp_directory):
    """Test context building with custom ignore patterns."""
    output_file = Path(temp_directory) / "context_custom_ignore.md"
    
    # Ignore Python files
    custom_ignore = ["*.py"]
    
    result_path = build_context(
        directories=[temp_directory],
        output_file=str(output_file),
        ignore_patterns=custom_ignore
    )
    
    assert result_path == str(output_file)
    assert output_file.exists()
    
    content = output_file.read_text()
    
    # Python file should be ignored
    assert "main.py" not in content
    
    # JavaScript file should still be included
    assert "app.js" in content


def test_build_context_with_base_directory(temp_directory):
    """Test context building with custom base directory."""
    output_file = Path(temp_directory) / "context_base_dir.md"
    src_dir = Path(temp_directory) / "src"
    
    result_path = build_context(
        directories=[str(src_dir)],
        output_file=str(output_file),
        base_directory=temp_directory
    )
    
    assert result_path == str(output_file)
    assert output_file.exists()
    
    content = output_file.read_text()
    
    # Should show relative paths from base directory
    assert "src/main.py" in content
    assert "src/app.js" in content


def test_build_context_error_handling():
    """Test error handling for invalid inputs."""
    # Test writing to a truly invalid path (no permissions)
    with pytest.raises(ValueError):
        build_context(
            directories=["/nonexistent"],
            output_file="/proc/invalid/cannot/create/context.md"
        )
    
    # Test validation that at least one of directories or files is provided
    with pytest.raises(ValueError, match="At least one of 'directories' or 'files' must be provided"):
        build_context(output_file="test.md")


def test_build_context_with_llm_summarization(temp_directory):
    """Test context building with LLM summarization (requires API key)."""
    # Skip if no API key available
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not available for LLM summarization test")
    
    output_file = Path(temp_directory) / "context_with_summary.md"
    
    result_path = build_context(
        directories=[temp_directory],
        output_file=str(output_file),
        summarize_model="openai:gpt-4o-mini"
    )
    
    assert result_path == str(output_file)
    assert output_file.exists()
    
    content = output_file.read_text()
    
    # Check that summary sections exist (the actual format used)
    assert "### Summary" in content
    # Ensure we don't have the fallback message
    assert "[No summary available]" not in content


def test_empty_directory():
    """Test with empty directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        output_file = Path(temp_dir) / "empty_context.md"
        
        result_path = build_context(
            directories=[temp_dir],
            output_file=str(output_file)
        )
        
        assert result_path == str(output_file)
        assert output_file.exists()
        
        content = output_file.read_text()
        assert "# Files" in content
        # Should have minimal content for empty directory
        assert len(content.strip()) < 100
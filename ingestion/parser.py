import ast
from config import CHUNK_SIZE


def parse_python_file(content: str, file_path: str) -> list[dict]:
    """Parse Python file into chunks using AST."""
    
    chunks = []
    
    try:
        tree = ast.parse(content)
    except SyntaxError:
        # If AST fails, fall back to simple chunking
        return simple_chunk(content, file_path)
    
    lines = content.split("\n")
    
    for node in ast.walk(tree):
        # Extract functions
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            start_line = node.lineno - 1
            end_line = node.end_lineno
            chunk_content = "\n".join(lines[start_line:end_line])
            
            # Get docstring if exists
            docstring = ast.get_docstring(node) or ""
            
            chunks.append({
                "content": chunk_content,
                "type": "function",
                "name": node.name,
                "file_path": file_path,
                "start_line": node.lineno,
                "end_line": end_line,
                "docstring": docstring
            })
        
        # Extract classes
        elif isinstance(node, ast.ClassDef):
            start_line = node.lineno - 1
            end_line = node.end_lineno
            chunk_content = "\n".join(lines[start_line:end_line])
            
            docstring = ast.get_docstring(node) or ""
            
            chunks.append({
                "content": chunk_content,
                "type": "class",
                "name": node.name,
                "file_path": file_path,
                "start_line": node.lineno,
                "end_line": end_line,
                "docstring": docstring
            })
    
    # If no functions/classes found, chunk the whole file
    if not chunks:
        return simple_chunk(content, file_path)
    
    return chunks


def simple_chunk(content: str, file_path: str) -> list[dict]:
    """Fallback: chunk by character limit."""
    
    chunks = []
    lines = content.split("\n")
    
    current_chunk = []
    current_size = 0
    start_line = 1
    
    for i, line in enumerate(lines, 1):
        current_chunk.append(line)
        current_size += len(line) + 1
        
        if current_size >= CHUNK_SIZE:
            chunks.append({
                "content": "\n".join(current_chunk),
                "type": "code_block",
                "name": f"block_{len(chunks) + 1}",
                "file_path": file_path,
                "start_line": start_line,
                "end_line": i,
                "docstring": ""
            })
            current_chunk = []
            current_size = 0
            start_line = i + 1
    
    # Add remaining
    if current_chunk:
        chunks.append({
            "content": "\n".join(current_chunk),
            "type": "code_block",
            "name": f"block_{len(chunks) + 1}",
            "file_path": file_path,
            "start_line": start_line,
            "end_line": len(lines),
            "docstring": ""
        })
    
    return chunks


def parse_file(content: str, file_path: str, extension: str) -> list[dict]:
    """Route to appropriate parser based on file type."""
    
    if extension == ".py":
        return parse_python_file(content, file_path)
    else:
        # For non-Python files, use simple chunking for now
        return simple_chunk(content, file_path)


def parse_all_files(files: list[dict]) -> list[dict]:
    """Parse all files and return chunks."""
    
    all_chunks = []
    
    for file in files:
        chunks = parse_file(
            content=file["content"],
            file_path=file["path"],
            extension=file["extension"]
        )
        all_chunks.extend(chunks)
    
    print(f"Created {len(all_chunks)} chunks from {len(files)} files")
    return all_chunks
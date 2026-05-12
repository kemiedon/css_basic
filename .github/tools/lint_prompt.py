# -*- coding: utf-8 -*-
import sys
import re
import os

def check_prompt_file(file_path):
    print(f"Linting: {file_path}...")
    errors = []
    warnings = []

    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')

    # --- 1. Metadata (YAML Frontmatter) Check ---
    if not content.startswith('---\n'):
        errors.append("Header: Missing YAML frontmatter (must start with '---')")
    else:
        # Safe-ish split for frontmatter
        parts = content.split('---')
        if len(parts) < 3:
             errors.append("Header: Malformed YAML frontmatter")
        else:
             yaml_content = parts[1]
             required_fields = ['name:', 'description:', 'model:']
             for field in required_fields:
                 if field not in yaml_content:
                     errors.append(f"Header: Metadata missing required field '{field}'")

             # Check for English descriptions in YAML (basic check)
             desc_lines = [l for l in yaml_content.split('\n') if 'description:' in l]
             if desc_lines:
                 desc_val = desc_lines[0].split(':', 1)[1].strip()
                 if re.search(r'[a-zA-Z]{5,}', desc_val) and not re.search(r'[\u4e00-\u9fa5]', desc_val):
                     warnings.append("Header: Description seems to be English. Guide requires Chinese.")

    # --- 2. Logic Keywords Check ---
    # Keywords: MUST, MUST NOT, IF, THEN, ELSE (from Appendix A)
    # Check if they appear in the file body (skipping top metadata)
    body_content = content.replace(parts[1], '') if len(parts) >= 3 else content

    keywords = ['MUST', 'MUST NOT', 'IF', 'THEN', 'ELSE']
    found_keywords = {kw: 0 for kw in keywords}
    for kw in keywords:
        found_keywords[kw] = len(re.findall(r'\b' + kw + r'\b', body_content))

    if sum(found_keywords.values()) == 0:
        warnings.append("Logic: No logical keywords found (MUST, IF, THEN). Ensure strict logic rules are defined.")

    # --- 3. Line-by-line Checks ---
    in_function_block = False
    current_step_name = "Header"
    in_code_block = False

    # White-listed Tool IDs (Standardized)
    VALID_TOOLS = [
        "agent/runSubagent",
        "edit/createDirectory", "edit/createFile", "edit/createJupyterNotebook",
        "edit/applyPatch", "edit/editNotebook", "edit/replaceStringInFile",
        "execute/createAndRunTask", "execute/getTerminalOutput", "execute/runInTerminal",
        "execute/runNotebookCell", "execute/runTask", "execute/runTests", "execute/testFailure",
        "read/getNotebookSummary", "read/getTaskOutput", "read/problems", "read/readFile",
        "read/readNotebookCellOutput", "read/terminalLastCommand", "read/terminalSelection",
        "search/changes", "search/codebase", "search/fileSearch", "search/listDirectory",
        "search/searchResults", "search/textSearch", "search/usage",
        "todo/todo",
        "vscode/extensions", "vscode/getProjectSetupInfo", "vscode/installExtension",
        "vscode/newWorkspace", "vscode/openSimpleBrowser", "vscode/runCommand", "vscode/vscodeAPI",
        "web/fetch", "web/githubRepo"
    ]

    for i, line in enumerate(lines):
        line_num = i + 1
        stripped = line.strip()

        # Track Markdown Code Blocks
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            continue

        if stripped.startswith('# STEP'):
            current_step_name = stripped
            in_function_block = False
            # Reset tool tracking for new step
            step_tool_count = 0

        elif stripped.startswith('FUNCTION'):
            in_function_block = True

        # RULE: Multi-tool Detection within one STEP/FUNCTION
        # Guide: "Split Multi-Tool Steps". One STEP should optimally use only 1 tool type.
        # Heuristic: Count lines starting with "- 工具:" inside a function block
        if in_function_block and stripped.startswith('- 工具:'):
             step_tool_count = locals().get('step_tool_count', 0) + 1

             # Extract Tool Name
             # Format: "- 工具: `tool_name`" or "- 工具: tool_name"
             tool_match = re.search(r'-\s*工具:\s*[`]?([^`\s]+)[`]?', stripped)
             if tool_match:
                 tool_name = tool_match.group(1).strip()
                 if tool_name not in VALID_TOOLS and tool_name != "(None)":
                      # Allow (None) if explicitly stated, though guide says omit line.
                      # Check if close match exists? No, strict check.
                      errors.append(f"Line {line_num}: [Standard] Invalid tool name '{tool_name}'. Must use standard format (e.g. 'execute/runInTerminal'). See Appendix B in standards.")

             if step_tool_count > 1:
                 # Warning only, as legacy files might use it. Ideally Error.
                 # Guide says "MUST split". Let's make it an Error to enforce standard.
                 errors.append(f"Line {line_num} in [{current_step_name}]: Multiple tool definitions detected. Per 'Multi-Tool Split Principle', split this into separate steps (e.g., Step X-1, Step X-2).")


        # RULE: No Backticks around [[...]]
        # Pattern: `[[...]]`
        if re.search(r'`\[\[.*?\]\]`', line):
            errors.append(f"Line {line_num}: [Style] Redundant backticks around wiki-link. Use [[...]] directly, not `[[...]]`.")

        # RULE: Visual Style - Forbidden Bold **text**
        # Strict ban on ALL bold text. Use [[...]] for references.
        # First remove inline code to avoid false positives
        line_no_code = re.sub(r'`[^`]+`', '', line)
        if '**' in line_no_code:
             # Find all **match**
             matches = re.finditer(r'\*\*(.*?)\*\*', line_no_code)
             for m in matches:
                 inner = m.group(1)
                 errors.append(f"Line {line_num}: [Style] Forbidden bold text '**{inner}**'. Use '[[{inner}]]' for references, or backticks for code values.")

        # RULE: Internal Reference Check
        # Keywords like STEP N or 附錄 X MUST be wrapped in [[...]]
        # Exception 1: Headers starting with #
        # Exception 2: Workflow list items (e.g. "1. STEP 1: ...")
        # Exception 3: Metadata (e.g. name: one-file) - though covered by line_num check mostly
        if not stripped.startswith('#') and not re.match(r'^\d+\.\s+STEP', stripped):
             # Regex: Look for STEP N or 附錄 X that are NOT preceded by [[
             # Note: Python lookbehind requires fixed width. [[ is 2 chars.
             unlinked_refs = re.finditer(r'(?<!\[\[)(STEP\s+\d+|附錄\s+[A-Z])', line_no_code, re.IGNORECASE)
             for m in unlinked_refs:
                 ref = m.group(1)
                 errors.append(f"Line {line_num}: [Style] Unlinked internal reference '{ref}'. Must be wrapped in [[...]]. Example: [[{ref}: Name]].")
                 ref = m.group(1)
                 # print(f"DEBUG: Found {ref} in {line_num}: {line}")
                 errors.append(f"Line {line_num}: [Style] Unlinked internal reference '{ref}'. Must be wrapped in [[...]]. Example: [[{ref}: Name]].")

        # RULE: Nesting Depth Check (Strict Error)
        # We strictly prohibit nesting > 1 level (8 spaces).
        # Philosophy: If it needs nesting, it needs a separate Function/Step.
        if stripped.startswith('-'):
            leading_spaces = len(line) - len(line.lstrip())
            # If 8 spaces or more (and it's a list item), it's nested
            if leading_spaces >= 8:
                 errors.append(f"Line {line_num} in [{current_step_name}]: Deep nesting detected (Indent: {leading_spaces}). Forbidden. Split into separate FUNCTIONs or flatten logic.")

        # RULE: English Translations in Parentheses (Forbidden)
        # Context: "中文 (English)" or "中文(English)"
        # Pattern matches: Chinese char -> optional space -> ( -> English words -> )
        # Exclude common patterns like (H4), (Preview), (copilot)
        if line_num > 10: # Skip metadata lines basically
            # Regex Explanation:
            # [\u4e00-\u9fa5] : Chinese character
            # \s* : Optional space
            # \( : Opening paren
            # [A-Za-z\s]+ : English text (letters and spaces)
            # \) : Closing paren
            matches = re.finditer(r'[\u4e00-\u9fa5]+\s*(\([A-Za-z\s]+\))', line_no_code)
            for m in matches:
                english_part = m.group(1)
                inner_text = english_part.strip('()').strip()

                # Whitelist / False Positive Filter
                # Allow single words if they are likely technical acronyms or very short?
                # But guide says "No English translation". "Iteration Logic" is 2 words.
                # Let's filter out known safe words if needed, or just flag all.

                # Heuristic: If it has spaces, it's likely a phrase/translation -> FLag it
                # If it's a single word, maybe check length. "Preview" (7 chars).

                if ' ' in inner_text or len(inner_text) > 3:
                     # Allow 'copilot' (case insensitive check done below if needed, but regex is A-Za-z)
                     if inner_text.lower() not in ['preview', 'copilot', 'phase2']:
                        errors.append(f"Line {line_num}: [Style] Potential English translation found: '{english_part}'. Guide forbids English translations/explanations in parentheses.")

    # --- Report ---
    print("\n=== Prompt Quality Check ===\n")
    if warnings:
        print("Warnings (Best Practices):")
        for w in warnings:
            print(f"  [!] {w}")
        print("")

    if errors:
        print("FAIL: Critical issues found. Please fix them before committing.")
        for e in errors:
            print(f"  [x] {e}")
        sys.exit(1)
    else:
        print("PASS: Prompt file looks good.")
        sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python lint_prompt.py <file_path>")
        sys.exit(1)

    check_prompt_file(sys.argv[1])

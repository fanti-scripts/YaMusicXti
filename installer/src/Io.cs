using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

namespace YMBG
{
    /// <summary>Файловые операции с повторами: клиент не всегда отпускает файлы сразу.</summary>
    internal static class Io
    {
        private const int MoveReplaceExisting = 0x1;

        [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode, EntryPoint = "MoveFileExW")]
        private static extern bool MoveFileEx(string existingFileName, string newFileName, int flags);

        public static void CopyRetry(string src, string dst, int attempts, int delayMs)
        {
            for (int i = 0; ; i++)
            {
                try
                {
                    File.Copy(src, dst, true);
                    return;
                }
                catch (Exception ex)
                {
                    if (!(ex is IOException) && !(ex is UnauthorizedAccessException))
                    {
                        throw;
                    }
                    if (i >= attempts - 1)
                    {
                        throw;
                    }
                    Thread.Sleep(delayMs);
                }
            }
        }

        public static void CopyRetry(string src, string dst)
        {
            CopyRetry(src, dst, 60, 250);
        }

        /// <summary>Атомарная замена файла (аналог os.replace).</summary>
        public static void ReplaceRetry(string src, string dst, int attempts, int delayMs)
        {
            for (int i = 0; ; i++)
            {
                if (MoveFileEx(src, dst, MoveReplaceExisting))
                {
                    return;
                }
                int err = Marshal.GetLastWin32Error();
                if (err == 2)
                {
                    throw new FileNotFoundException("Не найден файл для замены: " + src);
                }
                if (i >= attempts - 1)
                {
                    throw new IOException("Не удалось заменить файл (код " + err + "): " + dst);
                }
                Thread.Sleep(delayMs);
            }
        }

        public static void ReplaceRetry(string src, string dst)
        {
            ReplaceRetry(src, dst, 60, 250);
        }

        public static void WriteByteRetry(string path, long offset, byte value, int attempts, int delayMs)
        {
            for (int i = 0; ; i++)
            {
                try
                {
                    using (FileStream fs = new FileStream(path, FileMode.Open, FileAccess.Write, FileShare.None))
                    {
                        fs.Seek(offset, SeekOrigin.Begin);
                        fs.WriteByte(value);
                        fs.Flush(true);
                    }
                    return;
                }
                catch (Exception ex)
                {
                    if (!(ex is IOException) && !(ex is UnauthorizedAccessException))
                    {
                        throw;
                    }
                    if (i >= attempts - 1)
                    {
                        throw;
                    }
                    Thread.Sleep(delayMs);
                }
            }
        }

        public static void WriteTextUtf8(string path, string text)
        {
            string tmp = path + ".tmp";
            File.WriteAllText(tmp, text, new UTF8Encoding(false));
            try
            {
                ReplaceRetry(tmp, path, 40, 100);
            }
            finally
            {
                DeleteQuiet(tmp);
            }
        }

        public static void DeleteQuiet(string path)
        {
            try
            {
                if (File.Exists(path))
                {
                    File.Delete(path);
                }
            }
            catch
            {
                // не критично
            }
        }

        public static int IndexOf(byte[] haystack, byte[] needle)
        {
            return IndexOf(haystack, haystack.Length, needle, 0);
        }

        public static int IndexOf(byte[] haystack, int count, byte[] needle, int start)
        {
            if (needle.Length == 0)
            {
                return -1;
            }
            int limit = count - needle.Length;
            for (int i = start; i <= limit; i++)
            {
                if (haystack[i] != needle[0])
                {
                    continue;
                }
                int j = 1;
                while (j < needle.Length && haystack[i + j] == needle[j])
                {
                    j++;
                }
                if (j == needle.Length)
                {
                    return i;
                }
            }
            return -1;
        }
    }
}

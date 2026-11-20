using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Text;

namespace YaMusicXti
{
    internal sealed class AsarEntry
    {
        public string Path;
        public JObj Meta;
        public int Order;
    }

    internal sealed class AsarArchive
    {
        public JObj Header;
        public long DataStart;
        public byte[] Data;
    }

    /// <summary>Чтение и запись Electron app.asar, наложение и снятие патча.</summary>
    internal static class Asar
    {
        private const int BlockSize = 4 * 1024 * 1024;
        private const int MaxHeaderSize = 64 * 1024 * 1024;

        private static readonly byte[] MarkerBytes = Encoding.UTF8.GetBytes(Payload.Marker);
        private static readonly byte[] MarkerVersionBytes = Encoding.UTF8.GetBytes(Payload.MarkerVersion);

        public static AsarArchive Read(string path)
        {
            using (FileStream fs = OpenRead(path))
            {
                long dataStart;
                JObj header = ReadHeader(fs, out dataStart);
                long len = fs.Length - dataStart;
                if (len < 0 || len > int.MaxValue)
                {
                    throw new InvalidDataException("некорректный размер данных app.asar");
                }
                byte[] data = new byte[(int)len];
                fs.Position = dataStart;
                ReadExact(fs, data, 0, data.Length);
                AsarArchive archive = new AsarArchive();
                archive.Header = header;
                archive.DataStart = dataStart;
                archive.Data = data;
                return archive;
            }
        }

        public static byte[] ReadEntry(string path, string innerPath)
        {
            using (FileStream fs = OpenRead(path))
            {
                long dataStart;
                JObj header = ReadHeader(fs, out dataStart);
                JObj meta = FindNode(header, innerPath);
                if (meta == null)
                {
                    return null;
                }
                return ReadMeta(fs, dataStart, meta);
            }
        }

        public static string Version(string asarPath)
        {
            try
            {
                byte[] raw = ReadEntry(asarPath, "package.json");
                return ParseVersion(raw);
            }
            catch (FileNotFoundException)
            {
                return null;
            }
            catch (DirectoryNotFoundException)
            {
                return null;
            }
        }

        public static string Version(AsarArchive archive)
        {
            return ParseVersion(Extract(archive, "package.json"));
        }

        private static string ParseVersion(byte[] raw)
        {
            if (raw == null)
            {
                return null;
            }
            object parsed;
            if (!Json.TryParse(Encoding.UTF8.GetString(raw), out parsed))
            {
                return null;
            }
            JObj obj = parsed as JObj;
            if (obj == null)
            {
                return null;
            }
            return obj.GetString("version");
        }

        public static byte[] Extract(AsarArchive archive, string innerPath)
        {
            JObj meta = FindNode(archive.Header, innerPath);
            if (meta == null)
            {
                return null;
            }
            object rawOffset = meta.Get("offset");
            object rawSize = meta.Get("size");
            if (rawOffset == null || rawSize == null)
            {
                return null;
            }
            long offset = Num(rawOffset);
            long size = Num(rawSize);
            if (offset < 0 || size < 0 || offset + size > archive.Data.Length)
            {
                throw new InvalidDataException("битые границы файла в app.asar: " + innerPath);
            }
            byte[] buf = new byte[(int)size];
            Buffer.BlockCopy(archive.Data, (int)offset, buf, 0, (int)size);
            return buf;
        }

        /// <summary>Накладывает патч. Возвращает true, если патч в итоге на месте.</summary>
        public static bool Apply(string asarPath, Action<string> log)
        {
            string backup = asarPath + ".orig";
            string version = Version(asarPath);
            string versionLabel = version == null ? "" : " (версия " + version + ")";

            byte[] currentIndex = ReadEntry(asarPath, "index.js");
            bool patched = currentIndex != null && Io.IndexOf(currentIndex, MarkerBytes) >= 0;
            bool current = patched && Io.IndexOf(currentIndex, MarkerVersionBytes) >= 0;

            if (current)
            {
                log("Патч app.asar уже актуален" + versionLabel + ".");
                return true;
            }

            bool backupOk = false;
            if (File.Exists(backup))
            {
                try
                {
                    backupOk = string.Equals(Version(backup), version, StringComparison.Ordinal);
                }
                catch
                {
                    backupOk = false;
                }
            }

            if (!backupOk)
            {
                if (patched)
                {
                    throw new InvalidOperationException(
                        "app.asar уже пропатчен, а подходящей чистой копии app.asar.orig нет. " +
                        "Переустановите Яндекс Музыку и запустите установщик снова.");
                }
                long size = new FileInfo(asarPath).Length;
                EnsureFreeSpace(asarPath, size + 16L * 1024 * 1024, "бэкапа");
                Io.CopyRetry(asarPath, backup);
                log("Создан бэкап оригинала: app.asar.orig");
            }

            AsarArchive src;
            try
            {
                src = Read(backup);
            }
            catch (Exception ex)
            {
                throw new InvalidOperationException("Не удалось прочитать app.asar.orig: " + ex.Message, ex);
            }

            string indexJs = DecodeUtf8(Extract(src, "index.js") ?? new byte[0]);
            if (indexJs.IndexOf(Payload.Marker, StringComparison.Ordinal) >= 0)
            {
                throw new InvalidOperationException(
                    "Копия app.asar.orig уже содержит патч. Переустановите Яндекс Музыку, чтобы получить чистые файлы.");
            }
            if (indexJs.IndexOf(Payload.AnchorFunc, StringComparison.Ordinal) < 0)
            {
                throw new InvalidOperationException(
                    "Не нашёл место для вставки кода в index.js. Похоже, версия клиента сильно изменилась.");
            }

            indexJs = ReplaceFirst(
                indexJs,
                Payload.AnchorFunc,
                "// " + Payload.MarkerVersion + "\n" + Payload.InjectFunc + "\n" + Payload.AnchorFunc);

            string hook = Payload.AnchorHandler + "\n    " + Payload.AnchorInsert;
            if (indexJs.IndexOf(hook, StringComparison.Ordinal) < 0)
            {
                throw new InvalidOperationException(
                    "Не нашёл место для панели «Фон» в index.js. Похоже, версия клиента сильно изменилась.");
            }
            indexJs = ReplaceFirst(
                indexJs,
                hook,
                Payload.AnchorHandler + "\n    " + Payload.Marker + "(webContents);\n    " + Payload.AnchorInsert);

            List<AsarEntry> entries = CollectFiles(src.Header);
            entries.Sort(delegate(AsarEntry a, AsarEntry b)
            {
                int cmp = Num(a.Meta.Get("offset")).CompareTo(Num(b.Meta.Get("offset")));
                return cmp != 0 ? cmp : a.Order.CompareTo(b.Order);
            });

            List<byte[]> blobs = new List<byte[]>(entries.Count);
            int indexPos = -1;
            for (int i = 0; i < entries.Count; i++)
            {
                blobs.Add(Extract(src, entries[i].Path) ?? new byte[0]);
                if (entries[i].Path == "index.js")
                {
                    indexPos = i;
                }
            }
            if (indexPos < 0)
            {
                throw new InvalidOperationException("В app.asar нет index.js — патчить нечего.");
            }

            long total = 0;
            for (int i = 0; i < entries.Count; i++)
            {
                total += blobs[i].Length;
            }
            EnsureFreeSpace(asarPath, total + 32L * 1024 * 1024, "нового app.asar");

            blobs[indexPos] = Encoding.UTF8.GetBytes(indexJs);
            long offset = 0;
            for (int i = 0; i < entries.Count; i++)
            {
                JObj meta = entries[i].Meta;
                meta.Set("size", new JNum(blobs[i].Length));
                // offset в asar — строка; так же пишет и старый Python-патчер
                meta.Set("offset", offset.ToString(CultureInfo.InvariantCulture));
                meta.Set("integrity", Integrity(blobs[i]));
                offset += blobs[i].Length;
            }

            string tmp = asarPath + ".new";
            try
            {
                WriteArchive(tmp, src.Header, entries, blobs);
                Io.ReplaceRetry(tmp, asarPath);
            }
            finally
            {
                Io.DeleteQuiet(tmp);
            }

            log("Патч app.asar применён" + versionLabel + ".");
            return true;
        }

        public static void Restore(string asarPath, Action<string> log)
        {
            string backup = asarPath + ".orig";
            if (!File.Exists(backup))
            {
                throw new InvalidOperationException(
                    "Нет бэкапа app.asar.orig — вернуть оригинал без него нельзя. " +
                    "Переустановите Яндекс Музыку.");
            }
            string tmp = asarPath + ".restore.tmp";
            try
            {
                Io.CopyRetry(backup, tmp);
                Io.ReplaceRetry(tmp, asarPath);
            }
            finally
            {
                Io.DeleteQuiet(tmp);
            }
            log("Оригинальный app.asar восстановлен.");
        }

        private static FileStream OpenRead(string path)
        {
            return new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
        }

        private static JObj ReadHeader(FileStream fs, out long dataStart)
        {
            long total = fs.Length;
            if (total < 16)
            {
                throw new InvalidDataException("app.asar слишком мал");
            }
            byte[] head = new byte[16];
            fs.Position = 0;
            ReadExact(fs, head, 0, head.Length);
            uint headerSize = BitConverter.ToUInt32(head, 4);
            if (headerSize < 8 || headerSize > MaxHeaderSize || 8L + headerSize > total)
            {
                throw new InvalidDataException("некорректный заголовок app.asar");
            }
            byte[] hdr = new byte[(int)headerSize];
            fs.Position = 8;
            ReadExact(fs, hdr, 0, hdr.Length);

            int start = Io.IndexOf(hdr, new byte[] { (byte)'{' });
            if (start < 0)
            {
                throw new InvalidDataException("в заголовке app.asar нет JSON");
            }
            object parsed;
            if (!Json.TryParse(Encoding.UTF8.GetString(hdr, start, hdr.Length - start), out parsed))
            {
                throw new InvalidDataException("не удалось разобрать заголовок app.asar");
            }
            JObj header = parsed as JObj;
            if (header == null)
            {
                throw new InvalidDataException("заголовок app.asar не является объектом");
            }
            dataStart = 8 + (long)headerSize;
            return header;
        }

        private static byte[] ReadMeta(FileStream fs, long dataStart, JObj meta)
        {
            object rawOffset = meta.Get("offset");
            object rawSize = meta.Get("size");
            if (rawOffset == null || rawSize == null)
            {
                return null;
            }
            long offset = Num(rawOffset);
            long size = Num(rawSize);
            if (offset < 0 || size < 0 || dataStart + offset + size > fs.Length)
            {
                throw new InvalidDataException("битые границы файла в app.asar");
            }
            byte[] buf = new byte[(int)size];
            fs.Position = dataStart + offset;
            ReadExact(fs, buf, 0, buf.Length);
            return buf;
        }

        private static JObj FindNode(JObj header, string path)
        {
            JObj node = header;
            string[] parts = path.Split('/');
            for (int i = 0; i < parts.Length; i++)
            {
                JObj files = node.GetObj("files");
                if (files == null)
                {
                    return null;
                }
                node = files.GetObj(parts[i]);
                if (node == null)
                {
                    return null;
                }
            }
            return node;
        }

        private static List<AsarEntry> CollectFiles(JObj header)
        {
            List<AsarEntry> list = new List<AsarEntry>();
            CollectInto(header, "", list);
            return list;
        }

        private static void CollectInto(JObj node, string prefix, List<AsarEntry> list)
        {
            JObj files = node.GetObj("files");
            if (files == null)
            {
                return;
            }
            for (int i = 0; i < files.Items.Count; i++)
            {
                string name = files.Items[i].Key;
                JObj child = files.Items[i].Value as JObj;
                if (child == null)
                {
                    continue;
                }
                string path = prefix.Length == 0 ? name : prefix + "/" + name;
                if (child.GetObj("files") != null)
                {
                    CollectInto(child, path, list);
                    continue;
                }
                // Распакованные (unpacked) файлы лежат вне asar — их не трогаем.
                if (child.Get("offset") == null || child.Get("size") == null)
                {
                    continue;
                }
                AsarEntry entry = new AsarEntry();
                entry.Path = path;
                entry.Meta = child;
                entry.Order = list.Count;
                list.Add(entry);
            }
        }

        private static void WriteArchive(string path, JObj header, List<AsarEntry> entries, List<byte[]> blobs)
        {
            byte[] json = Encoding.UTF8.GetBytes(Json.Stringify(header));
            int pad = (4 - ((4 + json.Length) % 4)) % 4;
            int strPayloadLen = 4 + json.Length + pad;
            int headerLen = 4 + strPayloadLen;

            using (FileStream fs = new FileStream(path, FileMode.Create, FileAccess.Write, FileShare.None, 1 << 20))
            {
                byte[] prefix = new byte[8];
                WriteU32(prefix, 0, 4u);
                WriteU32(prefix, 4, (uint)headerLen);
                fs.Write(prefix, 0, prefix.Length);

                byte[] lenBuf = new byte[4];
                WriteU32(lenBuf, 0, (uint)strPayloadLen);
                fs.Write(lenBuf, 0, lenBuf.Length);
                WriteU32(lenBuf, 0, (uint)json.Length);
                fs.Write(lenBuf, 0, lenBuf.Length);
                fs.Write(json, 0, json.Length);
                if (pad > 0)
                {
                    fs.Write(new byte[pad], 0, pad);
                }
                for (int i = 0; i < entries.Count; i++)
                {
                    fs.Write(blobs[i], 0, blobs[i].Length);
                }
            }
        }

        private static JObj Integrity(byte[] buf)
        {
            List<object> blocks = new List<object>();
            for (int offset = 0; offset < buf.Length; offset += BlockSize)
            {
                int len = Math.Min(BlockSize, buf.Length - offset);
                blocks.Add(Hex(Sha256(buf, offset, len)));
            }
            JObj obj = new JObj();
            obj.Set("algorithm", "SHA256");
            obj.Set("hash", Hex(Sha256(buf, 0, buf.Length)));
            obj.Set("blockSize", new JNum(BlockSize));
            obj.Set("blocks", blocks);
            return obj;
        }

        private static byte[] Sha256(byte[] buf, int offset, int count)
        {
            using (SHA256 sha = SHA256.Create())
            {
                return sha.ComputeHash(buf, offset, count);
            }
        }

        private static string Hex(byte[] bytes)
        {
            StringBuilder sb = new StringBuilder(bytes.Length * 2);
            for (int i = 0; i < bytes.Length; i++)
            {
                sb.Append(bytes[i].ToString("x2", CultureInfo.InvariantCulture));
            }
            return sb.ToString();
        }

        private static void WriteU32(byte[] buf, int offset, uint value)
        {
            buf[offset] = (byte)(value & 0xFF);
            buf[offset + 1] = (byte)((value >> 8) & 0xFF);
            buf[offset + 2] = (byte)((value >> 16) & 0xFF);
            buf[offset + 3] = (byte)((value >> 24) & 0xFF);
        }

        private static long Num(object value)
        {
            JNum num = value as JNum;
            if (num != null)
            {
                return num.ToLong();
            }
            string str = value as string;
            long l;
            if (str != null && long.TryParse(str, NumberStyles.Integer, CultureInfo.InvariantCulture, out l))
            {
                return l;
            }
            throw new FormatException("в app.asar ожидалось число");
        }

        private static string DecodeUtf8(byte[] bytes)
        {
            try
            {
                return new UTF8Encoding(false, true).GetString(bytes);
            }
            catch (DecoderFallbackException)
            {
                return Encoding.UTF8.GetString(bytes);
            }
        }

        private static string ReplaceFirst(string text, string search, string replacement)
        {
            int index = text.IndexOf(search, StringComparison.Ordinal);
            if (index < 0)
            {
                return text;
            }
            return text.Substring(0, index) + replacement + text.Substring(index + search.Length);
        }

        private static void ReadExact(Stream stream, byte[] buffer, int offset, int count)
        {
            int done = 0;
            while (done < count)
            {
                int read = stream.Read(buffer, offset + done, count - done);
                if (read <= 0)
                {
                    throw new EndOfStreamException("файл неожиданно закончился");
                }
                done += read;
            }
        }

        private static void EnsureFreeSpace(string path, long needed, string what)
        {
            try
            {
                string root = Path.GetPathRoot(Path.GetFullPath(path));
                DriveInfo drive = new DriveInfo(root);
                if (drive.AvailableFreeSpace < needed)
                {
                    throw new InvalidOperationException(
                        "Мало места на диске для " + what + ": нужно примерно " +
                        (needed / (1024 * 1024)) + " МБ.");
                }
            }
            catch (InvalidOperationException)
            {
                throw;
            }
            catch
            {
                // не смогли определить диск — не мешаем работать
            }
        }
    }
}

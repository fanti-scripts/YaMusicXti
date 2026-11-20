using System;
using System.IO;
using System.Text;

namespace YaMusicXti
{
    /// <summary>
    /// Electron fuses: байт EnableEmbeddedAsarIntegrityValidation.
    /// Без него Electron отказывается запускать изменённый app.asar.
    /// </summary>
    internal static class Fuse
    {
        private static readonly byte[] Sentinel = Encoding.ASCII.GetBytes("dL7pKGdnNz796PbbjQWNKmHXBZaB9tsX");
        private const int FuseIndex = 4;
        private const byte Enabled = 0x31;  // '1'
        private const byte Disabled = 0x30; // '0'

        public enum State
        {
            Unknown,
            Enabled,
            Disabled
        }

        public static State ReadState(string exePath)
        {
            long offset = FindOffset(exePath);
            if (offset < 0)
            {
                return State.Unknown;
            }
            using (FileStream fs = new FileStream(exePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete))
            {
                fs.Position = offset;
                int b = fs.ReadByte();
                if (b == Enabled)
                {
                    return State.Enabled;
                }
                if (b == Disabled)
                {
                    return State.Disabled;
                }
            }
            return State.Unknown;
        }

        public static void Disable(string exePath, Action<string> log)
        {
            long offset = FindOffset(exePath);
            if (offset < 0)
            {
                throw new InvalidOperationException(
                    "В exe не найден блок fuses. Возможно, это другая версия клиента.");
            }
            State state = ReadState(exePath);
            if (state == State.Disabled)
            {
                log("Проверка целостности Electron уже отключена.");
                return;
            }
            if (state != State.Enabled)
            {
                throw new InvalidOperationException("Неизвестное состояние fuses в exe.");
            }

            string backup = exePath + ".orig";
            if (!File.Exists(backup))
            {
                Io.CopyRetry(exePath, backup);
                log("Создан бэкап exe: " + Path.GetFileName(backup));
            }
            Io.WriteByteRetry(exePath, offset, Disabled, 60, 250);
            log("Проверка целостности Electron отключена.");
        }

        public static void Restore(string exePath, Action<string> log)
        {
            long offset = FindOffset(exePath);
            if (offset >= 0)
            {
                State state = ReadState(exePath);
                if (state == State.Enabled)
                {
                    log("Проверка целостности Electron уже включена.");
                    return;
                }
                if (state == State.Disabled)
                {
                    try
                    {
                        Io.WriteByteRetry(exePath, offset, Enabled, 60, 250);
                        log("Проверка целостности Electron включена обратно.");
                        return;
                    }
                    catch (IOException)
                    {
                        // exe держит кто-то ещё — попробуем заменить файл из бэкапа
                    }
                    catch (UnauthorizedAccessException)
                    {
                    }
                }
            }

            string backup = exePath + ".orig";
            if (!File.Exists(backup))
            {
                if (offset >= 0 && ReadState(exePath) == State.Enabled)
                {
                    log("Проверка целостности Electron уже включена.");
                    return;
                }
                throw new InvalidOperationException(
                    "Нет бэкапа exe — вернуть оригинальный файл нельзя. Переустановите Яндекс Музыку.");
            }

            try
            {
                Io.CopyRetry(backup, exePath);
            }
            catch (IOException)
            {
                // Файл всё ещё держат. Пробуем отодвинуть его и положить оригинал.
                string locked = exePath + ".locked";
                Io.DeleteQuiet(locked);
                Io.ReplaceRetry(exePath, locked);
                try
                {
                    Io.CopyRetry(backup, exePath);
                }
                catch
                {
                    try
                    {
                        Io.ReplaceRetry(locked, exePath);
                    }
                    catch
                    {
                    }
                    throw;
                }
                Io.DeleteQuiet(locked);
            }
            log("Оригинальный exe восстановлен из бэкапа.");
        }

        private static long FindOffset(string exePath)
        {
            const int chunk = 1 << 20;
            int overlap = Sentinel.Length;
            byte[] buf = new byte[chunk + overlap];
            using (FileStream fs = new FileStream(exePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete))
            {
                long basePos = 0;
                int carry = 0;
                while (true)
                {
                    int read = fs.Read(buf, carry, chunk);
                    if (read <= 0)
                    {
                        return -1;
                    }
                    int total = carry + read;
                    int index = Io.IndexOf(buf, total, Sentinel, 0);
                    if (index >= 0)
                    {
                        return basePos + index + Sentinel.Length + 2 + FuseIndex;
                    }
                    carry = Math.Min(overlap - 1, total);
                    Buffer.BlockCopy(buf, total - carry, buf, 0, carry);
                    basePos += total - carry;
                }
            }
        }
    }
}

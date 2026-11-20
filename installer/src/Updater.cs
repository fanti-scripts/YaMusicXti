using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Threading;

namespace YaMusicXti
{
    internal sealed class UpdateInfo
    {
        public bool Available;
        public string Version;
        public string Tag;
        public string Url;
        public string Name;
        public long Size;
        public string Sha256;
        public string Notes;
        public string Error;
    }

    /// <summary>
    /// Автообновление установщика с GitHub Releases. Пользователю не нужно
    /// заново качать exe: старый установщик сам забирает свежий и подменяет себя.
    /// </summary>
    internal static class Updater
    {
        public const string Repo = "fanti-scripts/YaMusicXti";
        public const string AssetPrefix = "YaMusicXti-Setup";
        private const string DefaultApi = "https://api.github.com/repos/" + Repo + "/releases/latest";
        private const int Tls12 = 3072;

        /// <summary>Для тестов можно подставить свой адрес API через YaMusicXti_UPDATE_API.</summary>
        public static string ApiUrl
        {
            get
            {
                string custom = Environment.GetEnvironmentVariable("YaMusicXti_UPDATE_API");
                return string.IsNullOrEmpty(custom) ? DefaultApi : custom;
            }
        }

        /// <summary>Убирает exe.old, оставшийся после прошлого самообновления.</summary>
        public static void CleanupOld()
        {
            try
            {
                string self = SelfPath();
                if (string.IsNullOrEmpty(self))
                {
                    return;
                }
                Io.DeleteQuiet(self + ".old");
            }
            catch
            {
            }
        }

        public static string SelfPath()
        {
            try
            {
                return Process.GetCurrentProcess().MainModule.FileName;
            }
            catch
            {
                return null;
            }
        }

        public static UpdateInfo Check()
        {
            UpdateInfo info = new UpdateInfo();
            try
            {
                EnableTls();
                HttpWebRequest req = (HttpWebRequest)WebRequest.Create(ApiUrl);
                req.UserAgent = "YaMusicXti-Installer/" + Core.InstallerVersion;
                req.Accept = "application/vnd.github+json";
                req.Timeout = 12000;
                req.ReadWriteTimeout = 12000;
                req.AllowAutoRedirect = true;
                using (HttpWebResponse resp = (HttpWebResponse)req.GetResponse())
                using (Stream stream = resp.GetResponseStream())
                using (StreamReader reader = new StreamReader(stream, Encoding.UTF8))
                {
                    string text = reader.ReadToEnd();
                    object parsed;
                    if (!Json.TryParse(text, out parsed))
                    {
                        info.Error = "GitHub вернул непонятный ответ.";
                        return info;
                    }
                    JObj root = parsed as JObj;
                    if (root == null)
                    {
                        info.Error = "GitHub вернул пустой ответ.";
                        return info;
                    }
                    info.Tag = root.GetString("tag_name");
                    info.Version = Normalize(info.Tag);
                    info.Notes = root.GetString("body");
                    info.Available = Compare(info.Version, Core.InstallerVersion) > 0;

                    List<object> assets = root.Get("assets") as List<object>;
                    if (assets != null)
                    {
                        JObj best = null;
                        for (int i = 0; i < assets.Count; i++)
                        {
                            JObj asset = assets[i] as JObj;
                            if (asset == null)
                            {
                                continue;
                            }
                            string name = asset.GetString("name");
                            if (string.IsNullOrEmpty(name) || !name.EndsWith(".exe", StringComparison.OrdinalIgnoreCase))
                            {
                                continue;
                            }
                            if (name.IndexOf(AssetPrefix, StringComparison.OrdinalIgnoreCase) < 0)
                            {
                                continue;
                            }
                            // Стабильное имя без версии — предпочтительный вариант.
                            bool stable = string.Equals(name, AssetPrefix + ".exe", StringComparison.OrdinalIgnoreCase);
                            if (best == null || stable)
                            {
                                best = asset;
                            }
                            if (stable)
                            {
                                break;
                            }
                        }
                        if (best != null)
                        {
                            info.Name = best.GetString("name");
                            info.Url = best.GetString("browser_download_url");
                            JNum size = best.Get("size") as JNum;
                            if (size != null)
                            {
                                info.Size = size.ToLong();
                            }
                            info.Sha256 = DigestHash(best.GetString("digest"));
                        }
                    }
                    if (info.Available && string.IsNullOrEmpty(info.Url))
                    {
                        info.Available = false;
                        info.Error = "В релизе " + info.Tag + " нет exe-файла установщика.";
                    }
                }
            }
            catch (WebException ex)
            {
                info.Error = DescribeWebError(ex);
            }
            catch (Exception ex)
            {
                info.Error = "Не удалось проверить обновления: " + ex.Message;
            }
            return info;
        }

        /// <summary>Скачивает exe обновления и возвращает путь. Повторно файл не качается.</summary>
        public static string Download(UpdateInfo info, Action<string> log)
        {
            if (info == null || string.IsNullOrEmpty(info.Url))
            {
                throw new InvalidOperationException("Нет ссылки на файл обновления.");
            }
            string dir = Path.Combine(Path.GetTempPath(), "YaMusicXti");
            Directory.CreateDirectory(dir);
            string dst = Path.Combine(dir, "setup-" + Sanitize(info.Version) + ".exe");
            if (File.Exists(dst) && IsGoodFile(dst, info))
            {
                if (log != null)
                {
                    log("Обновление уже скачано.");
                }
                return dst;
            }

            string part = dst + ".part";
            Io.DeleteQuiet(part);
            if (log != null)
            {
                log("Скачиваю обновление " + info.Version + "…");
            }
            EnableTls();
            HttpWebRequest req = (HttpWebRequest)WebRequest.Create(info.Url);
            req.UserAgent = "YaMusicXti-Installer/" + Core.InstallerVersion;
            req.Timeout = 30000;
            req.ReadWriteTimeout = 120000;
            req.AllowAutoRedirect = true;
            try
            {
                using (HttpWebResponse resp = (HttpWebResponse)req.GetResponse())
                using (Stream stream = resp.GetResponseStream())
                using (FileStream file = new FileStream(part, FileMode.Create, FileAccess.Write, FileShare.None))
                {
                    byte[] buffer = new byte[128 * 1024];
                    long total = 0;
                    int read;
                    while ((read = stream.Read(buffer, 0, buffer.Length)) > 0)
                    {
                        file.Write(buffer, 0, read);
                        total += read;
                    }
                    file.Flush(true);
                    if (info.Size > 0 && total != info.Size)
                    {
                        throw new InvalidDataException(
                            "Файл обновления скачался не целиком (" + total + " из " + info.Size + " байт).");
                    }
                }
            }
            catch
            {
                Io.DeleteQuiet(part);
                throw;
            }

            if (!string.IsNullOrEmpty(info.Sha256))
            {
                string actual = Sha256File(part);
                if (!string.Equals(actual, info.Sha256, StringComparison.OrdinalIgnoreCase))
                {
                    Io.DeleteQuiet(part);
                    throw new InvalidDataException("SHA-256 обновления не совпал с релизом.");
                }
            }
            if (!IsGoodFile(part, info))
            {
                Io.DeleteQuiet(part);
                throw new InvalidDataException("Скачанный файл обновления повреждён.");
            }
            Io.ReplaceRetry(part, dst);
            if (log != null)
            {
                log("Обновление " + info.Version + " готово.");
            }
            return dst;
        }

        /// <summary>
        /// Подменяет запущенный exe новым. Запущенный файл нельзя перезаписать,
        /// но можно переименовать — этим и пользуемся.
        /// </summary>
        public static void Apply(string downloadedPath, Action<string> log)
        {
            string self = SelfPath();
            if (string.IsNullOrEmpty(self))
            {
                throw new InvalidOperationException("Не удалось определить путь установщика.");
            }
            if (!File.Exists(downloadedPath))
            {
                throw new FileNotFoundException("Файл обновления не найден.", downloadedPath);
            }
            if (string.Equals(Path.GetFullPath(self), Path.GetFullPath(downloadedPath),
                StringComparison.OrdinalIgnoreCase))
            {
                return;
            }

            string old = self + ".old";
            Io.DeleteQuiet(old);
            bool renamed = false;
            try
            {
                File.Move(self, old);
                renamed = true;
                File.Copy(downloadedPath, self, true);
                Io.DeleteQuiet(downloadedPath);
            }
            catch (Exception ex)
            {
                if (renamed)
                {
                    try
                    {
                        if (!File.Exists(self))
                        {
                            File.Move(old, self);
                        }
                    }
                    catch
                    {
                    }
                }
                throw new InvalidOperationException(
                    "Не удалось заменить установщик: " + ex.Message +
                    "\n\nСкачайте новую версию вручную: " + ReleasePageUrl(), ex);
            }

            if (log != null)
            {
                log("Новый установщик запущен.");
            }

            ProcessStartInfo info = new ProcessStartInfo(self);
            info.Arguments = "--updated --wait-pid " + Process.GetCurrentProcess().Id.ToString(CultureInfo.InvariantCulture);
            info.WorkingDirectory = Path.GetDirectoryName(self);
            info.UseShellExecute = true;
            Process.Start(info);
        }

        public static string ReleasePageUrl()
        {
            return "https://github.com/" + Repo + "/releases/latest";
        }

        /// <summary>Сравнение версий вида 2.2.0 и v2.10.1. Возвращает -1, 0 или 1.</summary>
        public static int Compare(string a, string b)
        {
            int[] left = Parts(a);
            int[] right = Parts(b);
            int count = Math.Max(left.Length, right.Length);
            for (int i = 0; i < count; i++)
            {
                int l = i < left.Length ? left[i] : 0;
                int r = i < right.Length ? right[i] : 0;
                if (l != r)
                {
                    return l < r ? -1 : 1;
                }
            }
            return 0;
        }

        private static int[] Parts(string version)
        {
            string text = Normalize(version);
            string[] raw = text.Split('.');
            List<int> parts = new List<int>();
            for (int i = 0; i < raw.Length; i++)
            {
                int value = 0;
                int.TryParse(raw[i], NumberStyles.Integer, CultureInfo.InvariantCulture, out value);
                parts.Add(value);
            }
            if (parts.Count == 0)
            {
                parts.Add(0);
            }
            return parts.ToArray();
        }

        private static string Normalize(string version)
        {
            if (string.IsNullOrEmpty(version))
            {
                return "0";
            }
            string text = version.Trim();
            if (text.StartsWith("v", StringComparison.OrdinalIgnoreCase) ||
                text.StartsWith("V", StringComparison.OrdinalIgnoreCase))
            {
                text = text.Substring(1);
            }
            int cut = text.IndexOfAny(new char[] { '-', '+', ' ' });
            if (cut > 0)
            {
                text = text.Substring(0, cut);
            }
            return text;
        }

        private static string Sanitize(string version)
        {
            string text = Normalize(version);
            StringBuilder sb = new StringBuilder(text.Length);
            for (int i = 0; i < text.Length; i++)
            {
                char c = text[i];
                sb.Append(char.IsLetterOrDigit(c) || c == '.' ? c : '_');
            }
            return sb.Length == 0 ? "latest" : sb.ToString();
        }

        private static bool IsGoodFile(string path, UpdateInfo info)
        {
            try
            {
                FileInfo fi = new FileInfo(path);
                if (!fi.Exists || fi.Length < 32 * 1024)
                {
                    return false;
                }
                if (info.Size > 0 && fi.Length != info.Size)
                {
                    return false;
                }
                if (!string.IsNullOrEmpty(info.Sha256))
                {
                    return string.Equals(Sha256File(path), info.Sha256, StringComparison.OrdinalIgnoreCase);
                }
                return true;
            }
            catch
            {
                return false;
            }
        }

        private static string DigestHash(string digest)
        {
            if (string.IsNullOrEmpty(digest))
            {
                return null;
            }
            string text = digest.Trim();
            int colon = text.IndexOf(':');
            if (colon >= 0)
            {
                string algo = text.Substring(0, colon);
                if (!string.Equals(algo, "sha256", StringComparison.OrdinalIgnoreCase))
                {
                    return null;
                }
                text = text.Substring(colon + 1);
            }
            return text.Length == 64 ? text : null;
        }

        private static string Sha256File(string path)
        {
            using (SHA256 sha = SHA256.Create())
            using (FileStream stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read))
            {
                byte[] hash = sha.ComputeHash(stream);
                StringBuilder sb = new StringBuilder(hash.Length * 2);
                for (int i = 0; i < hash.Length; i++)
                {
                    sb.Append(hash[i].ToString("x2", CultureInfo.InvariantCulture));
                }
                return sb.ToString();
            }
        }

        private static void EnableTls()
        {
            try
            {
                ServicePointManager.SecurityProtocol =
                    (SecurityProtocolType)Tls12 | SecurityProtocolType.Tls;
            }
            catch
            {
            }
        }

        private static string DescribeWebError(WebException ex)
        {
            HttpWebResponse resp = ex.Response as HttpWebResponse;
            if (resp != null)
            {
                int code = (int)resp.StatusCode;
                if (code == 403 || code == 429)
                {
                    return "GitHub временно ограничил частоту запросов. Попробуйте позже.";
                }
                if (code == 404)
                {
                    return "Релиз не найден на GitHub.";
                }
                return "GitHub ответил ошибкой " + code + ".";
            }
            if (ex.Status == WebExceptionStatus.Timeout)
            {
                return "GitHub не ответил вовремя (таймаут).";
            }
            return "Нет связи с GitHub: " + ex.Message;
        }
    }
}

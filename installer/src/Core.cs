using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;

namespace YMBG
{
    internal sealed class AppState
    {
        public bool Found;
        public string Dir;
        public string Exe;
        public string Asar;
        public string Version;
        public bool PatchPresent;
        public bool PatchCurrent;
        public bool HasAsarBackup;
        public bool HasExeBackup;
        public Fuse.State FuseState = Fuse.State.Unknown;
        public string Error;
    }

    /// <summary>Вся работа установщика: поиск клиента,apply/restore, файлы пользователя.</summary>
    internal static class Core
    {
        public const string InstallerVersion = "2.3.0";
        public const string AppName = "Яндекс Музыка";

        public static string UserDir
        {
            get { return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "YandexMusic"); }
        }

        /// <summary>Папка с обоями пользователя: только фоны, без служебных файлов.</summary>
        public static string WallDir
        {
            get { return Path.Combine(UserDir, "wallpapers"); }
        }

        /// <summary>Служебные файлы мода: настройки, CSS, кэш превью и архивов.</summary>
        public static string CacheDir
        {
            get
            {
                return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "YandexMusic-bg");
            }
        }

        public static string DetectAppDir(string hint)
        {
            if (!string.IsNullOrEmpty(hint))
            {
                string full = Path.GetFullPath(hint);
                if (File.Exists(AsarPath(full)))
                {
                    return full;
                }
                return null;
            }
            List<string> candidates = new List<string>();
            candidates.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "Programs", "YandexMusic"));
            candidates.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "YandexMusic"));
            string pf86 = Environment.GetEnvironmentVariable("ProgramFiles(x86)");
            if (!string.IsNullOrEmpty(pf86))
            {
                candidates.Add(Path.Combine(pf86, "YandexMusic"));
            }
            for (int i = 0; i < candidates.Count; i++)
            {
                if (File.Exists(AsarPath(candidates[i])))
                {
                    return candidates[i];
                }
            }
            return null;
        }

        public static string AsarPath(string appDir)
        {
            return Path.Combine(appDir, "resources", "app.asar");
        }

        public static string FindExe(string appDir)
        {
            if (!Directory.Exists(appDir))
            {
                return null;
            }
            List<string> files = new List<string>();
            try
            {
                foreach (string path in Directory.GetFiles(appDir, "*.exe"))
                {
                    if (Path.GetFileName(path).StartsWith("Uninstall", StringComparison.OrdinalIgnoreCase))
                    {
                        continue;
                    }
                    files.Add(path);
                }
            }
            catch
            {
                return null;
            }
            if (files.Count == 0)
            {
                return null;
            }
            for (int i = 0; i < files.Count; i++)
            {
                if (Path.GetFileName(files[i]).IndexOf("Музыка", StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    return files[i];
                }
            }
            for (int i = 0; i < files.Count; i++)
            {
                if (Path.GetFileName(files[i]).StartsWith("YandexMusic", StringComparison.OrdinalIgnoreCase))
                {
                    return files[i];
                }
            }
            return files[0];
        }

        public static string ReadClientVersion(string exePath)
        {
            if (string.IsNullOrEmpty(exePath))
            {
                return null;
            }
            try
            {
                FileVersionInfo info = FileVersionInfo.GetVersionInfo(exePath);
                string v = info.FileVersion;
                if (string.IsNullOrEmpty(v))
                {
                    return null;
                }
                string[] parts = v.Split('.');
                if (parts.Length >= 3)
                {
                    return parts[0] + "." + parts[1] + "." + parts[2];
                }
                return v.Trim();
            }
            catch
            {
                return null;
            }
        }

        public static AppState GetState(string appDirHint)
        {
            AppState state = new AppState();
            state.Dir = DetectAppDir(appDirHint);
            if (state.Dir == null)
            {
                return state;
            }
            state.Found = true;
            state.Asar = AsarPath(state.Dir);
            state.Exe = FindExe(state.Dir);
            state.Version = ReadClientVersion(state.Exe);
            state.HasAsarBackup = File.Exists(state.Asar + ".orig");
            state.HasExeBackup = state.Exe != null && File.Exists(state.Exe + ".orig");

            try
            {
                byte[] index = Asar.ReadEntry(state.Asar, "index.js");
                if (index != null)
                {
                    byte[] marker = Encoding.UTF8.GetBytes(Payload.Marker);
                    byte[] markerVersion = Encoding.UTF8.GetBytes(Payload.MarkerVersion);
                    state.PatchPresent = Io.IndexOf(index, marker) >= 0;
                    state.PatchCurrent = state.PatchPresent && Io.IndexOf(index, markerVersion) >= 0;
                }
            }
            catch (Exception ex)
            {
                state.Error = ex.Message;
            }

            if (state.Version == null)
            {
                try
                {
                    state.Version = Asar.ReadEntry(state.Asar, "package.json") == null
                        ? null
                        : Asar.Version(state.Asar);
                }
                catch
                {
                }
            }

            if (!string.IsNullOrEmpty(state.Exe))
            {
                try
                {
                    state.FuseState = Fuse.ReadState(state.Exe);
                }
                catch
                {
                    state.FuseState = Fuse.State.Unknown;
                }
            }
            return state;
        }

        public static void Apply(string appDirHint, bool launch, Action<string> log)
        {
            AppState state = GetState(appDirHint);
            if (!state.Found)
            {
                throw new InvalidOperationException("Яндекс Музыка не найдена. Установите клиент и попробуйте снова.");
            }
            if (state.Exe == null)
            {
                throw new InvalidOperationException("В папке клиента не найден exe.");
            }
            if (state.Error != null)
            {
                throw new InvalidOperationException("Не удалось прочитать app.asar: " + state.Error);
            }

            log("Останавливаю Яндекс Музыку…");
            StopApp(state.Dir, log);
            Thread.Sleep(600);

            Fuse.Disable(state.Exe, log);
            Asar.Apply(state.Asar, log);

            ApplyUserFiles(log);
            log("Готово.");
            if (launch)
            {
                StartApp(state.Exe, log);
            }
        }

        public static void Restore(string appDirHint, bool launch, Action<string> log)
        {
            AppState state = GetState(appDirHint);
            if (!state.Found)
            {
                throw new InvalidOperationException("Яндекс Музыка не найдена.");
            }
            if (state.Exe == null)
            {
                throw new InvalidOperationException("В папке клиента не найден exe.");
            }

            log("Останавливаю Яндекс Музыку…");
            StopApp(state.Dir, log);
            Thread.Sleep(600);

            Fuse.Restore(state.Exe, log);
            Asar.Restore(state.Asar, log);
            RemoveLegacy(log);
            log("Готово. Оригинал на месте.");
            if (launch)
            {
                StartApp(state.Exe, log);
            }
        }

        private static void ApplyUserFiles(Action<string> log)
        {
            string dir = CacheDir;
            string wall = WallDir;
            try
            {
                Directory.CreateDirectory(dir);
                Directory.CreateDirectory(wall);
            }
            catch (Exception ex)
            {
                throw new InvalidOperationException("Не удалось создать папку " + dir + ": " + ex.Message, ex);
            }

            MigrateLegacy(log);

            string css = Path.Combine(dir, "custom-background.css");
            if (File.Exists(css))
            {
                try
                {
                    string text = File.ReadAllText(css, Encoding.UTF8);
                    if (text.IndexOf("v2", StringComparison.Ordinal) < 0)
                    {
                        string bak = css + ".v1.bak";
                        File.Copy(css, bak, true);
                        File.Delete(css);
                        log("Старый CSS сохранён как custom-background.css.v1.bak.");
                    }
                }
                catch (Exception ex)
                {
                    log("Не удалось обновить CSS: " + ex.Message);
                }
            }
            if (!File.Exists(css))
            {
                File.WriteAllText(css, Payload.Css, new UTF8Encoding(false));
                log("Установлен custom-background.css.");
            }

            string json = Path.Combine(dir, "custom-background.json");
            if (!File.Exists(json))
            {
                File.WriteAllText(json, Payload.DefaultJson, new UTF8Encoding(false));
                log("Установлен custom-background.json.");
            }

            RemoveLegacy(log);

            if (!HasCustomBackground(wall))
            {
                log("Свой фон пока не выбран — открой вкладку «Фон» в Музыке.");
            }
        }

        private static bool HasCustomBackground(string wallDir)
        {
            string[] exts = new string[] { ".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".bmp",
                ".mp4", ".webm", ".mov", ".m4v", ".ogv" };
            try
            {
                foreach (string path in Directory.GetFiles(wallDir))
                {
                    if (Array.IndexOf(exts, Path.GetExtension(path).ToLowerInvariant()) >= 0)
                    {
                        return true;
                    }
                }
            }
            catch
            {
            }
            return false;
        }

        /// <summary>Старая раскладка: фоны лежали в корне профиля вместе со служебными файлами.</summary>
        private static void MigrateLegacy(Action<string> log)
        {
            string src = UserDir;
            if (!Directory.Exists(src))
            {
                return;
            }
            string[] mediaExt = new string[] { ".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".bmp",
                ".mp4", ".webm", ".mov", ".m4v", ".ogv", ".zip", ".html", ".htm" };
            string[] files;
            try
            {
                files = Directory.GetFiles(src);
            }
            catch
            {
                return;
            }
            int moved = 0;
            for (int i = 0; i < files.Length; i++)
            {
                string name = Path.GetFileName(files[i]);
                string ext = Path.GetExtension(name).ToLowerInvariant();
                bool isMedia = Array.IndexOf(mediaExt, ext) >= 0;
                bool isModFile = name.StartsWith("custom-background_", StringComparison.OrdinalIgnoreCase) ||
                                 name.StartsWith("custom-background.", StringComparison.OrdinalIgnoreCase) ||
                                 name.StartsWith(".custom-background", StringComparison.OrdinalIgnoreCase);
                if (!isMedia && !isModFile)
                {
                    continue;
                }
                string dst = Path.Combine(isMedia ? WallDir : CacheDir, name);
                try
                {
                    if (File.Exists(dst))
                    {
                        File.Delete(files[i]);
                    }
                    else
                    {
                        File.Move(files[i], dst);
                    }
                    moved++;
                }
                catch
                {
                }
            }
            if (moved > 0)
            {
                log("Фоны из корневой папки перенесены в wallpapers, служебные файлы — в кэш.");
            }
            try
            {
                string web = Path.Combine(src, "web-wallpaper");
                if (Directory.Exists(web))
                {
                    Directory.Delete(web, true);
                }
                string thumbs = Path.Combine(src, "thumbs");
                if (Directory.Exists(thumbs))
                {
                    Directory.Delete(thumbs, true);
                }
            }
            catch
            {
            }
        }

        public static void RemoveLegacy(Action<string> log)
        {
            string[] names = new string[] { "ymbg.token", "YMBackground.ps1" };
            for (int i = 0; i < names.Length; i++)
            {
                string path = Path.Combine(UserDir, names[i]);
                if (File.Exists(path))
                {
                    try
                    {
                        File.Delete(path);
                        log("Удалён устаревший файл " + names[i] + ".");
                    }
                    catch
                    {
                    }
                }
            }
        }

        public static void DeleteSettings()
        {
            string dir = UserDir;
            if (Directory.Exists(dir))
            {
                foreach (string path in Directory.GetFiles(dir, "custom-background*"))
                {
                    try
                    {
                        File.Delete(path);
                    }
                    catch
                    {
                    }
                }
                try
                {
                    string web = Path.Combine(dir, "web-wallpaper");
                    if (Directory.Exists(web))
                    {
                        Directory.Delete(web, true);
                    }
                    string thumbs = Path.Combine(dir, "thumbs");
                    if (Directory.Exists(thumbs))
                    {
                        Directory.Delete(thumbs, true);
                    }
                }
                catch
                {
                }
            }
            // Кэш мода (превью, распакованные из архивов фоны, HTML-обои) живёт
            // в LocalAppData и в папке пользователя не остаётся.
            try
            {
                string cache = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "YandexMusic-bg");
                if (Directory.Exists(cache))
                {
                    Directory.Delete(cache, true);
                }
            }
            catch
            {
            }
        }

        public static void StopApp(string appDir, Action<string> log)
        {
            string prefix = appDir.TrimEnd('\\') + "\\";
            DateTime deadline = DateTime.UtcNow.AddSeconds(30);
            int stopped = 0;
            while (true)
            {
                List<Process> procs = FindAppProcesses(prefix);
                if (procs.Count == 0)
                {
                    break;
                }
                for (int i = 0; i < procs.Count; i++)
                {
                    try
                    {
                        procs[i].CloseMainWindow();
                    }
                    catch
                    {
                    }
                }
                for (int i = 0; i < procs.Count; i++)
                {
                    try
                    {
                        procs[i].Kill();
                        stopped++;
                    }
                    catch
                    {
                    }
                }
                for (int i = 0; i < procs.Count; i++)
                {
                    procs[i].Dispose();
                }
                if (DateTime.UtcNow >= deadline)
                {
                    throw new InvalidOperationException(
                        "Не удалось закрыть Яндекс Музыку. Закройте её вручную и повторите.");
                }
                Thread.Sleep(500);
            }
            if (stopped > 0)
            {
                log("Яндекс Музыка остановлена.");
            }
            WaitUnlocked(FindExe(appDir));
        }

        private static void WaitUnlocked(string exePath)
        {
            if (string.IsNullOrEmpty(exePath))
            {
                return;
            }
            for (int i = 0; i < 60; i++)
            {
                try
                {
                    using (new FileStream(exePath, FileMode.Open, FileAccess.ReadWrite, FileShare.None))
                    {
                    }
                    return;
                }
                catch (IOException)
                {
                    Thread.Sleep(250);
                }
                catch (UnauthorizedAccessException)
                {
                    Thread.Sleep(250);
                }
            }
            throw new InvalidOperationException(
                "Файл клиента всё ещё занят. Закройте Яндекс Музыку и повторите.");
        }

        public static bool IsRunning(string exePath)
        {
            if (string.IsNullOrEmpty(exePath))
            {
                return false;
            }
            Process[] all = Process.GetProcesses();
            int self = Process.GetCurrentProcess().Id;
            for (int i = 0; i < all.Length; i++)
            {
                Process p = all[i];
                try
                {
                    if (p.Id == self)
                    {
                        continue;
                    }
                    string path = null;
                    try
                    {
                        path = p.MainModule.FileName;
                    }
                    catch
                    {
                    }
                    if (path != null && string.Equals(path, exePath, StringComparison.OrdinalIgnoreCase))
                    {
                        return true;
                    }
                }
                finally
                {
                    p.Dispose();
                }
            }
            return false;
        }

        public static void StartApp(string exePath, Action<string> log)
        {
            if (IsRunning(exePath))
            {
                log("Яндекс Музыка уже запущена.");
                return;
            }
            log("Запускаю Яндекс Музыку…");
            ProcessStartInfo info = new ProcessStartInfo(exePath);
            info.WorkingDirectory = Path.GetDirectoryName(exePath);
            info.UseShellExecute = true;
            Process.Start(info);
        }

        private static List<Process> FindAppProcesses(string dirPrefix)
        {
            List<Process> result = new List<Process>();
            Process[] all;
            try
            {
                all = Process.GetProcesses();
            }
            catch
            {
                return result;
            }
            int self = Process.GetCurrentProcess().Id;
            string selfPath = null;
            try
            {
                selfPath = Process.GetCurrentProcess().MainModule.FileName;
            }
            catch
            {
            }
            for (int i = 0; i < all.Length; i++)
            {
                Process p = all[i];
                bool keep = false;
                try
                {
                    if (p.Id == self)
                    {
                        continue;
                    }
                    string path = null;
                    try
                    {
                        path = p.MainModule.FileName;
                    }
                    catch
                    {
                    }
                    if (path != null && selfPath != null &&
                        string.Equals(path, selfPath, StringComparison.OrdinalIgnoreCase))
                    {
                        continue;
                    }
                    bool hit = false;
                    if (path != null)
                    {
                        // Путь читается — доверяем только ему, чтобы не убить чужую копию клиента.
                        hit = path.StartsWith(dirPrefix, StringComparison.OrdinalIgnoreCase);
                    }
                    else
                    {
                        // Путь недоступен (например, клиент запущен от администратора) —
                        // тогда узнаём процесс по имени.
                        string name = p.ProcessName;
                        hit = string.Equals(name, AppName, StringComparison.OrdinalIgnoreCase) ||
                              name.StartsWith("YandexMusic", StringComparison.OrdinalIgnoreCase) ||
                              name.StartsWith("Яндекс Музыка", StringComparison.OrdinalIgnoreCase);
                    }
                    if (hit)
                    {
                        result.Add(p);
                        keep = true;
                    }
                }
                catch
                {
                }
                finally
                {
                    if (!keep)
                    {
                        p.Dispose();
                    }
                }
            }
            return result;
        }
    }
}

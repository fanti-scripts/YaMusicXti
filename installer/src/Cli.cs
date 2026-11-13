using System;
using System.IO;
using System.Text;

namespace YMBG
{
    /// <summary>Режим командной строки: удобно для проверки и для скриптов.</summary>
    internal static class Cli
    {
        [System.Runtime.InteropServices.DllImport("kernel32.dll")]
        private static extern bool AttachConsole(int processId);

        [System.Runtime.InteropServices.DllImport("kernel32.dll")]
        private static extern bool AllocConsole();

        public static int Run(string[] args)
        {
            try
            {
                if (!AttachConsole(-1))
                {
                    AllocConsole();
                }
            }
            catch
            {
            }
            try
            {
                Console.OutputEncoding = new UTF8Encoding(false);
            }
            catch
            {
            }

            bool apply = false;
            bool restore = false;
            bool status = false;
            bool launch = false;
            string appDir = null;
            StreamWriter fileLog = null;

            try
            {
                for (int i = 0; i < args.Length; i++)
                {
                    string arg = args[i];
                    switch (arg.ToLowerInvariant())
                    {
                        case "--apply":
                            apply = true;
                            break;
                        case "--restore":
                        case "--remove":
                        case "--uninstall":
                            restore = true;
                            break;
                        case "--status":
                            status = true;
                            break;
                        case "--launch":
                            launch = true;
                            break;
                        case "--appdir":
                            if (i + 1 < args.Length)
                            {
                                appDir = args[++i];
                            }
                            break;
                        case "--out":
                            if (i + 1 < args.Length)
                            {
                                try
                                {
                                    fileLog = new StreamWriter(args[++i], false, new UTF8Encoding(false));
                                    fileLog.AutoFlush = true;
                                }
                                catch
                                {
                                    fileLog = null;
                                }
                            }
                            break;
                        case "--help":
                        case "-h":
                        case "/?":
                            PrintHelp();
                            return 0;
                    }
                }

                Action<string> log = delegate(string message)
                {
                    try
                    {
                        Console.WriteLine(message);
                    }
                    catch
                    {
                    }
                    if (fileLog != null)
                    {
                        try
                        {
                            fileLog.WriteLine(message);
                        }
                        catch
                        {
                        }
                    }
                };

                if (status)
                {
                    return PrintStatus(appDir, log);
                }
                if (apply == restore)
                {
                    PrintHelp();
                    return 2;
                }

                log(apply ? "Установка мода «Фон Яндекс Музыки»" : "Удаление мода «Фон Яндекс Музыки»");
                if (apply)
                {
                    Core.Apply(appDir, launch, log);
                }
                else
                {
                    Core.Restore(appDir, launch, log);
                }
                return 0;
            }
            catch (Exception ex)
            {
                try
                {
                    Console.WriteLine("Ошибка: " + ex.Message);
                }
                catch
                {
                }
                if (fileLog != null)
                {
                    try
                    {
                        fileLog.WriteLine("Ошибка: " + ex.Message);
                    }
                    catch
                    {
                    }
                }
                return 1;
            }
            finally
            {
                if (fileLog != null)
                {
                    fileLog.Dispose();
                }
            }
        }

        private static int PrintStatus(string appDir, Action<string> log)
        {
            AppState state = Core.GetState(appDir);
            if (!state.Found)
            {
                log("Яндекс Музыка: не найдена");
                return 1;
            }
            log("Яндекс Музыка: " + (state.Version ?? "версия неизвестна"));
            log("Папка: " + state.Dir);
            log("Патч app.asar: " + (state.PatchCurrent ? "установлен"
                : state.PatchPresent ? "устарел" : "нет"));
            log("Бэкап app.asar.orig: " + (state.HasAsarBackup ? "есть" : "нет"));
            log("Бэкап exe.orig: " + (state.HasExeBackup ? "есть" : "нет"));
            log("Проверка целостности Electron: " + (state.FuseState == Fuse.State.Disabled ? "отключена"
                : state.FuseState == Fuse.State.Enabled ? "включена" : "неизвестно"));
            log("Версия мода: " + Payload.MarkerVersion);
            if (state.Error != null)
            {
                log("Ошибка чтения: " + state.Error);
                return 1;
            }
            return 0;
        }

        private static void PrintHelp()
        {
            string text =
                "Фон Яндекс Музыки — установщик " + Core.InstallerVersion + "\r\n" +
                "\r\n" +
                "Без аргументов открывает окно установщика.\r\n" +
                "\r\n" +
                "  --apply            установить патч\r\n" +
                "  --restore          вернуть оригинальные файлы\r\n" +
                "  --status           показать состояние\r\n" +
                "  --launch           запустить Музыку после операции\r\n" +
                "  --appdir <путь>    указать папку клиента вручную\r\n" +
                "  --out <файл>       писать журнал в файл\r\n" +
                "  --help             эта справка\r\n";
            try
            {
                Console.WriteLine(text);
            }
            catch
            {
            }
        }
    }
}

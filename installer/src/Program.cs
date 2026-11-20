using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Threading;
using System.Windows.Forms;

[assembly: System.Reflection.AssemblyTitle("YaMusicXti — установщик")]
[assembly: System.Reflection.AssemblyDescription("Установщик мода «YaMusicXti»")]
[assembly: System.Reflection.AssemblyProduct("YaMusicXti")]
[assembly: System.Reflection.AssemblyCopyright("Неофициальный мод")]
[assembly: System.Reflection.AssemblyVersion("2.4.0.0")]
[assembly: System.Reflection.AssemblyFileVersion("2.4.0.0")]
[assembly: System.Runtime.InteropServices.ComVisible(false)]

namespace YaMusicXti
{
    internal static class Program
    {
        [STAThread]
        private static int Main(string[] args)
        {
            // Служебные аргументы самообновления: новый exe ждёт, пока старый
            // процесс отпустит мьютекс, и только потом открывает окно.
            int waitPid = 0;
            List<string> rest = new List<string>();
            if (args != null)
            {
                for (int i = 0; i < args.Length; i++)
                {
                    string arg = args[i];
                    if (string.Equals(arg, "--updated", StringComparison.OrdinalIgnoreCase))
                    {
                        continue;
                    }
                    if (string.Equals(arg, "--wait-pid", StringComparison.OrdinalIgnoreCase))
                    {
                        if (i + 1 < args.Length)
                        {
                            int.TryParse(args[++i], out waitPid);
                        }
                        continue;
                    }
                    rest.Add(arg);
                }
            }
            if (waitPid > 0)
            {
                try
                {
                    using (Process old = Process.GetProcessById(waitPid))
                    {
                        old.WaitForExit(20000);
                    }
                }
                catch
                {
                }
            }
            Updater.CleanupOld();

            if (rest.Count > 0)
            {
                return Cli.Run(rest.ToArray());
            }

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            bool created;
            using (Mutex mutex = new Mutex(true, @"Local\YaMusicXtiInstaller", out created))
            {
                if (!created)
                {
                    return 0;
                }
                Application.Run(new MainForm(null));
                GC.KeepAlive(mutex);
            }
            return 0;
        }
    }
}
